"""Database access for the payment core."""

from __future__ import annotations

import uuid

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.models.enums import ProviderCode, TransactionStatus
from app.models.organization import Merchant
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
            selectinload(Transaction.qr_code),
            selectinload(Transaction.receipt),
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
        status: str | None = None,
        reference: str | None = None,
        query_text: str | None = None,
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
        if status:
            query = query.where(Transaction.status == status)
        if reference:
            needle = f"%{reference.strip().lower()}%"
            query = query.where(func.lower(Transaction.reference).like(needle))
        if query_text:
            needle = f"%{query_text.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(Transaction.reference).like(needle),
                    func.lower(func.coalesce(Transaction.description, "")).like(needle),
                )
            )
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def list_initiated_by(
        self,
        cashier_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        merchant_id: uuid.UUID | None = None,
        status: str | None = None,
        reference: str | None = None,
        query_text: str | None = None,
        amount_min: Decimal | None = None,
        amount_max: Decimal | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> list[Transaction]:
        query = (
            self._detail_query()
            .where(
                Transaction.cashier_id == cashier_id,
                Transaction.deleted_at.is_(None),
            )
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if merchant_id is not None:
            query = query.where(Transaction.merchant_id == merchant_id)
        if status:
            query = query.where(Transaction.status == status)
        if reference:
            needle = f"%{reference.strip().lower()}%"
            query = query.where(func.lower(Transaction.reference).like(needle))
        if query_text:
            needle = f"%{query_text.strip().lower()}%"
            query = query.join(Merchant, Merchant.id == Transaction.merchant_id).where(
                or_(
                    func.lower(Transaction.reference).like(needle),
                    func.lower(Merchant.name).like(needle),
                    func.lower(func.coalesce(Transaction.description, "")).like(needle),
                )
            )
        if amount_min is not None:
            query = query.where(Transaction.amount >= amount_min)
        if amount_max is not None:
            query = query.where(Transaction.amount <= amount_max)
        if created_from is not None:
            query = query.where(Transaction.created_at >= created_from)
        if created_to is not None:
            query = query.where(Transaction.created_at <= created_to)
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def merchant_summary(
        self, merchant_id: uuid.UUID, *, since: datetime, branch_id: uuid.UUID | None = None
    ) -> tuple[int, Decimal, int]:
        filters = [
            Transaction.merchant_id == merchant_id,
            Transaction.deleted_at.is_(None),
            Transaction.status == TransactionStatus.SUCCESS,
            Transaction.completed_at >= since,
        ]
        if branch_id is not None:
            filters.append(Transaction.branch_id == branch_id)
        result = await self._session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Transaction.amount), 0),
            ).where(*filters)
        )
        count, total = result.one()
        all_success = await self._session.execute(
            select(func.count()).where(
                Transaction.merchant_id == merchant_id,
                Transaction.deleted_at.is_(None),
                Transaction.status == TransactionStatus.SUCCESS,
                *( [Transaction.branch_id == branch_id] if branch_id is not None else [] ),
            )
        )
        return int(count or 0), Decimal(str(total or 0)), int(all_success.scalar_one() or 0)

    async def customer_insights(
        self,
        cashier_id: uuid.UUID,
        *,
        week_start: datetime,
        month_start: datetime,
    ) -> dict[str, object]:
        async def _window(since: datetime) -> tuple[int, Decimal]:
            result = await self._session.execute(
                select(func.count(), func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.cashier_id == cashier_id,
                    Transaction.deleted_at.is_(None),
                    Transaction.status == TransactionStatus.SUCCESS,
                    Transaction.completed_at >= since,
                )
            )
            count, total = result.one()
            return int(count or 0), Decimal(str(total or 0))

        week_count, week_total = await _window(week_start)
        month_count, month_total = await _window(month_start)
        lifetime = await self._session.execute(
            select(func.count(), func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.cashier_id == cashier_id,
                Transaction.deleted_at.is_(None),
                Transaction.status == TransactionStatus.SUCCESS,
            )
        )
        life_count, life_total = lifetime.one()
        top = await self._session.execute(
            select(Merchant.id, Merchant.name, func.count().label("uses"))
            .join(Transaction, Transaction.merchant_id == Merchant.id)
            .where(
                Transaction.cashier_id == cashier_id,
                Transaction.deleted_at.is_(None),
                Transaction.status == TransactionStatus.SUCCESS,
                Merchant.deleted_at.is_(None),
            )
            .group_by(Merchant.id, Merchant.name)
            .order_by(func.count().desc())
            .limit(5)
        )
        return {
            "payments_this_week": week_count,
            "spent_this_week": week_total,
            "payments_this_month": month_count,
            "spent_this_month": month_total,
            "payment_count": int(life_count or 0),
            "spent_total": Decimal(str(life_total or 0)),
            "most_used_merchants": [
                {"merchant_id": row[0], "merchant_name": row[1], "payment_count": int(row[2])}
                for row in top.all()
            ],
        }


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
