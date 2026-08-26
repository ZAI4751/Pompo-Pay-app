"""Merchant and branch administration with explicit tenant enforcement."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Branch, Merchant, User
from app.repositories.organization import BranchRepository, MerchantRepository
from app.repositories.rbac import AuthorizationRepository
from app.services.authorization import AuthorizationService


class OrganizationError(Exception):
    """Base class for organization administration failures."""


class OrganizationNotFoundError(OrganizationError):
    pass


class OrganizationConflictError(OrganizationError):
    pass


class OrganizationForbiddenError(OrganizationError):
    pass


class OrganizationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._merchants = MerchantRepository(session)
        self._branches = BranchRepository(session)
        self._authorization = AuthorizationService(AuthorizationRepository(session))

    async def list_merchants(self, actor: User) -> list[Merchant]:
        await self._require(actor, "merchants:read")
        scope = None if await self._is_platform_admin(actor) else actor.merchant_id
        if scope is None and not await self._is_platform_admin(actor):
            raise OrganizationForbiddenError("Actor has no merchant scope")
        return await self._merchants.list_active(scope)

    async def get_merchant(self, actor: User, merchant_id: uuid.UUID) -> Merchant:
        await self._require(actor, "merchants:read")
        merchant = await self._merchants.get_active(merchant_id)
        if merchant is None:
            raise OrganizationNotFoundError("Merchant not found")
        await self._check_merchant_scope(actor, merchant.id)
        return merchant

    async def create_merchant(self, actor: User, values: dict[str, Any]) -> Merchant:
        await self._require(actor, "merchants:create")
        if not await self._is_platform_admin(actor):
            raise OrganizationForbiddenError("Only platform administrators can create merchants")
        merchant = Merchant(**values)
        self._session.add(merchant)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise OrganizationConflictError("Merchant contact email already exists") from exc
        await self._audit(actor, "merchant_created", merchant.id, None, {"name": merchant.name})
        await self._session.commit()
        return merchant

    async def update_merchant(
        self, actor: User, merchant_id: uuid.UUID, values: dict[str, Any]
    ) -> Merchant:
        await self._require(actor, "merchants:update")
        merchant = await self.get_merchant(actor, merchant_id)
        before = {key: getattr(merchant, key) for key in values}
        for key, value in values.items():
            setattr(merchant, key, value)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise OrganizationConflictError("Merchant contact email already exists") from exc
        await self._audit(actor, "merchant_updated", merchant.id, before, values)
        await self._session.commit()
        return merchant

    async def delete_merchant(self, actor: User, merchant_id: uuid.UUID) -> None:
        await self._require(actor, "merchants:delete")
        merchant = await self.get_merchant(actor, merchant_id)
        merchant.is_active = False
        await self._merchants.soft_delete(merchant)
        await self._audit(
            actor, "merchant_deactivated", merchant.id, {"is_active": True}, {"is_active": False}
        )
        await self._session.commit()

    async def list_branches(self, actor: User, merchant_id: uuid.UUID) -> list[Branch]:
        await self._require(actor, "branches:read")
        await self._check_merchant_scope(actor, merchant_id)
        branch_id = (
            actor.branch_id
            if not await self._is_platform_admin(actor) and actor.branch_id
            else None
        )
        return await self._branches.list_active(merchant_id, branch_id)

    async def create_branch(
        self, actor: User, merchant_id: uuid.UUID, values: dict[str, Any]
    ) -> Branch:
        await self._require(actor, "branches:create")
        if await self._merchants.get_active(merchant_id) is None:
            raise OrganizationNotFoundError("Merchant not found")
        await self._check_merchant_scope(actor, merchant_id)
        if not await self._is_platform_admin(actor) and actor.branch_id is not None:
            raise OrganizationForbiddenError("Branch managers cannot create branches")
        branch = Branch(merchant_id=merchant_id, **values)
        self._session.add(branch)
        await self._session.flush()
        await self._audit(
            actor,
            "branch_created",
            branch.id,
            None,
            {"merchant_id": str(merchant_id), "name": branch.name},
        )
        await self._session.commit()
        return branch

    async def update_branch(
        self, actor: User, branch_id: uuid.UUID, values: dict[str, Any]
    ) -> Branch:
        await self._require(actor, "branches:update")
        branch = await self._get_branch_in_scope(actor, branch_id)
        before = {key: getattr(branch, key) for key in values}
        for key, value in values.items():
            setattr(branch, key, value)
        await self._audit(actor, "branch_updated", branch.id, before, values)
        await self._session.commit()
        return branch

    async def delete_branch(self, actor: User, branch_id: uuid.UUID) -> None:
        await self._require(actor, "branches:delete")
        branch = await self._get_branch_in_scope(actor, branch_id)
        await self._branches.soft_delete(branch)
        branch.is_active = False
        await self._audit(
            actor, "branch_deactivated", branch.id, {"is_active": True}, {"is_active": False}
        )
        await self._session.commit()

    async def _get_branch_in_scope(self, actor: User, branch_id: uuid.UUID) -> Branch:
        branch = await self._branches.get_active(branch_id)
        if branch is None:
            raise OrganizationNotFoundError("Branch not found")
        await self._check_merchant_scope(actor, branch.merchant_id, branch.id)
        return branch

    async def _check_merchant_scope(
        self, actor: User, merchant_id: uuid.UUID, branch_id: uuid.UUID | None = None
    ) -> None:
        if await self._is_platform_admin(actor):
            return
        if actor.merchant_id != merchant_id or (
            branch_id is not None and actor.branch_id != branch_id
        ):
            raise OrganizationForbiddenError("Resource is outside actor scope")

    async def _is_platform_admin(self, actor: User) -> bool:
        role = await self._authorization.get_user_role(actor)
        return role is not None and role.code == "platform_admin"

    async def _require(self, actor: User, permission: str) -> None:
        if not await self._authorization.has_permission(actor, permission):
            raise OrganizationForbiddenError("Insufficient authority")

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
                entity_type="organization",
                entity_id=str(entity_id),
                before_state=before,
                after_state=after,
            )
        )
