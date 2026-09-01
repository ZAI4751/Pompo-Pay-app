"""Till administration: repository, tenant scope, and API mapping."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
from app.api.v1.organization import get_organization_service, router
from app.models import AuditLog, Branch, Merchant, Permission, Role, RolePermission, Till, User
from app.models.base import Base
from app.repositories.organization import TillRepository
from app.services.organization import (
    OrganizationConflictError,
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
    role = await session.scalar(select(Role).where(Role.code == code))
    if role is None:
        role = Role(code=code, name=role_code)
        session.add(role)
        await session.flush()
    for permission_code in permissions:
        permission = await session.scalar(
            select(Permission).where(Permission.code == permission_code)
        )
        if permission is None:
            permission = Permission(code=permission_code)
            session.add(permission)
            await session.flush()
        grant = await session.scalar(
            select(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id,
            )
        )
        if grant is None:
            session.add(RolePermission(role=role, permission=permission))
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


async def _branch(session: AsyncSession, merchant: Merchant, name: str = "Main") -> Branch:
    branch = Branch(merchant_id=merchant.id, name=name)
    session.add(branch)
    await session.commit()
    return branch


TILL_PERMS = ("tills:read", "tills:create", "tills:update", "tills:delete")


@pytest.mark.asyncio
async def test_till_repository_filters_by_branch_and_soft_delete(session: AsyncSession) -> None:
    merchant = await _merchant(session, "Merchant")
    first_branch = await _branch(session, merchant, "First")
    second_branch = await _branch(session, merchant, "Second")
    till = Till(branch_id=first_branch.id, code="T1", name="Counter")
    other = Till(branch_id=second_branch.id, code="T1", name="Other")
    session.add_all([till, other])
    await session.commit()
    repository = TillRepository(session)

    assert await repository.list_active(first_branch.id) == [till]
    await repository.soft_delete(till)
    await session.commit()
    assert await repository.list_active(first_branch.id) == []
    assert await repository.get_active(other.id) == other


@pytest.mark.asyncio
async def test_create_retrieve_list_update_and_deactivate_till(session: AsyncSession) -> None:
    merchant = await _merchant(session, "Merchant")
    branch = await _branch(session, merchant)
    actor = await _actor(session, "platform_admin", TILL_PERMS)
    service = OrganizationService(session)

    created = await service.create_till(actor, branch.id, {"code": "POS-1", "name": "Front"})
    fetched = await service.get_till(actor, created.id)
    listed = await service.list_tills(actor, branch.id)
    updated = await service.update_till(actor, created.id, {"name": "Front desk"})
    await service.delete_till(actor, created.id)

    assert fetched.id == created.id
    assert listed == [created]
    assert updated.name == "Front desk"
    assert await service.list_tills(actor, branch.id) == []
    actions = (await session.scalars(select(AuditLog.action))).all()
    assert {"till_created", "till_updated", "till_deactivated"}.issubset(set(actions))


@pytest.mark.asyncio
async def test_duplicate_till_code_conflicts(session: AsyncSession) -> None:
    merchant = await _merchant(session, "Merchant")
    branch = await _branch(session, merchant)
    actor = await _actor(session, "platform_admin", TILL_PERMS)
    service = OrganizationService(session)
    await service.create_till(actor, branch.id, {"code": "POS-1", "name": "One"})
    with pytest.raises(OrganizationConflictError):
        await service.create_till(actor, branch.id, {"code": "POS-1", "name": "Two"})


@pytest.mark.asyncio
async def test_cannot_reassign_till_branch_or_code(session: AsyncSession) -> None:
    merchant = await _merchant(session, "Merchant")
    branch = await _branch(session, merchant)
    actor = await _actor(session, "platform_admin", TILL_PERMS)
    service = OrganizationService(session)
    till = await service.create_till(actor, branch.id, {"code": "POS-1", "name": "Front"})
    with pytest.raises(OrganizationForbiddenError):
        await service.update_till(actor, till.id, {"code": "POS-2"})
    with pytest.raises(OrganizationForbiddenError):
        await service.update_till(actor, till.id, {"branch_id": uuid.uuid4()})


@pytest.mark.asyncio
async def test_cross_merchant_and_cross_branch_till_access_is_forbidden(
    session: AsyncSession,
) -> None:
    first = await _merchant(session, "First")
    second = await _merchant(session, "Second")
    first_branch = await _branch(session, first)
    second_branch = await _branch(session, second)
    owner = await _actor(session, "owner", TILL_PERMS, first.id)
    service = OrganizationService(session)
    till = await OrganizationService(session).create_till(
        await _actor(session, "platform_admin", TILL_PERMS),
        second_branch.id,
        {"code": "X1", "name": "Other"},
    )

    with pytest.raises(OrganizationForbiddenError):
        await service.list_tills(owner, second_branch.id)
    with pytest.raises(OrganizationForbiddenError):
        await service.create_till(owner, second_branch.id, {"code": "T9", "name": "Nope"})
    with pytest.raises(OrganizationForbiddenError):
        await service.get_till(owner, till.id)
    with pytest.raises(OrganizationNotFoundError):
        await service.get_till(owner, uuid.uuid4())

    other_branch = await _branch(session, first, "Other")
    manager = await _actor(session, "manager", TILL_PERMS, first.id, first_branch.id)
    with pytest.raises(OrganizationForbiddenError):
        await service.list_tills(manager, other_branch.id)


@pytest.mark.asyncio
async def test_merchant_owner_can_manage_tills_without_branch_assignment(
    session: AsyncSession,
) -> None:
    merchant = await _merchant(session, "Merchant")
    branch = await _branch(session, merchant)
    owner = await _actor(session, "owner", TILL_PERMS, merchant.id)
    service = OrganizationService(session)
    till = await service.create_till(owner, branch.id, {"code": "POS-1", "name": "Front"})
    updated = await service.update_till(owner, till.id, {"name": "Updated"})
    assert updated.name == "Updated"


@pytest.mark.asyncio
async def test_unauthorized_actor_cannot_read_tills(session: AsyncSession) -> None:
    merchant = await _merchant(session, "Merchant")
    branch = await _branch(session, merchant)
    actor = await _actor(session, "cashier", ("transactions:read",), merchant.id)
    service = OrganizationService(session)
    with pytest.raises(OrganizationForbiddenError):
        await service.list_tills(actor, branch.id)


@pytest.mark.asyncio
async def test_till_api_returns_401_without_authentication() -> None:
    from fastapi import FastAPI

    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[deps.get_auth_service] = lambda: object()
    application.dependency_overrides[get_organization_service] = lambda: object()
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get(f"/organization/tills/{uuid.uuid4()}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_till_api_maps_scope_errors_to_403() -> None:
    from fastapi import FastAPI

    class ForbiddenService:
        async def list_tills(self, _actor: User, _branch_id: uuid.UUID) -> list[Till]:
            raise OrganizationForbiddenError("Resource is outside actor scope")

    application = FastAPI()
    application.include_router(router)
    actor = User(email="api@example.com", full_name="API", hashed_password="hash")
    application.dependency_overrides[deps.get_current_user] = lambda: actor
    application.dependency_overrides[get_organization_service] = lambda: ForbiddenService()
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get(f"/organization/branches/{uuid.uuid4()}/tills")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_till_api_returns_till_list_with_merchant_id() -> None:
    from fastapi import FastAPI

    merchant_id = uuid.uuid4()
    branch_id = uuid.uuid4()
    till = Till(
        id=uuid.uuid4(),
        branch_id=branch_id,
        code="POS-1",
        name="Front",
        is_active=True,
    )
    till.branch = Branch(
        id=branch_id,
        merchant_id=merchant_id,
        name="Main",
        is_active=True,
    )

    class OrganizationStub:
        async def list_tills(self, _actor: User, _branch_id: uuid.UUID) -> list[Till]:
            return [till]

    application = FastAPI()
    application.include_router(router)
    actor = User(email="api@example.com", full_name="API", hashed_password="hash")
    application.dependency_overrides[deps.get_current_user] = lambda: actor
    application.dependency_overrides[get_organization_service] = lambda: OrganizationStub()
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get(f"/organization/branches/{branch_id}/tills")
    assert response.status_code == 200
    body = response.json()[0]
    assert body["code"] == "POS-1"
    assert body["merchant_id"] == str(merchant_id)
    assert body["branch_id"] == str(branch_id)
