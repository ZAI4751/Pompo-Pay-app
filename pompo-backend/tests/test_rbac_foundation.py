"""Focused tests for the M004 RBAC foundation."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Permission, Role, RolePermission, User
from app.models.base import Base
from app.permissions.catalog import PERMISSIONS, SYSTEM_ROLES, validate_catalog
from app.repositories.rbac import AuthorizationRepository
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


def test_permission_catalog_is_unique_and_complete() -> None:
    validate_catalog()
    assert len({permission.code for permission in PERMISSIONS}) == len(PERMISSIONS)
    assert set(SYSTEM_ROLES) == {"platform_admin", "merchant_owner", "branch_manager", "cashier"}


@pytest.mark.asyncio
async def test_seed_is_idempotent_and_preserves_existing_role(session: AsyncSession) -> None:
    existing_role = Role(code="cashier", name="Existing Cashier", is_system_role=False)
    session.add(existing_role)
    await session.commit()

    await seed_rbac_session(session)
    await session.commit()
    await seed_rbac_session(session)
    await session.commit()

    roles = list((await session.scalars(select(Role))).all())
    permissions = list((await session.scalars(select(Permission))).all())
    assignments = list((await session.scalars(select(RolePermission))).all())
    cashier = next(role for role in roles if role.code == "cashier")

    assert len(roles) == len(SYSTEM_ROLES)
    assert len(permissions) == len(PERMISSIONS)
    assert len(assignments) == sum(len(values[2]) for values in SYSTEM_ROLES.values())
    assert cashier.name == "Existing Cashier"
    assert cashier.is_system_role is True


@pytest.mark.asyncio
async def test_effective_permissions_ignore_inactive_role(session: AsyncSession) -> None:
    role = Role(code="cashier", name="Cashier", is_active=False)
    permission = Permission(code="transactions:read", description="Read transactions")
    user = User(
        role=role,
        email="inactive-role@chikondi.mw",
        full_name="Inactive Role",
        hashed_password="not-a-real-hash",
    )
    session.add_all([role, permission, user])
    await session.flush()
    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    await session.commit()

    repository = AuthorizationRepository(session)
    assert await repository.get_user_role(user.id) is None
    assert await repository.get_user_permission_codes(user.id) == set()


@pytest.mark.asyncio
async def test_duplicate_role_permission_is_rejected(session: AsyncSession) -> None:
    role = Role(code="cashier", name="Cashier")
    permission = Permission(code="transactions:read")
    session.add_all([role, permission])
    await session.flush()
    session.add_all(
        [
            RolePermission(role_id=role.id, permission_id=permission.id),
            RolePermission(role_id=role.id, permission_id=permission.id),
        ]
    )
    with pytest.raises(IntegrityError):
        await session.flush()