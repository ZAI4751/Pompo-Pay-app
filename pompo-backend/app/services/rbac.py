"""RBAC administration business rules."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Permission, Role, RolePermission, User
from app.permissions.catalog import SYSTEM_ROLES
from app.repositories.rbac import (
    AuthorizationRepository,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
)
from app.repositories.user import UserRepository
from app.services.authorization import AuthorizationService


class RBACError(Exception):
    """Base class for expected RBAC administration failures."""


class RBACNotFoundError(RBACError):
    """An RBAC resource does not exist."""


class RBACConflictError(RBACError):
    """An RBAC operation conflicts with current state."""


class RBACForbiddenError(RBACError):
    """The actor cannot perform the requested RBAC operation."""


class RBACService:
    """Own persistence and security rules for RBAC administration."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._roles = RoleRepository(session)
        self._permissions = PermissionRepository(session)
        self._assignments = RolePermissionRepository(session)
        self._users = UserRepository(session)
        self._authorization = AuthorizationService(AuthorizationRepository(session))

    async def list_roles(self) -> list[Role]:
        return await self._roles.list_all()

    async def get_role(self, role_id: uuid.UUID) -> Role:
        role = await self._roles.get_by_id(role_id)
        if role is None:
            raise RBACNotFoundError("Role not found")
        return role

    async def get_role_permission_codes(self, role_id: uuid.UUID) -> list[str]:
        await self.get_role(role_id)
        codes = await self._authorization.get_role_permissions(role_id)
        return sorted(codes)

    async def list_permissions(self) -> list[Permission]:
        return await self._permissions.list_all()

    async def get_permission(self, permission_id: uuid.UUID) -> Permission:
        permission = await self._permissions.get_by_id(permission_id)
        if permission is None:
            raise RBACNotFoundError("Permission not found")
        return permission

    async def create_role(self, actor: User, code: str, name: str, description: str | None) -> Role:
        await self._require_actor_permission(actor, "roles:create")
        if code in SYSTEM_ROLES:
            raise RBACForbiddenError("System role codes are reserved")
        role = Role(code=code, name=name, description=description, is_system_role=False)
        self._session.add(role)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise RBACConflictError("Role code already exists") from exc
        await self._audit(actor, "role_created", role.id, None, {"code": code})
        await self._session.commit()
        return role

    async def update_role(
        self,
        actor: User,
        role_id: uuid.UUID,
        name: str | None,
        description: str | None,
        is_active: bool | None,
    ) -> Role:
        await self._require_actor_permission(actor, "roles:update")
        role = await self.get_role(role_id)
        if role.is_system_role:
            raise RBACForbiddenError("System roles are protected")
        before = {"name": role.name, "description": role.description, "is_active": role.is_active}
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        if is_active is not None:
            role.is_active = is_active
        await self._audit(
            actor,
            "role_updated",
            role.id,
            before,
            {"name": role.name, "description": role.description, "is_active": role.is_active},
        )
        await self._session.commit()
        return role

    async def delete_role(self, actor: User, role_id: uuid.UUID) -> None:
        await self._require_actor_permission(actor, "roles:delete")
        role = await self.get_role(role_id)
        if role.is_system_role:
            raise RBACForbiddenError("System roles are protected")
        if not role.is_active:
            return
        role.is_active = False
        await self._audit(
            actor, "role_deactivated", role.id, {"is_active": True}, {"is_active": False}
        )
        await self._session.commit()

    async def grant_permission(
        self, actor: User, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> RolePermission:
        await self._require_actor_permission(actor, "role_permissions:grant")
        role = await self.get_role(role_id)
        permission = await self.get_permission(permission_id)
        if not role.is_active or role.is_system_role:
            raise RBACForbiddenError("Protected or inactive roles cannot be changed")
        if not await self._authorization.can_grant_permission(actor, permission.code):
            raise RBACForbiddenError("Permission exceeds actor authority")
        if await self._assignments.get_assignment(role.id, permission.id) is not None:
            raise RBACConflictError("Permission is already assigned")
        assignment = RolePermission(
            role_id=role.id, permission_id=permission.id, granted_at=datetime.now(UTC)
        )
        self._session.add(assignment)
        await self._session.flush()
        await self._audit(
            actor, "permission_granted", role.id, None, {"permission_id": str(permission.id)}
        )
        await self._session.commit()
        return assignment

    async def revoke_permission(
        self, actor: User, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> None:
        await self._require_actor_permission(actor, "role_permissions:revoke")
        role = await self.get_role(role_id)
        permission = await self.get_permission(permission_id)
        if role.is_system_role:
            raise RBACForbiddenError("System roles are protected")
        if not await self._authorization.can_grant_permission(actor, permission.code):
            raise RBACForbiddenError("Permission exceeds actor authority")
        if await self._assignments.get_assignment(role.id, permission.id) is None:
            raise RBACNotFoundError("Permission assignment not found")
        await self._assignments.remove_assignment(role.id, permission.id)
        await self._audit(
            actor, "permission_revoked", role.id, {"permission_id": str(permission.id)}, None
        )
        await self._session.commit()

    async def assign_role(self, actor: User, user_id: uuid.UUID, role_id: uuid.UUID) -> User:
        await self._require_actor_permission(actor, "users:roles:assign")
        user = await self._users.get_by_id(user_id)
        role = await self.get_role(role_id)
        if user is None or user.is_deleted:
            raise RBACNotFoundError("User not found")
        if not user.is_active:
            raise RBACForbiddenError("Inactive users cannot receive roles")
        if not await self._authorization.can_assign_role(actor, role):
            raise RBACForbiddenError("Role exceeds actor authority")
        if user.merchant_id != actor.merchant_id and not await self._authorization.can_access_scope(
            actor, user.merchant_id
        ):
            raise RBACForbiddenError("User is outside actor scope")
        before = str(user.role_id)
        user.role_id = role.id
        await self._audit(
            actor, "user_role_assigned", user.id, {"role_id": before}, {"role_id": str(role.id)}
        )
        await self._session.commit()
        return user

    async def remove_role(self, actor: User, user_id: uuid.UUID) -> None:
        await self._require_actor_permission(actor, "users:roles:revoke")
        user = await self._users.get_by_id(user_id)
        if user is None or user.is_deleted:
            raise RBACNotFoundError("User not found")
        if user.id == actor.id:
            raise RBACForbiddenError("Users cannot remove their own role")
        if user.merchant_id != actor.merchant_id and not await self._authorization.can_access_scope(
            actor, user.merchant_id
        ):
            raise RBACForbiddenError("User is outside actor scope")
        raise RBACConflictError("Users must retain one role")

    async def _audit(
        self,
        actor: User,
        action: str,
        entity_id: uuid.UUID,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=actor.id,
                merchant_id=actor.merchant_id,
                action=action,
                entity_type="rbac",
                entity_id=str(entity_id),
                before_state=before,
                after_state=after,
            )
        )

    async def _require_actor_permission(self, actor: User, permission_code: str) -> None:
        if not await self._authorization.has_permission(actor, permission_code):
            raise RBACForbiddenError("Insufficient authority")
