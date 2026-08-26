"""API-level tests for RBAC administration."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
from app.api.v1.rbac import get_rbac_service, router
from app.models import Permission, Role, User
from app.models.base import Base
from app.permissions.catalog import PERMISSIONS
from app.repositories.rbac import AuthorizationRepository
from app.services.authorization import AuthorizationService
from app.services.rbac import RBACService
from scripts.seed_rbac import seed_rbac_session


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


@pytest.fixture
async def admin_app(session: AsyncSession) -> tuple[FastAPI, User]:
    await seed_rbac_session(session)
    platform_role = await session.scalar(select(Role).where(Role.code == "platform_admin"))
    assert platform_role is not None
    admin = User(
        role_id=platform_role.id,
        email="rbac-admin@chikondi.mw",
        full_name="RBAC Admin",
        hashed_password="not-a-real-hash",
    )
    session.add(admin)
    await session.commit()

    app = FastAPI()
    app.include_router(router)
    authorization_service = AuthorizationService(AuthorizationRepository(session))
    app.dependency_overrides[deps.get_current_user] = lambda: admin
    app.dependency_overrides[deps.get_authorization_service] = lambda: authorization_service
    app.dependency_overrides[get_rbac_service] = lambda: RBACService(session)
    return app, admin


@pytest.mark.asyncio
async def test_rbac_api_role_crud_and_permission_management(
    admin_app: tuple[FastAPI, User], session: AsyncSession
) -> None:
    app, _admin = admin_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post(
            "/rbac/roles",
            json={"code": "api_operator", "name": "API Operator"},
        )
        assert create_response.status_code == 201
        role = create_response.json()
        assert role["code"] == "api_operator"

        permission = await session.scalar(select(Permission).where(Permission.code == "users:read"))
        assert permission is not None
        grant_response = await client.post(f"/rbac/roles/{role['id']}/permissions/{permission.id}")
        assert grant_response.status_code == 201
        assert grant_response.json()["permission_code"] == "users:read"

        duplicate_response = await client.post(
            f"/rbac/roles/{role['id']}/permissions/{permission.id}"
        )
        assert duplicate_response.status_code == 409

        revoke_response = await client.delete(
            f"/rbac/roles/{role['id']}/permissions/{permission.id}"
        )
        assert revoke_response.status_code == 204

        update_response = await client.patch(
            f"/rbac/roles/{role['id']}",
            json={"name": "Updated API Operator"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated API Operator"

        delete_response = await client.delete(f"/rbac/roles/{role['id']}")
        assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_rbac_api_protects_system_roles_and_lists_catalog(
    admin_app: tuple[FastAPI, User], session: AsyncSession
) -> None:
    app, _admin = admin_app
    platform_role = await session.scalar(select(Role).where(Role.code == "platform_admin"))
    assert platform_role is not None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        roles_response = await client.get("/rbac/roles")
        assert roles_response.status_code == 200
        assert any(role["code"] == "platform_admin" for role in roles_response.json())

        permissions_response = await client.get("/rbac/permissions")
        assert permissions_response.status_code == 200
        assert len(permissions_response.json()) == len(PERMISSIONS)

        update_response = await client.patch(
            f"/rbac/roles/{platform_role.id}",
            json={"name": "Changed"},
        )
        assert update_response.status_code == 403

        delete_response = await client.delete(f"/rbac/roles/{platform_role.id}")
        assert delete_response.status_code == 403


@pytest.mark.asyncio
async def test_rbac_api_assigns_role_and_rejects_role_removal(
    admin_app: tuple[FastAPI, User], session: AsyncSession
) -> None:
    app, admin = admin_app
    target_role = Role(code="assigned_role", name="Assigned Role")
    target = User(
        role=target_role,
        email="rbac-target@chikondi.mw",
        full_name="RBAC Target",
        hashed_password="not-a-real-hash",
    )
    session.add_all([target_role, target])
    await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assign_response = await client.put(
            f"/rbac/users/{target.id}/role",
            json={"role_id": str(target_role.id)},
        )
        assert assign_response.status_code == 204

        removal_response = await client.delete(f"/rbac/users/{target.id}/role")
        assert removal_response.status_code == 409

        self_removal_response = await client.delete(f"/rbac/users/{admin.id}/role")
        assert self_removal_response.status_code == 403
