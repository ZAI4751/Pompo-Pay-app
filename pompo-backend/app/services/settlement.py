"""Settlement ingestion, matching, and reconciliation.

Settlement is not a payment engine. Reconciliation never mutates payment history.
PostgreSQL unique constraints are the financial identity authority.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import AuditLog, Transaction, User
from app.models.enums import (
    ReconciliationRunStatus,
    ReconciliationStatus,
    SettlementBatchStatus,
    SettlementStatus,
    UserRoleCode,
)
from app.models.settlement import (
    ReconciliationRecord,
    ReconciliationRun,
    Settlement,
    SettlementBatch,
)
from app.payments.credentials import resolve_provider_credentials
from app.payments.matching import classify, decide_identity
from app.payments.money import ZERO_MONEY, parse_money
from app.payments.pricing import apply_schedule
from app.payments.registry import ProviderRegistry
from app.payments.settlement import NormalizedSettlementBatch, NormalizedSettlementRecord
from app.repositories.payment import PaymentProviderRepository, TransactionRepository
from app.repositories.rbac import AuthorizationRepository
from app.repositories.settlement import (
    PricingScheduleRepository,
    ReconciliationRecordRepository,
    ReconciliationRunRepository,
    SettlementBatchRepository,
    SettlementRepository,
    list_attempts_by_provider_reference,
    list_successful_transactions_without_settlement,
)
from app.services.authorization import AuthorizationService

logger = get_logger(__name__)


class SettlementError(Exception):
    """Base class for settlement/reconciliation failures."""


class SettlementNotFoundError(SettlementError):
    pass


class SettlementForbiddenError(SettlementError):
    pass


class SettlementInvalidError(SettlementError):
    pass


class SettlementDuplicateError(SettlementError):
    def __init__(self, batch: SettlementBatch) -> None:
        super().__init__("Duplicate settlement batch")
        self.batch = batch


class SettlementSignatureError(SettlementError):
    pass


def _public_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex.upper()}"


class SettlementService:
    def __init__(
        self,
        session: AsyncSession,
        registry: ProviderRegistry | None = None,
    ) -> None:
        self._session = session
        self._batches = SettlementBatchRepository(session)
        self._settlements = SettlementRepository(session)
        self._pricing = PricingScheduleRepository(session)
        self._recon = ReconciliationRecordRepository(session)
        self._runs = ReconciliationRunRepository(session)
        self._providers = PaymentProviderRepository(session)
        self._transactions = TransactionRepository(session)
        self._authorization = AuthorizationService(AuthorizationRepository(session))
        self._registry = registry or ProviderRegistry()

    async def ingest_signed(
        self,
        provider_code: str,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> tuple[SettlementBatch, bool]:
        provider = await self._providers.get_by_code(provider_code)
        if provider is None:
            raise SettlementInvalidError("Unknown provider")
        if not provider.is_active:
            raise SettlementInvalidError("Provider is not active")
        adapter = self._registry.get_optional(provider_code)
        if adapter is None or not hasattr(adapter, "verify_settlement") or not hasattr(
            adapter, "parse_settlement"
        ):
            raise SettlementInvalidError("Provider does not support settlement ingestion")
        credentials = resolve_provider_credentials(
            provider_code, catalog_environment=provider.environment
        )
        verification = await adapter.verify_settlement(
            headers=headers, body=body, credentials=credentials
        )
        if not verification.verified:
            logger.warning(
                "settlement_rejected",
                provider=provider_code,
                reason=verification.failure_reason,
            )
            raise SettlementSignatureError(verification.failure_reason or "Invalid signature")
        try:
            normalized = await adapter.parse_settlement(headers=headers, body=body)
        except ValueError as exc:
            raise SettlementInvalidError(str(exc)) from exc
        return await self.ingest_normalized(provider_code, normalized)

    async def ingest_admin(
        self,
        actor: User,
        provider_code: str,
        payload: dict[str, Any],
    ) -> tuple[SettlementBatch, bool]:
        await self._require(actor, "settlements:create")
        import json

        from app.payments.settlement import parse_mock_settlement_body

        try:
            normalized = parse_mock_settlement_body(json.dumps(payload).encode())
        except ValueError as exc:
            raise SettlementInvalidError(str(exc)) from exc
        return await self.ingest_normalized(provider_code, normalized, actor=actor)

    async def ingest_normalized(
        self,
        provider_code: str,
        normalized: NormalizedSettlementBatch,
        *,
        actor: User | None = None,
    ) -> tuple[SettlementBatch, bool]:
        provider = await self._providers.get_by_code(provider_code)
        if provider is None:
            raise SettlementInvalidError("Unknown provider")

        existing = await self._batches.get_by_provider_reference(
            provider.id, normalized.external_batch_reference
        )
        if existing is not None:
            logger.info(
                "settlement_batch_deduplicated",
                provider=provider_code,
                batch_id=str(existing.id),
            )
            return existing, True

        received_at = datetime.now(UTC)
        batch = SettlementBatch(
            public_identifier=_public_id("BAT"),
            provider_id=provider.id,
            external_batch_reference=normalized.external_batch_reference,
            settlement_date=normalized.settlement_date,
            currency=normalized.currency,
            status=SettlementBatchStatus.PROCESSING,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(batch)
                await self._session.flush()
        except IntegrityError:
            duplicate = await self._batches.get_by_provider_reference(
                provider.id, normalized.external_batch_reference
            )
            if duplicate is not None:
                return duplicate, True
            raise

        await self._audit(
            actor,
            "settlement_received",
            "settlement_batch",
            batch.id,
            None,
            {
                "provider": provider_code,
                "external_batch_reference": normalized.external_batch_reference,
                "record_count": len(normalized.records),
            },
        )
        logger.info(
            "settlement_received",
            batch_id=str(batch.id),
            provider=provider_code,
            external_batch_reference=normalized.external_batch_reference,
        )

        for record in normalized.records:
            await self._ingest_record(batch, provider_code, record, received_at, actor)

        await self._refresh_batch_totals(batch)
        batch.status = SettlementBatchStatus.SETTLED
        batch.processed_at = datetime.now(UTC)
        await self._audit(
            actor,
            "settlement_processed",
            "settlement_batch",
            batch.id,
            None,
            {
                "record_count": batch.record_count,
                "total_gross": str(batch.total_gross),
                "total_merchant_net": str(batch.total_merchant_net),
            },
        )
        await self._session.commit()
        await self._session.refresh(batch)
        return batch, False

    async def _ingest_record(
        self,
        batch: SettlementBatch,
        provider_code: str,
        record: NormalizedSettlementRecord,
        received_at: datetime,
        actor: User | None,
    ) -> Settlement:
        existing = await self._settlements.get_by_provider_reference(
            batch.provider_id, record.provider_settlement_reference
        )
        if existing is not None:
            logger.info(
                "settlement_record_deduplicated",
                settlement_id=str(existing.id),
                provider_settlement_reference=record.provider_settlement_reference,
            )
            return existing

        identity_txn, identity_attempts = await self._lookup_identity(batch.provider_id, record)
        merchant_id = identity_txn.merchant_id if identity_txn is not None else None
        branch_id = identity_txn.branch_id if identity_txn is not None else None
        schedule = await self._pricing.find_applicable(
            provider_id=batch.provider_id,
            merchant_id=merchant_id,
            currency=record.currency,
        )
        expected = apply_schedule(record.gross_amount, schedule, record.currency)
        provider_fee = (
            parse_money(record.provider_fee) if record.provider_fee is not None else expected.provider_cost
        )
        pompo_fee = expected.pompo_fee
        net = parse_money(record.gross_amount - provider_fee - pompo_fee)

        settlement = Settlement(
            public_identifier=_public_id("SET"),
            batch_id=batch.id,
            provider_id=batch.provider_id,
            provider_settlement_reference=record.provider_settlement_reference,
            payment_reference=record.payment_reference,
            provider_transaction_reference=record.provider_transaction_reference,
            merchant_id=merchant_id,
            branch_id=branch_id,
            gross_amount=record.gross_amount,
            provider_fee=provider_fee,
            pompo_fee=pompo_fee,
            merchant_net=net,
            currency=record.currency,
            status=SettlementStatus.PROCESSING,
            settlement_date=record.settlement_date,
            received_at=received_at,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(settlement)
                await self._session.flush()
        except IntegrityError:
            duplicate = await self._settlements.get_by_provider_reference(
                batch.provider_id, record.provider_settlement_reference
            )
            if duplicate is not None:
                return duplicate
            raise

        existing_for_txn = 0
        if identity_txn is not None:
            existing_for_txn = len(await self._settlements.list_for_transaction(identity_txn.id))

        match = decide_identity(
            settlement=settlement,
            by_payment_reference=identity_txn,
            by_provider_reference=identity_attempts,
            existing_settlements_for_transaction=existing_for_txn,
        )
        if match.transaction is not None:
            settlement.transaction_id = match.transaction.id
            settlement.merchant_id = match.transaction.merchant_id
            settlement.branch_id = match.transaction.branch_id
            if match.attempt is not None:
                settlement.payment_attempt_id = match.attempt.id

        decision = classify(settlement=settlement, identity=match, expected=expected)
        if (
            match.transaction is not None
            and existing_for_txn > 0
            and decision.status is ReconciliationStatus.MATCHED
        ):
            from app.models.enums import MismatchCategory

            decision = decision.__class__(
                status=ReconciliationStatus.DISCREPANCY,
                category=MismatchCategory.DUPLICATE_SETTLEMENT,
                expected_amount=decision.expected_amount,
                actual_amount=decision.actual_amount,
                variance=decision.variance,
                expected_provider_fee=decision.expected_provider_fee,
                actual_provider_fee=decision.actual_provider_fee,
                expected_pompo_fee=decision.expected_pompo_fee,
                actual_pompo_fee=decision.actual_pompo_fee,
                expected_currency=decision.expected_currency,
                actual_currency=decision.actual_currency,
                pompo_reference=decision.pompo_reference,
                provider_reference=decision.provider_reference,
            )

        recon = ReconciliationRecord(
            public_identifier=_public_id("REC"),
            settlement_id=settlement.id,
            transaction_id=settlement.transaction_id,
            payment_attempt_id=settlement.payment_attempt_id,
            status=decision.status,
            mismatch_category=decision.category,
            expected_amount=decision.expected_amount,
            actual_amount=decision.actual_amount,
            variance=decision.variance,
            expected_provider_fee=decision.expected_provider_fee,
            actual_provider_fee=decision.actual_provider_fee,
            expected_pompo_fee=decision.expected_pompo_fee,
            actual_pompo_fee=decision.actual_pompo_fee,
            expected_currency=decision.expected_currency,
            actual_currency=decision.actual_currency,
            pompo_reference=decision.pompo_reference,
            provider_reference=decision.provider_reference,
            detected_at=datetime.now(UTC),
        )
        self._session.add(recon)
        await self._session.flush()
        settlement.status = (
            SettlementStatus.RECONCILED
            if decision.status is ReconciliationStatus.MATCHED
            else SettlementStatus.SETTLED
        )
        if decision.status is ReconciliationStatus.INVESTIGATION:
            settlement.status = SettlementStatus.EXCEPTION

        action = (
            "settlement_matched"
            if decision.status is ReconciliationStatus.MATCHED
            else "settlement_unmatched"
            if decision.status is ReconciliationStatus.UNMATCHED
            else "discrepancy_created"
        )
        await self._audit(
            actor,
            action,
            "reconciliation",
            recon.id,
            None,
            {
                "settlement_id": str(settlement.id),
                "status": decision.status.value,
                "category": decision.category.value if decision.category else None,
                "pompo_reference": decision.pompo_reference,
            },
        )
        logger.info(
            action,
            settlement_id=str(settlement.id),
            reconciliation_id=str(recon.id),
            status=decision.status.value,
            category=decision.category.value if decision.category else None,
        )
        return settlement

    async def _lookup_identity(
        self,
        provider_id: uuid.UUID,
        record: NormalizedSettlementRecord,
    ) -> tuple[Transaction | None, list]:
        transaction = None
        if record.payment_reference:
            transaction = await self._transactions.get_active_by_reference(record.payment_reference)
        attempts = []
        if record.provider_transaction_reference:
            attempts = await list_attempts_by_provider_reference(
                self._session,
                provider_id=provider_id,
                provider_reference=record.provider_transaction_reference,
            )
            if transaction is None and len({item.transaction_id for item in attempts}) == 1:
                transaction = attempts[0].transaction
        return transaction, attempts

    async def _refresh_batch_totals(self, batch: SettlementBatch) -> None:
        count, gross, provider_fees, pompo_fees, net = await self._settlements.batch_totals(batch.id)
        batch.record_count = count
        batch.total_gross = parse_money(gross)
        batch.total_provider_fees = parse_money(provider_fees)
        batch.total_pompo_fees = parse_money(pompo_fees)
        batch.total_merchant_net = parse_money(net)

    async def list_settlements(
        self,
        actor: User,
        *,
        provider_code: str | None = None,
        status: str | None = None,
        settlement_date: date | None = None,
        batch_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Settlement]:
        await self._require(actor, "settlements:read")
        provider_id = await self._provider_id(provider_code)
        parsed_status = None
        if status:
            try:
                parsed_status = SettlementStatus(status)
            except ValueError as exc:
                raise SettlementInvalidError("Invalid settlement status") from exc
        return await self._settlements.list_settlements(
            provider_id=provider_id,
            merchant_id=await self._merchant_scope(actor),
            batch_id=batch_id,
            status=parsed_status,
            settlement_date=settlement_date,
            limit=min(limit, 100),
            offset=offset,
        )

    async def get_settlement(self, actor: User, settlement_id: uuid.UUID) -> Settlement:
        await self._require(actor, "settlements:read")
        settlement = await self._settlements.get_with_relations(settlement_id)
        if settlement is None:
            raise SettlementNotFoundError("Settlement not found")
        await self._assert_merchant_scope(actor, settlement.merchant_id)
        return settlement

    async def list_batches(
        self,
        actor: User,
        *,
        provider_code: str | None = None,
        settlement_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SettlementBatch]:
        await self._require(actor, "settlements:read")
        if not await self._is_platform_admin(actor):
            raise SettlementForbiddenError("Insufficient authority")
        provider_id = await self._provider_id(provider_code)
        return await self._batches.list_batches(
            provider_id=provider_id,
            settlement_date=settlement_date,
            limit=min(limit, 100),
            offset=offset,
        )

    async def get_batch(self, actor: User, batch_id: uuid.UUID) -> SettlementBatch:
        await self._require(actor, "settlements:read")
        if not await self._is_platform_admin(actor):
            raise SettlementForbiddenError("Insufficient authority")
        batch = await self._batches.get_by_id(batch_id)
        if batch is None:
            raise SettlementNotFoundError("Settlement batch not found")
        return batch

    async def settlement_summary(self, actor: User) -> dict[str, Decimal | int]:
        await self._require(actor, "settlements:read")
        return await self._settlements.summary(merchant_id=await self._merchant_scope(actor))

    async def list_reconciliation(
        self,
        actor: User,
        *,
        status: str | None = None,
        provider_code: str | None = None,
        run_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReconciliationRecord]:
        await self._require(actor, "reconciliation:read")
        parsed = None
        if status:
            try:
                parsed = ReconciliationStatus(status)
            except ValueError as exc:
                raise SettlementInvalidError("Invalid reconciliation status") from exc
        return await self._recon.list_records(
            status=parsed,
            merchant_id=await self._merchant_scope(actor),
            provider_id=await self._provider_id(provider_code),
            run_id=run_id,
            limit=min(limit, 100),
            offset=offset,
        )

    async def get_reconciliation(self, actor: User, record_id: uuid.UUID) -> ReconciliationRecord:
        await self._require(actor, "reconciliation:read")
        record = await self._recon.get_with_relations(record_id)
        if record is None:
            raise SettlementNotFoundError("Reconciliation record not found")
        merchant_id = record.settlement.merchant_id if record.settlement is not None else None
        if merchant_id is None and record.transaction is not None:
            merchant_id = record.transaction.merchant_id
        await self._assert_merchant_scope(actor, merchant_id)
        return record

    async def resolve(
        self,
        actor: User,
        record_id: uuid.UUID,
        *,
        note: str,
    ) -> ReconciliationRecord:
        await self._require(actor, "reconciliation:update")
        record = await self.get_reconciliation(actor, record_id)
        if record.status is ReconciliationStatus.RESOLVED:
            return record
        before = {"status": record.status.value}
        record.status = ReconciliationStatus.RESOLVED
        record.resolved_at = datetime.now(UTC)
        record.resolved_by_id = actor.id
        record.resolution_note = note[:1000]
        await self._audit(
            actor,
            "resolution_recorded",
            "reconciliation",
            record.id,
            before,
            {
                "status": record.status.value,
                "note_present": True,
                "pompo_reference": record.pompo_reference,
            },
        )
        await self._session.commit()
        logger.info(
            "resolution_recorded",
            reconciliation_id=str(record.id),
            actor_id=str(actor.id),
        )
        return record

    async def reconciliation_summary(self, actor: User) -> dict[str, Decimal | int | str]:
        await self._require(actor, "reconciliation:read")
        merchant_id = await self._merchant_scope(actor)
        counts = await self._recon.status_counts(merchant_id=merchant_id)
        settlement_summary = await self._settlements.summary(merchant_id=merchant_id)
        total = int(settlement_summary["total_settlements"])
        matched = counts.get(ReconciliationStatus.MATCHED.value, 0)
        matched_rate = "0.00" if total == 0 else f"{(Decimal(matched) / Decimal(total) * Decimal('100')).quantize(Decimal('0.01'))}"
        variance = await self._recon.discrepancy_total(merchant_id=merchant_id)
        return {
            **settlement_summary,
            **counts,
            "matched_rate": matched_rate,
            "unmatched_count": counts.get(ReconciliationStatus.UNMATCHED.value, 0),
            "discrepancy_total": variance,
        }

    async def create_run(
        self,
        actor: User,
        *,
        provider_code: str | None,
        window_start: datetime,
        window_end: datetime,
    ) -> ReconciliationRun:
        await self._require(actor, "reconciliation:update")
        if window_end <= window_start:
            raise SettlementInvalidError("window_end must be after window_start")
        provider_id = await self._provider_id(provider_code) if provider_code else None
        if provider_code and provider_id is None:
            raise SettlementInvalidError("Unknown provider")
        run = ReconciliationRun(
            public_identifier=_public_id("RUN"),
            provider_id=provider_id,
            window_start=window_start,
            window_end=window_end,
            status=ReconciliationRunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        self._session.add(run)
        await self._session.flush()

        merchant_id = await self._merchant_scope(actor)
        settlements = await self._settlements.list_in_window(
            provider_id=provider_id,
            window_start=window_start,
            window_end=window_end,
            merchant_id=merchant_id,
        )
        examined = 0
        matched = unmatched = discrepancy = partial = investigation = 0
        total_expected = ZERO_MONEY
        total_actual = ZERO_MONEY

        for settlement in settlements:
            examined += 1
            recon = settlement.reconciliation or await self._recon.get_by_settlement(settlement.id)
            if recon is None:
                continue
            recon.run_id = run.id
            if recon.status is ReconciliationStatus.MATCHED:
                matched += 1
            elif recon.status is ReconciliationStatus.UNMATCHED:
                unmatched += 1
            elif recon.status is ReconciliationStatus.DISCREPANCY:
                discrepancy += 1
            elif recon.status is ReconciliationStatus.PARTIAL_MATCH:
                partial += 1
            elif recon.status is ReconciliationStatus.INVESTIGATION:
                investigation += 1
            if recon.expected_amount is not None:
                total_expected += parse_money(recon.expected_amount)
            if recon.actual_amount is not None:
                total_actual += parse_money(recon.actual_amount)

        missing = await list_successful_transactions_without_settlement(
            self._session,
            provider_id=provider_id,
            window_start=window_start,
            window_end=window_end,
            merchant_id=merchant_id,
        )
        from app.models.enums import MismatchCategory

        for transaction in missing:
            examined += 1
            unmatched += 1
            total_expected += parse_money(transaction.amount)
            existing = await self._recon.get_missing_settlement(transaction.id)
            if existing is not None:
                existing.run_id = run.id
                if existing.status is not ReconciliationStatus.RESOLVED:
                    existing.status = ReconciliationStatus.UNMATCHED
                    existing.mismatch_category = MismatchCategory.MISSING_SETTLEMENT
                continue
            self._session.add(
                ReconciliationRecord(
                    public_identifier=_public_id("REC"),
                    run_id=run.id,
                    transaction_id=transaction.id,
                    status=ReconciliationStatus.UNMATCHED,
                    mismatch_category=MismatchCategory.MISSING_SETTLEMENT,
                    expected_amount=parse_money(transaction.amount),
                    actual_amount=None,
                    variance=None,
                    expected_currency=transaction.currency,
                    pompo_reference=transaction.reference,
                    detected_at=datetime.now(UTC),
                )
            )

        run.records_examined = examined
        run.matched_count = matched
        run.unmatched_count = unmatched
        run.discrepancy_count = discrepancy
        run.partial_count = partial
        run.investigation_count = investigation
        run.total_expected = parse_money(total_expected)
        run.total_actual = parse_money(total_actual)
        run.total_variance = parse_money(total_actual - total_expected)
        run.status = ReconciliationRunStatus.COMPLETED
        run.finished_at = datetime.now(UTC)
        await self._audit(
            actor,
            "reconciliation_completed",
            "reconciliation_run",
            run.id,
            None,
            {
                "records_examined": examined,
                "matched_count": matched,
                "unmatched_count": unmatched,
                "discrepancy_count": discrepancy,
            },
        )
        await self._session.commit()
        logger.info(
            "reconciliation_completed",
            run_id=str(run.id),
            records_examined=examined,
            matched_count=matched,
        )
        return run

    async def list_runs(
        self,
        actor: User,
        *,
        provider_code: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReconciliationRun]:
        await self._require(actor, "reconciliation:read")
        if not await self._is_platform_admin(actor):
            raise SettlementForbiddenError("Insufficient authority")
        return await self._runs.list_runs(
            provider_id=await self._provider_id(provider_code),
            limit=min(limit, 100),
            offset=offset,
        )

    async def get_run(self, actor: User, run_id: uuid.UUID) -> ReconciliationRun:
        await self._require(actor, "reconciliation:read")
        if not await self._is_platform_admin(actor):
            raise SettlementForbiddenError("Insufficient authority")
        run = await self._runs.get_by_id(run_id)
        if run is None:
            raise SettlementNotFoundError("Reconciliation run not found")
        return run

    async def _provider_id(self, provider_code: str | None) -> uuid.UUID | None:
        if not provider_code:
            return None
        provider = await self._providers.get_by_code(provider_code)
        return None if provider is None else provider.id

    async def _is_platform_admin(self, actor: User) -> bool:
        role = await self._authorization.get_user_role(actor)
        return role is not None and role.code == UserRoleCode.PLATFORM_ADMIN.value

    async def _merchant_scope(self, actor: User) -> uuid.UUID | None:
        if await self._is_platform_admin(actor):
            return None
        return actor.merchant_id

    async def _assert_merchant_scope(self, actor: User, merchant_id: uuid.UUID | None) -> None:
        if await self._is_platform_admin(actor):
            return
        if merchant_id is None or actor.merchant_id != merchant_id:
            raise SettlementForbiddenError("Insufficient authority")

    async def _require(self, actor: User, permission: str) -> None:
        if not await self._authorization.has_permission(actor, permission):
            raise SettlementForbiddenError("Insufficient authority")

    async def _audit(
        self,
        actor: User | None,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=None if actor is None else actor.id,
                merchant_id=None if actor is None else actor.merchant_id,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id),
                before_state=before,
                after_state=after,
            )
        )
