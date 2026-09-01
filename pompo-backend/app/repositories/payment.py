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

    async def get_active_by_reference(self, reference: str) -> Transaction | None:
        result = await self._session.execute(
            select(Transaction)
            .where(
                Transaction.reference == reference,
                Transaction.deleted_at.is_(None),
            )
            .options(selectinload(Transaction.attempts))
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
