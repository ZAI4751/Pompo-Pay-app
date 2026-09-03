"""Merchant and branch administration with explicit tenant enforcement."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Branch, Merchant, Till, User
from app.repositories.organization import BranchRepository, MerchantRepository, TillRepository
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
        self._tills = TillRepository(session)
        self._authorization = AuthorizationService(AuthorizationRepository(session))

    async def get_merchant_access(self, actor: User) -> dict[str, Any]:
        """Authoritatively evaluate whether the actor can operate in Merchant Mode.

        Returns allowed=False with empty resource lists if the user is an
        ordinary customer or not affiliated with an active merchant.
        """
        is_admin = await self._is_platform_admin(actor)
        user_perms = await self._authorization.get_user_permissions(actor)

        # Platform admin does not automatically imply merchant access: an explicit merchant affiliation is required
        if actor.merchant_id is None:
            return {
                "allowed": False,
                "reason": "Account is not associated with any merchant organization",
                "can_generate_qr": False,
                "merchant": None,
                "merchants": [],
                "branches": [],
                "tills": [],
                "operating_branch_id": None,
                "operating_till_id": None,
                "permissions": sorted(user_perms) if is_admin else [],
            }

        can_generate_qr = "qr:create" in user_perms or is_admin
        target_merchant = await self._merchants.get_active(actor.merchant_id)
        merchants = [target_merchant] if target_merchant is not None else []

        if target_merchant is None or not target_merchant.is_active:
            return {
                "allowed": False,
                "reason": "Merchant organization is inactive or not found",
                "can_generate_qr": False,
                "merchant": None,
                "merchants": [],
                "branches": [],
                "tills": [],
                "operating_branch_id": None,
                "operating_till_id": None,
                "permissions": sorted(user_perms),
            }

        branch_scope = actor.branch_id if not is_admin and actor.branch_id else None
        branches = await self._branches.list_active(target_merchant.id, branch_scope)

        tills: list[Till] = []
        for branch in branches:
            branch_tills = await self._tills.list_active(branch.id)
            for t in branch_tills:
                t.branch = branch
                tills.append(t)

        operating_branch_id = actor.branch_id or (branches[0].id if branches else None)
        operating_till_id = None
        for t in tills:
            if t.branch_id == operating_branch_id and t.is_active:
                operating_till_id = t.id
                break
        if operating_till_id is None and tills:
            operating_till_id = tills[0].id

        return {
            "allowed": True,
            "reason": None,
            "can_generate_qr": can_generate_qr,
            "merchant": target_merchant,
            "merchants": merchants,
            "branches": branches,
            "tills": [
                {
                    "id": t.id,
                    "branch_id": t.branch_id,
                    "merchant_id": target_merchant.id,
                    "code": t.code,
                    "name": t.name,
                    "is_active": t.is_active,
                }
                for t in tills
            ],
            "operating_branch_id": operating_branch_id,
            "operating_till_id": operating_till_id,
            "permissions": sorted(user_perms),
        }

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

    async def list_tills(self, actor: User, branch_id: uuid.UUID) -> list[Till]:
        await self._require(actor, "tills:read")
        branch = await self._get_branch_in_scope(actor, branch_id)
        tills = await self._tills.list_active(branch.id)
        for till in tills:
            till.branch = branch
        return tills

    async def get_till(self, actor: User, till_id: uuid.UUID) -> Till:
        await self._require(actor, "tills:read")
        return await self._get_till_in_scope(actor, till_id)

    async def create_till(
        self, actor: User, branch_id: uuid.UUID, values: dict[str, Any]
    ) -> Till:
        await self._require(actor, "tills:create")
        branch = await self._get_branch_in_scope(actor, branch_id)
        till = Till(branch_id=branch.id, **values)
        self._session.add(till)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise OrganizationConflictError("Till code already exists on this branch") from exc
        await self._audit(
            actor,
            "till_created",
            till.id,
            None,
            {
                "branch_id": str(branch.id),
                "merchant_id": str(branch.merchant_id),
                "code": till.code,
                "name": till.name,
            },
        )
        await self._session.commit()
        till.branch = branch
        return till

    async def update_till(
        self, actor: User, till_id: uuid.UUID, values: dict[str, Any]
    ) -> Till:
        await self._require(actor, "tills:update")
        if "branch_id" in values or "code" in values:
            raise OrganizationForbiddenError("Till branch and code cannot be reassigned")
        till = await self._get_till_in_scope(actor, till_id)
        before = {key: getattr(till, key) for key in values}
        for key, value in values.items():
            setattr(till, key, value)
        await self._audit(actor, "till_updated", till.id, before, values)
        await self._session.commit()
        return till

    async def delete_till(self, actor: User, till_id: uuid.UUID) -> None:
        await self._require(actor, "tills:delete")
        till = await self._get_till_in_scope(actor, till_id)
        till.is_active = False
        await self._tills.soft_delete(till)
        await self._audit(
            actor, "till_deactivated", till.id, {"is_active": True}, {"is_active": False}
        )
        await self._session.commit()

    async def _get_till_in_scope(self, actor: User, till_id: uuid.UUID) -> Till:
        till = await self._tills.get_active(till_id)
        if till is None:
            raise OrganizationNotFoundError("Till not found")
        branch = await self._branches.get_active(till.branch_id)
        if branch is None:
            raise OrganizationNotFoundError("Till not found")
        await self._check_merchant_scope(actor, branch.merchant_id, branch.id)
        till.branch = branch
        return till

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
        if actor.merchant_id != merchant_id:
            raise OrganizationForbiddenError("Resource is outside actor scope")
        if actor.branch_id is not None and branch_id is not None and actor.branch_id != branch_id:
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
