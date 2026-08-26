"""Phase 2 authorization engine tests."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import require_permission
from app.models import Permission, Role, RolePermission, User
from app.models.base import Base
from app.repositories.rbac import AuthorizationRepository
from app.services.authorization import AuthorizationDeniedError, AuthorizationService


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
async def users(session: AsyncSession) -> tuple[User, User, User]:
    permission = Permission(code="transactions:read")
    role = Role(code="cashier", name="Cashier")
    role.permissions.append(RolePermission(permission=permission))
    allowed = User(
        role=role,
        email="allowed@chikondi.mw",
        full_name="Allowed User",
        hashed_password="not-a-real-hash",
    )
    denied_role = Role(code="empty", name="Empty", is_active=True)
    denied = User(
        role=denied_role,
        email="denied@chikondi.mw",
        full_name="Denied User",
        hashed_password="not-a-real-hash",
    )
    inactive = User(
        role=role,
        email="inactive@chikondi.mw",
        full_name="Inactive User",
        hashed_password="not-a-real-hash",
        is_active=False,
    )
    session.add_all([permission, role, allowed, denied_role, denied, inactive])
    await session.commit()
    return allowed, denied, inactive


@pytest.mark.asyncio
async def test_effective_permissions_and_denial(
    session: AsyncSession, users: tuple[User, User, User]
) -> None:
    allowed, denied, inactive = users
    service = AuthorizationService(AuthorizationRepository(session))

    assert await service.has_permission(allowed, "transactions:read") is True
    assert await service.has_permission(denied, "transactions:read") is False
    assert await service.get_user_permissions(inactive) == set()
    with pytest.raises(AuthorizationDeniedError):
        await service.require_permission(denied, "transactions:read")


@pytest.mark.asyncio
async def test_dependency_returns_403_for_authenticated_user_without_permission(
    session: AsyncSession, users: tuple[User, User, User]
) -> None:
    _allowed, denied, _inactive = users
    service = AuthorizationService(AuthorizationRepository(session))
    app = FastAPI()

    async def current_user() -> User:
        return denied

    async def authorization_service() -> AuthorizationService:
        return service

    app.get(
        "/protected",
        dependencies=[
            Depends(require_permission("transactions:read")),
        ],
    )(lambda: {"ok": True})
    app.dependency_overrides.update(
        {
            # Resolve the aliases used inside the generated dependency.
            # The override keys are imported lazily to keep this test isolated.
        }
    )

    from app.api import deps

    app.dependency_overrides[deps.get_current_user] = current_user
    app.dependency_overrides[deps.get_authorization_service] = authorization_service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/protected")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_role_delegation_and_tenant_scope_are_limited(
    session: AsyncSession, users: tuple[User, User, User]
) -> None:
    allowed, denied, _inactive = users
    merchant_id = uuid.uuid4()
    allowed.merchant_id = merchant_id
    allowed.branch_id = uuid.uuid4()
    await session.commit()

    service = AuthorizationService(AuthorizationRepository(session))
    target_role = Role(code="target", name="Target")
    permission_id = await session.scalar(
        select(Permission.id).where(Permission.code == "transactions:read")
    )
    target_role.permissions.append(RolePermission(permission_id=permission_id))
    session.add(target_role)
    await session.commit()

    assert await service.can_grant_permission(allowed, "transactions:read") is True
    assert await service.can_grant_permission(denied, "transactions:read") is False
    assert await service.can_assign_role(allowed, target_role) is True
    assert await service.can_access_scope(allowed, merchant_id=merchant_id) is False
    assert await service.can_access_scope(allowed, merchant_id=uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_only_platform_admin_can_assign_system_roles(
    session: AsyncSession, users: tuple[User, User, User]
) -> None:
    allowed, _denied, _inactive = users
    platform_role = Role(code="platform_admin", name="Platform administrator", is_system_role=True)
    session.add(platform_role)
    await session.commit()

    service = AuthorizationService(AuthorizationRepository(session))
    assert await service.can_assign_role(allowed, platform_role) is False