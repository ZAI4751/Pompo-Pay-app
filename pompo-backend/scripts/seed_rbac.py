"""Idempotently seed POMPO's default permissions, roles, and assignments."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config.base import get_settings
from app.database.engine import create_engine, dispose_engine
from app.models import Permission, Role, RolePermission
from app.permissions.catalog import PERMISSIONS, SYSTEM_ROLES


async def seed_rbac_session(session: AsyncSession) -> None:
    """Create missing catalog rows without deleting or duplicating existing data."""
    permissions: dict[str, Permission] = {}
    for definition in PERMISSIONS:
        permission = await session.scalar(
            select(Permission).where(Permission.code == definition.code)
        )
        if permission is None:
            permission = Permission(
                code=definition.code,
                description=definition.description,
            )
            session.add(permission)
        permissions[definition.code] = permission

    await session.flush()

    for code, (name, description, permission_codes) in SYSTEM_ROLES.items():
        role = await session.scalar(select(Role).where(Role.code == code))
        if role is None:
            role = Role(
                code=code,
                name=name,
                description=description,
                is_system_role=True,
                is_active=True,
            )
            session.add(role)
            await session.flush()
        elif role.is_system_role is False:
            role.is_system_role = True

        assignments = (
            await session.scalars(
                select(RolePermission).where(RolePermission.role_id == role.id)
            )
        ).all()
        existing = {assignment.permission_id for assignment in assignments}
        for permission_code in permission_codes:
            permission = permissions[permission_code]
            if permission.id not in existing:
                session.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                        granted_at=datetime.now(UTC),
                    )
                )


async def seed_rbac() -> None:
    """Create missing catalog rows without deleting or duplicating existing data."""
    settings = get_settings()
    engine = create_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    try:
        async with factory() as session:
            await seed_rbac_session(session)
            await session.commit()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(seed_rbac())