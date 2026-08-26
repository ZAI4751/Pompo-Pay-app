"""M005 repository, service, and tenant-boundary tests."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
from app.api.v1.organization import get_organization_service, router
from app.models import AuditLog, Branch, Merchant, Permission, Role, RolePermission, User
from app.models.base import Base
from app.repositories.organization import BranchRepository, MerchantRepository
from app.services.organization import (
    OrganizationForbiddenError,
    OrganizationNotFoundError,
    OrganizationService,
)


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


async def _actor(
    session: AsyncSession,
    role_code: str,
    permissions: tuple[str, ...],
    merchant_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
) -> User:
    code = role_code if role_code == "platform_admin" else f"{role_code}_{uuid.uuid4().hex}"
    role = Role(code=code, name=role_code)
    permission_models = [Permission(code=permission) for permission in permissions]
    role.permissions.extend(
        RolePermission(permission=permission) for permission in permission_models
    )
    actor = User(
        merchant_id=merchant_id,
        branch_id=branch_id,
        role=role,
        email=f"{role_code}-{uuid.uuid4().hex}@example.com",
        full_name=role_code,
        hashed_password="test-hash",
        is_active=True,
    )
    session.add(actor)
    await session.commit()
    return actor


async def _merchant(session: AsyncSession, name: str) -> Merchant:
    merchant = Merchant(
        name=name,
        contact_email=f"{uuid.uuid4().hex}@example.com",
        contact_phone="+265991000000",
    )
    session.add(merchant)
    await session.commit()
    return merchant


@pytest.mark.asyncio
async def test_repositories_filter_soft_deleted_rows(session: AsyncSession) -> None:
    first = await _merchant(session, "First")
    second = await _merchant(session, "Second")
    repository = MerchantRepository(session)

    await repository.soft_delete(first)
    await session.commit()

    assert await repository.get_active(first.id) is None
    assert await repository.get_active(second.id) == second
    assert await repository.list_active() == [second]


@pytest.mark.asyncio
async def test_branch_repository_filters_by_merchant_and_soft_delete(
    session: AsyncSession,
) -> None:
    first = await _merchant(session, "First")
    second = await _merchant(session, "Second")
    branch = Branch(merchant_id=first.id, name="First Branch")
    other = Branch(merchant_id=second.id, name="Other Branch")
    session.add_all([branch, other])
    await session.commit()
    repository = BranchRepository(session)

    assert await repository.list_active(first.id) == [branch]
    await repository.soft_delete(branch)
    await session.commit()
    assert await repository.list_active(first.id) == []
    assert await repository.get_active(other.id) == other


@pytest.mark.asyncio
async def test_service_blocks_cross_tenant_and_invalid_branch_creation(
    session: AsyncSession,
) -> None:
    first = await _merchant(session, "First")
    second = await _merchant(session, "Second")
    actor = await _actor(session, "owner", ("merchants:read", "branches:create"), first.id)
    service = OrganizationService(session)

    with pytest.raises(OrganizationForbiddenError):
        await service.get_merchant(actor, second.id)
    with pytest.raises(OrganizationForbiddenError):
        await service.create_branch(actor, second.id, {"name": "Forbidden"})
    with pytest.raises(OrganizationNotFoundError):
        await service.create_branch(actor, uuid.uuid4(), {"name": "Missing"})


@pytest.mark.asyncio
async def test_platform_admin_can_cross_tenants_and_mutations_are_audited(
    session: AsyncSession,
) -> None:
    merchant = await _merchant(session, "Merchant")
    actor = await _actor(
        session,
        "platform_admin",
        ("merchants:read", "merchants:update", "branches:create"),
    )
    service = OrganizationService(session)

    updated = await service.update_merchant(actor, merchant.id, {"name": "Renamed"})
    branch = await service.create_branch(actor, merchant.id, {"name": "Main"})

    assert updated.name == "Renamed"
    assert branch.merchant_id == merchant.id
    actions = (await session.scalars(select(AuditLog.action))).all()
    assert set(actions) == {"merchant_updated", "branch_created"}


@pytest.mark.asyncio
async def test_api_returns_401_without_authentication() -> None:
    from fastapi import FastAPI

    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[deps.get_auth_service] = lambda: object()
    application.dependency_overrides[get_organization_service] = lambda: object()
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/organization/merchants")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_maps_service_scope_errors_to_403() -> None:
    from fastapi import FastAPI

    class ForbiddenService:
        async def list_merchants(self, _actor: User) -> list[Merchant]:
            raise OrganizationForbiddenError("Resource is outside actor scope")

    application = FastAPI()
    application.include_router(router)
    actor = User(email="api@example.com", full_name="API", hashed_password="hash")
    application.dependency_overrides[deps.get_current_user] = lambda: actor
    application.dependency_overrides[get_organization_service] = lambda: ForbiddenService()
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/organization/merchants")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_api_returns_merchant_list() -> None:
    from fastapi import FastAPI

    merchant = Merchant(
        id=uuid.uuid4(),
        name="Merchant",
        contact_email="merchant@example.com",
        contact_phone="+265991000000",
        is_active=True,
    )

    class OrganizationStub:
        async def list_merchants(self, _actor: User) -> list[Merchant]:
            return [merchant]

    application = FastAPI()
    application.include_router(router)
    actor = User(email="api@example.com", full_name="API", hashed_password="hash")
    application.dependency_overrides[deps.get_current_user] = lambda: actor
    application.dependency_overrides[get_organization_service] = lambda: OrganizationStub()
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/organization/merchants")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Merchant"