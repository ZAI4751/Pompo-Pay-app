"""Repository queries for roles, permissions, and effective grants."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Permission, Role, RolePermission, User
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Data access for roles."""

    model = Role

    async def get_by_code(self, code: str) -> Role | None:
        result = await self._session.execute(select(Role).where(Role.code == code))
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Role]:
        result = await self._session.execute(
            select(Role).where(Role.is_active.is_(True)).order_by(Role.code)
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[Role]:
        result = await self._session.execute(select(Role).order_by(Role.code))
        return list(result.scalars().all())


class PermissionRepository(BaseRepository[Permission]):
    """Data access for permissions."""

    model = Permission

    async def get_by_code(self, code: str) -> Permission | None:
        result = await self._session.execute(select(Permission).where(Permission.code == code))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Permission]:
        result = await self._session.execute(select(Permission).order_by(Permission.code))
        return list(result.scalars().all())


class RolePermissionRepository(BaseRepository[RolePermission]):
    """Data access for role-permission assignments."""

    model = RolePermission

    async def get_assignment(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> RolePermission | None:
        result = await self._session.execute(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )
        return result.scalar_one_or_none()

    async def remove_assignment(self, role_id: uuid.UUID, permission_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )


class AuthorizationRepository:
    """Efficient read queries for a user's active role permissions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_role(self, user_id: uuid.UUID) -> Role | None:
        result = await self._session.execute(
            select(Role)
            .join(User, User.role_id == Role.id)
            .where(
                User.id == user_id,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                Role.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_user_permission_codes(self, user_id: uuid.UUID) -> set[str]:
        result = await self._session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(User, User.role_id == Role.id)
            .where(
                User.id == user_id,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                Role.is_active.is_(True),
            )
        )
        return set(result.scalars().all())

    async def get_role_permission_codes(self, role_id: uuid.UUID) -> set[str]:
        """Return permission codes assigned to a role without lazy loading."""
        result = await self._session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        )
        return set(result.scalars().all())

    async def get_role_permissions(self, role_id: uuid.UUID) -> list[Permission]:
        result = await self._session.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
            .order_by(Permission.code)
        )
        return list(result.scalars().all())
