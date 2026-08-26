"""Authorization decisions built on the Phase 1 RBAC data model."""

from __future__ import annotations

import uuid

from app.core.logging import get_logger
from app.models.user import Role, User
from app.repositories.rbac import AuthorizationRepository

logger = get_logger(__name__)


class AuthorizationDeniedError(Exception):
    """Raised when an authenticated principal lacks an authorization grant."""


class AuthorizationService:
    """Resolve permissions and enforce authorization policy for a request."""

    def __init__(self, repository: AuthorizationRepository) -> None:
        self._repository = repository

    async def get_user_role(self, user: User) -> Role | None:
        """Return the user's active role, or none when the account is not usable."""
        if not user.is_active or user.is_deleted:
            return None
        return await self._repository.get_user_role(user.id)

    async def get_user_permissions(self, user: User) -> set[str]:
        """Return effective permission codes for the user's active role."""
        if not user.is_active or user.is_deleted:
            return set()
        return await self._repository.get_user_permission_codes(user.id)

    async def get_role_permissions(self, role_id: uuid.UUID) -> set[str]:
        """Return permission codes assigned to a role."""
        return await self._repository.get_role_permission_codes(role_id)

    async def has_permission(self, user: User, permission_code: str) -> bool:
        """Return whether an active user has the exact permission code."""
        return permission_code in await self.get_user_permissions(user)

    async def require_permission(self, user: User, permission_code: str) -> User:
        """Require an exact permission and return the authenticated principal."""
        if not await self.has_permission(user, permission_code):
            logger.warning(
                "authorization_denied",
                user_id=str(user.id),
                permission=permission_code,
            )
            raise AuthorizationDeniedError(permission_code)
        return user

    async def can_grant_permission(self, actor: User, permission_code: str) -> bool:
        """Allow grant delegation only for permissions the actor already has."""
        return await self.has_permission(actor, permission_code)

    async def can_assign_role(self, actor: User, target_role: Role) -> bool:
        """Prevent role escalation by requiring authority over every target grant."""
        if not target_role.is_active:
            return False
        is_platform_admin = await self._is_platform_admin(actor)
        if target_role.is_system_role:
            return is_platform_admin

        actor_permissions = await self.get_user_permissions(actor)
        target_permissions = await self._repository.get_role_permission_codes(target_role.id)
        return target_permissions.issubset(actor_permissions)

    async def _is_platform_admin(self, user: User) -> bool:
        role = await self.get_user_role(user)
        return role is not None and role.code == "platform_admin"

    async def can_access_scope(
        self,
        user: User,
        merchant_id: uuid.UUID | None = None,
        branch_id: uuid.UUID | None = None,
    ) -> bool:
        """Check current tenant scope without granting cross-merchant access by UUID."""
        has_merchant_access = await self.has_permission(user, "merchants:read")
        is_platform_admin = await self._is_platform_admin(user)
        if not has_merchant_access and not is_platform_admin:
            return False
        if is_platform_admin:
            return True
        if merchant_id is not None and user.merchant_id != merchant_id:
            return False
        return branch_id is None or user.branch_id == branch_id
