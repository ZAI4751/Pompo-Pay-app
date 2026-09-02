"""Database access for settlement, pricing, and reconciliation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.enums import ReconciliationStatus, SettlementStatus, TransactionStatus
from app.models.payment import PaymentAttempt, Transaction
from app.models.settlement import (
    PricingSchedule,
    ReconciliationRecord,
    ReconciliationRun,
    Settlement,
    SettlementBatch,
)
from app.repositories.base import BaseRepository


def _scope_reconciliation_query(stmt, *, merchant_id: uuid.UUID | None, provider_id: uuid.UUID | None):
    if merchant_id is None and provider_id is None:
        return stmt
    stmt = stmt.outerjoin(Settlement, Settlement.id == ReconciliationRecord.settlement_id)
    if merchant_id is not None:
        stmt = stmt.where(
            (Settlement.merchant_id == merchant_id)
            | (
                ReconciliationRecord.transaction_id.in_(
                    select(Transaction.id).where(Transaction.merchant_id == merchant_id)
                )
            )
        )
    if provider_id is not None:
        stmt = stmt.where(
            (Settlement.provider_id == provider_id)
            | (
                ReconciliationRecord.settlement_id.is_(None)
                & ReconciliationRecord.transaction_id.in_(
                    select(Transaction.id).where(Transaction.provider_id == provider_id)
                )
            )
        )
    return stmt


class PricingScheduleRepository(BaseRepository[PricingSchedule]):
    model = PricingSchedule

    async def find_applicable(
        self,
        *,
        provider_id: uuid.UUID,
        merchant_id: uuid.UUID | None,
        currency: str,
    ) -> PricingSchedule | None:
        """Most specific active schedule: merchant+provider, merchant, provider, platform."""

        candidates = (
            await self._session.scalars(
                select(PricingSchedule).where(
                    PricingSchedule.is_active.is_(True),
                    PricingSchedule.currency == currency,
                )
            )
        ).all()
        ranked: list[tuple[int, PricingSchedule]] = []
        for schedule in candidates:
            if schedule.provider_id not in (None, provider_id):
                continue
            if schedule.merchant_id not in (None, merchant_id):
                continue
            score = 0
            if schedule.provider_id == provider_id:
                score += 2
            if merchant_id is not None and schedule.merchant_id == merchant_id:
                score += 4
            ranked.append((score, schedule))
        if not ranked:
            return None
        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked[0][1]


class SettlementBatchRepository(BaseRepository[SettlementBatch]):
    model = SettlementBatch

    async def get_by_provider_reference(
        self, provider_id: uuid.UUID, external_batch_reference: str
    ) -> SettlementBatch | None:
        result = await self._session.execute(
            select(SettlementBatch)
            .where(
                SettlementBatch.provider_id == provider_id,
                SettlementBatch.external_batch_reference == external_batch_reference,
            )
            .options(selectinload(SettlementBatch.settlements))
        )
        return result.scalar_one_or_none()

    async def get_by_public_identifier(self, public_identifier: str) -> SettlementBatch | None:
        result = await self._session.execute(
            select(SettlementBatch).where(SettlementBatch.public_identifier == public_identifier)
        )
        return result.scalar_one_or_none()

    async def list_batches(
        self,
        *,
        provider_id: uuid.UUID | None = None,
        merchant_id: uuid.UUID | None = None,
        settlement_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SettlementBatch]:
        stmt = select(SettlementBatch).order_by(SettlementBatch.created_at.desc())
        if provider_id is not None:
            stmt = stmt.where(SettlementBatch.provider_id == provider_id)
        if settlement_date is not None:
            stmt = stmt.where(SettlementBatch.settlement_date == settlement_date)
        if merchant_id is not None:
            stmt = (
                stmt.join(Settlement, Settlement.batch_id == SettlementBatch.id)
                .where(Settlement.merchant_id == merchant_id)
                .distinct()
            )
        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())


class SettlementRepository(BaseRepository[Settlement]):
    model = Settlement

    async def get_by_provider_reference(
        self, provider_id: uuid.UUID, provider_settlement_reference: str
    ) -> Settlement | None:
        result = await self._session.execute(
            select(Settlement)
            .where(
                Settlement.provider_id == provider_id,
                Settlement.provider_settlement_reference == provider_settlement_reference,
            )
            .options(selectinload(Settlement.reconciliation))
        )
        return result.scalar_one_or_none()

    async def get_with_relations(self, settlement_id: uuid.UUID) -> Settlement | None:
        result = await self._session.execute(
            select(Settlement)
            .where(Settlement.id == settlement_id)
            .options(
                selectinload(Settlement.reconciliation),
                selectinload(Settlement.batch),
                selectinload(Settlement.transaction),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_transaction(self, transaction_id: uuid.UUID) -> list[Settlement]:
        result = await self._session.execute(
            select(Settlement).where(Settlement.transaction_id == transaction_id)
        )
        return list(result.scalars().all())

    async def list_settlements(
        self,
        *,
        provider_id: uuid.UUID | None = None,
        merchant_id: uuid.UUID | None = None,
        batch_id: uuid.UUID | None = None,
        status: SettlementStatus | None = None,
        settlement_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Settlement]:
        stmt = (
            select(Settlement)
            .options(selectinload(Settlement.reconciliation))
            .order_by(Settlement.received_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if provider_id is not None:
            stmt = stmt.where(Settlement.provider_id == provider_id)
        if merchant_id is not None:
            stmt = stmt.where(Settlement.merchant_id == merchant_id)
        if batch_id is not None:
            stmt = stmt.where(Settlement.batch_id == batch_id)
        if status is not None:
            stmt = stmt.where(Settlement.status == status)
        if settlement_date is not None:
            stmt = stmt.where(Settlement.settlement_date == settlement_date)
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def list_in_window(
        self,
        *,
        provider_id: uuid.UUID | None,
        window_start: datetime,
        window_end: datetime,
        merchant_id: uuid.UUID | None = None,
    ) -> list[Settlement]:
        stmt = (
            select(Settlement)
            .options(selectinload(Settlement.reconciliation), selectinload(Settlement.transaction))
            .where(
                Settlement.received_at >= window_start,
                Settlement.received_at < window_end,
            )
        )
        if provider_id is not None:
            stmt = stmt.where(Settlement.provider_id == provider_id)
        if merchant_id is not None:
            stmt = stmt.where(Settlement.merchant_id == merchant_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def batch_totals(self, batch_id: uuid.UUID) -> tuple[int, Decimal, Decimal, Decimal, Decimal]:
        result = await self._session.execute(
            select(
                func.count(Settlement.id),
                func.coalesce(func.sum(Settlement.gross_amount), 0),
                func.coalesce(func.sum(Settlement.provider_fee), 0),
                func.coalesce(func.sum(Settlement.pompo_fee), 0),
                func.coalesce(func.sum(Settlement.merchant_net), 0),
            ).where(Settlement.batch_id == batch_id)
        )
        row = result.one()
        return int(row[0] or 0), row[1], row[2], row[3], row[4]

    async def summary(
        self, *, merchant_id: uuid.UUID | None = None, provider_id: uuid.UUID | None = None
    ) -> dict[str, Decimal | int]:
        stmt = select(
            func.count(Settlement.id),
            func.coalesce(func.sum(Settlement.gross_amount), 0),
            func.coalesce(func.sum(Settlement.provider_fee), 0),
            func.coalesce(func.sum(Settlement.pompo_fee), 0),
            func.coalesce(func.sum(Settlement.merchant_net), 0),
        )
        if merchant_id is not None:
            stmt = stmt.where(Settlement.merchant_id == merchant_id)
        if provider_id is not None:
            stmt = stmt.where(Settlement.provider_id == provider_id)
        row = (await self._session.execute(stmt)).one()
        return {
            "total_settlements": int(row[0] or 0),
            "total_gross": row[1],
            "total_provider_fees": row[2],
            "total_pompo_fees": row[3],
            "total_merchant_net": row[4],
        }


class ReconciliationRecordRepository(BaseRepository[ReconciliationRecord]):
    model = ReconciliationRecord

    async def get_by_settlement(self, settlement_id: uuid.UUID) -> ReconciliationRecord | None:
        result = await self._session.execute(
            select(ReconciliationRecord).where(ReconciliationRecord.settlement_id == settlement_id)
        )
        return result.scalar_one_or_none()

    async def get_missing_settlement(self, transaction_id: uuid.UUID) -> ReconciliationRecord | None:
        result = await self._session.execute(
            select(ReconciliationRecord).where(
                ReconciliationRecord.transaction_id == transaction_id,
                ReconciliationRecord.settlement_id.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_with_relations(self, record_id: uuid.UUID) -> ReconciliationRecord | None:
        result = await self._session.execute(
            select(ReconciliationRecord)
            .where(ReconciliationRecord.id == record_id)
            .options(
                selectinload(ReconciliationRecord.settlement),
                selectinload(ReconciliationRecord.transaction),
                selectinload(ReconciliationRecord.run),
            )
        )
        return result.scalar_one_or_none()

    async def list_records(
        self,
        *,
        status: ReconciliationStatus | None = None,
        merchant_id: uuid.UUID | None = None,
        provider_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReconciliationRecord]:
        stmt = (
            select(ReconciliationRecord)
            .options(selectinload(ReconciliationRecord.settlement))
            .order_by(ReconciliationRecord.detected_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            stmt = stmt.where(ReconciliationRecord.status == status)
        if run_id is not None:
            stmt = stmt.where(ReconciliationRecord.run_id == run_id)
        stmt = _scope_reconciliation_query(stmt, merchant_id=merchant_id, provider_id=provider_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def status_counts(
        self, *, merchant_id: uuid.UUID | None = None, provider_id: uuid.UUID | None = None
    ) -> dict[str, int]:
        stmt = select(ReconciliationRecord.status, func.count(ReconciliationRecord.id)).group_by(
            ReconciliationRecord.status
        )
        stmt = _scope_reconciliation_query(stmt, merchant_id=merchant_id, provider_id=provider_id)
        rows = (await self._session.execute(stmt)).all()
        counts = {status.value: 0 for status in ReconciliationStatus}
        for status, count in rows:
            counts[status.value] = int(count)
        return counts

    async def discrepancy_total(
        self, *, merchant_id: uuid.UUID | None = None, provider_id: uuid.UUID | None = None
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(ReconciliationRecord.variance), 0)).where(
            ReconciliationRecord.status == ReconciliationStatus.DISCREPANCY
        )
        stmt = _scope_reconciliation_query(stmt, merchant_id=merchant_id, provider_id=provider_id)
        value = (await self._session.execute(stmt)).scalar_one()
        return value


class ReconciliationRunRepository(BaseRepository[ReconciliationRun]):
    model = ReconciliationRun

    async def list_runs(
        self,
        *,
        provider_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReconciliationRun]:
        stmt = (
            select(ReconciliationRun)
            .order_by(ReconciliationRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if provider_id is not None:
            stmt = stmt.where(ReconciliationRun.provider_id == provider_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


async def list_successful_transactions_without_settlement(
    session,
    *,
    provider_id: uuid.UUID | None,
    window_start: datetime,
    window_end: datetime,
    merchant_id: uuid.UUID | None = None,
) -> list[Transaction]:
    settled_ids = select(Settlement.transaction_id).where(Settlement.transaction_id.is_not(None))
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.attempts))
        .where(
            Transaction.status == TransactionStatus.SUCCESS,
            Transaction.deleted_at.is_(None),
            Transaction.completed_at.is_not(None),
            Transaction.completed_at >= window_start,
            Transaction.completed_at < window_end,
            Transaction.id.not_in(settled_ids),
        )
    )
    if provider_id is not None:
        stmt = stmt.where(Transaction.provider_id == provider_id)
    if merchant_id is not None:
        stmt = stmt.where(Transaction.merchant_id == merchant_id)
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def list_attempts_by_provider_reference(
    session,
    *,
    provider_id: uuid.UUID,
    provider_reference: str,
) -> list[PaymentAttempt]:
    result = await session.execute(
        select(PaymentAttempt)
        .options(selectinload(PaymentAttempt.transaction).selectinload(Transaction.attempts))
        .where(
            PaymentAttempt.provider_id == provider_id,
            PaymentAttempt.provider_reference == provider_reference,
        )
    )
    return list(result.scalars().unique().all())
