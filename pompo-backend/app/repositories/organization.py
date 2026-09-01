"""Tenant-scoped queries for merchants, branches, and tills."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.organization import Branch, Merchant, Till
from app.repositories.base import BaseRepository


class MerchantRepository(BaseRepository[Merchant]):
    model = Merchant

    async def list_active(self, merchant_id: uuid.UUID | None = None) -> list[Merchant]:
        statement = select(Merchant).where(
            Merchant.deleted_at.is_(None), Merchant.is_active.is_(True)
        )
        if merchant_id is not None:
            statement = statement.where(Merchant.id == merchant_id)
        result = await self._session.execute(statement.order_by(Merchant.name))
        return list(result.scalars().all())

    async def get_active(self, merchant_id: uuid.UUID) -> Merchant | None:
        result = await self._session.execute(
            select(Merchant).where(
                Merchant.id == merchant_id,
                Merchant.deleted_at.is_(None),
                Merchant.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()


class BranchRepository(BaseRepository[Branch]):
    model = Branch

    async def list_active(
        self, merchant_id: uuid.UUID, branch_id: uuid.UUID | None = None
    ) -> list[Branch]:
        statement = select(Branch).where(
            Branch.merchant_id == merchant_id,
            Branch.deleted_at.is_(None),
            Branch.is_active.is_(True),
        )
        if branch_id is not None:
            statement = statement.where(Branch.id == branch_id)
        result = await self._session.execute(statement.order_by(Branch.name))
        return list(result.scalars().all())

    async def get_active(self, branch_id: uuid.UUID) -> Branch | None:
        result = await self._session.execute(
            select(Branch).where(
                Branch.id == branch_id,
                Branch.deleted_at.is_(None),
                Branch.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()


class TillRepository(BaseRepository[Till]):
    model = Till

    async def list_active(self, branch_id: uuid.UUID) -> list[Till]:
        statement = select(Till).where(
            Till.branch_id == branch_id,
            Till.deleted_at.is_(None),
            Till.is_active.is_(True),
        )
        result = await self._session.execute(statement.order_by(Till.code))
        return list(result.scalars().all())

    async def get_active(self, till_id: uuid.UUID) -> Till | None:
        result = await self._session.execute(
            select(Till).where(
                Till.id == till_id,
                Till.deleted_at.is_(None),
                Till.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()
