"""Database access for the payment core."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.enums import ProviderCode
from app.models.payment import PaymentAttempt, PaymentProvider, Transaction
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    model = Transaction

    def _detail_query(self):
        return select(Transaction).options(
            selectinload(Transaction.attempts),
            selectinload(Transaction.merchant),
            selectinload(Transaction.branch),
            selectinload(Transaction.till),
        )

    async def get_active_by_reference(self, reference: str) -> Transaction | None:
        result = await self._session.execute(
            self._detail_query().where(
                Transaction.reference == reference,
                Transaction.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency(
        self, merchant_id: uuid.UUID, idempotency_key: str
    ) -> Transaction | None:
        result = await self._session.execute(
            select(Transaction)
            .where(
                Transaction.merchant_id == merchant_id,
                Transaction.idempotency_key == idempotency_key,
            )
            .options(selectinload(Transaction.attempts))
        )
        return result.scalar_one_or_none()

    async def list_for_merchant(
        self,
        merchant_id: uuid.UUID,
        *,
        branch_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        query = (
            self._detail_query()
            .where(
                Transaction.merchant_id == merchant_id,
                Transaction.deleted_at.is_(None),
            )
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if branch_id is not None:
            query = query.where(Transaction.branch_id == branch_id)
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def list_initiated_by(
        self,
        cashier_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        result = await self._session.execute(
            self._detail_query()
            .where(
                Transaction.cashier_id == cashier_id,
                Transaction.deleted_at.is_(None),
            )
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().unique().all())


class PaymentProviderRepository(BaseRepository[PaymentProvider]):
    model = PaymentProvider

    async def get_active_by_code(self, code: str) -> PaymentProvider | None:
        try:
            provider_code = ProviderCode(code)
        except ValueError:
            return None
        result = await self._session.execute(
            select(PaymentProvider).where(
                PaymentProvider.code == provider_code,
                PaymentProvider.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> PaymentProvider | None:
        try:
            provider_code = ProviderCode(code)
        except ValueError:
            return None
        result = await self._session.execute(
            select(PaymentProvider).where(PaymentProvider.code == provider_code)
        )
        return result.scalar_one_or_none()

    async def list_catalog(self) -> list[PaymentProvider]:
        result = await self._session.execute(
            select(PaymentProvider).order_by(PaymentProvider.priority, PaymentProvider.code)
        )
        return list(result.scalars().all())


class PaymentAttemptRepository(BaseRepository[PaymentAttempt]):
    model = PaymentAttempt

    async def next_number(self, transaction_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(PaymentAttempt.attempt_number)
            .where(PaymentAttempt.transaction_id == transaction_id)
            .order_by(PaymentAttempt.attempt_number.desc())
            .limit(1)
        )
        current = result.scalar_one_or_none()
        return 1 if current is None else current + 1

    async def find_by_provider_reference(
        self, provider_id: uuid.UUID, provider_reference: str
    ) -> PaymentAttempt | None:
        result = await self._session.execute(
            select(PaymentAttempt)
            .where(
                PaymentAttempt.provider_id == provider_id,
                PaymentAttempt.provider_reference == provider_reference,
            )
            .order_by(PaymentAttempt.attempt_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
