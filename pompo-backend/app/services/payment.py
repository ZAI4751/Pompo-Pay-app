"""M006 payment orchestration and transaction lifecycle service."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    AuditLog,
    Branch,
    Merchant,
    PaymentAttempt,
    PaymentProvider,
    Till,
    Transaction,
    User,
)
from app.models.enums import PaymentAttemptStatus, TransactionStatus
from app.payments.providers import ProviderError, ProviderOutcome, ProviderPaymentRequest
from app.payments.registry import ProviderRegistry
from app.payments.state_machine import InvalidTransactionTransition, validate_transition
from app.repositories.payment import (
    PaymentAttemptRepository,
    PaymentProviderRepository,
    TransactionRepository,
)
from app.repositories.rbac import AuthorizationRepository
from app.services.authorization import AuthorizationService

logger = get_logger(__name__)


class PaymentError(Exception):
    """Base class for expected payment-core failures."""


class PaymentNotFoundError(PaymentError):
    pass


class PaymentForbiddenError(PaymentError):
    pass


class PaymentConflictError(PaymentError):
    pass


class PaymentInvalidError(PaymentError):
    pass


class PaymentService:
    def __init__(self, session: AsyncSession, registry: ProviderRegistry | None = None) -> None:
        self._session = session
        self._transactions = TransactionRepository(session)
        self._providers = PaymentProviderRepository(session)
        self._attempts = PaymentAttemptRepository(session)
        self._authorization = AuthorizationService(AuthorizationRepository(session))
        self._registry = registry or ProviderRegistry()

    async def create_payment(self, actor: User, values: dict[str, Any]) -> Transaction:
        await self._require(actor, "transactions:create")
        merchant_id = values["merchant_id"]
        await self._validate_scope(actor, merchant_id, values["branch_id"], values["till_id"])
        fingerprint = self._fingerprint(values)
        existing = await self._transactions.get_by_idempotency(
            merchant_id, values["idempotency_key"]
        )
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise PaymentConflictError("Idempotency key was used with a different request")
            return existing

        provider = await self._providers.get_active_by_code(values["provider_code"])
        if provider is None:
            raise PaymentInvalidError("Payment provider is unavailable")
        transaction = Transaction(
            merchant_id=merchant_id,
            branch_id=values["branch_id"],
            till_id=values["till_id"],
            cashier_id=actor.id,
            provider_id=provider.id,
            reference=f"PMP-{uuid.uuid4().hex.upper()}",
            idempotency_key=values["idempotency_key"],
            request_fingerprint=fingerprint,
            amount=values["amount"],
            currency=values["currency"],
            payment_method=values["payment_method"],
            customer_phone=values.get("customer_phone"),
            description=values.get("description"),
            status=TransactionStatus.CREATED,
        )
        self._session.add(transaction)
        await self._session.flush()
        attempt = PaymentAttempt(
            transaction_id=transaction.id,
            provider_id=provider.id,
            attempt_number=1,
            status=PaymentAttemptStatus.INITIATED,
            initiated_at=datetime.now(UTC),
        )
        attempt.transaction = transaction
        self._session.add(attempt)
        await self._audit(
            actor, "payment_created", transaction.id, None, {"reference": transaction.reference}
        )
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            existing = await self._transactions.get_by_idempotency(
                merchant_id, values["idempotency_key"]
            )
            if existing is not None and existing.request_fingerprint == fingerprint:
                return existing
            raise PaymentConflictError(
                "Payment request conflicts with an existing transaction"
            ) from exc
        await self._session.refresh(transaction, attribute_names=["attempts"])
        logger.info(
            "payment_created", transaction_id=str(transaction.id), reference=transaction.reference
        )
        return transaction

    async def get_payment(self, actor: User, reference: str) -> Transaction:
        await self._require(actor, "transactions:read")
        transaction = await self._transactions.get_active_by_reference(reference)
        if transaction is None:
            raise PaymentNotFoundError("Payment not found")
        await self._validate_scope(
            actor, transaction.merchant_id, transaction.branch_id, transaction.till_id
        )
        return transaction

    async def transition_payment(
        self,
        actor: User,
        reference: str,
        target: TransactionStatus,
        failure_reason: str | None = None,
    ) -> Transaction:
        await self._require(actor, "transactions:update")
        transaction = await self.get_payment(actor, reference)
        try:
            validate_transition(transaction.status, target)
        except InvalidTransactionTransition as exc:
            raise PaymentInvalidError(str(exc)) from exc
        before = transaction.status.value
        transaction.status = target
        transaction.failure_reason = failure_reason
        if target in {
            TransactionStatus.SUCCESS,
            TransactionStatus.FAILED,
            TransactionStatus.TIMEOUT,
            TransactionStatus.CANCELLED,
            TransactionStatus.REFUNDED,
        }:
            transaction.completed_at = datetime.now(UTC)
        await self._audit(
            actor,
            "transaction_transitioned",
            transaction.id,
            {"status": before},
            {"status": target.value},
        )
        await self._session.commit()
        logger.info("transaction_transitioned", reference=reference, status=target.value)
        return transaction

    async def cancel_payment(self, actor: User, reference: str) -> Transaction:
        await self._require(actor, "transactions:cancel")
        return await self.transition_payment(actor, reference, TransactionStatus.CANCELLED)

    async def create_attempt(self, actor: User, reference: str) -> PaymentAttempt:
        await self._require(actor, "transactions:update")
        transaction = await self.get_payment(actor, reference)
        if transaction.status in {
            TransactionStatus.SUCCESS,
            TransactionStatus.REFUNDED,
            TransactionStatus.CANCELLED,
        }:
            raise PaymentInvalidError("Terminal transactions cannot receive new attempts")
        if transaction.provider_id is None:
            raise PaymentInvalidError("Transaction has no payment provider")
        number = await self._attempts.next_number(transaction.id)
        attempt = PaymentAttempt(
            transaction_id=transaction.id,
            provider_id=transaction.provider_id,
            attempt_number=number,
            status=PaymentAttemptStatus.INITIATED,
            initiated_at=datetime.now(UTC),
        )
        self._session.add(attempt)
        await self._session.commit()
        return attempt

    async def process_payment(self, actor: User, reference: str) -> Transaction:
        await self._require(actor, "transactions:update")
        transaction = await self.get_payment(actor, reference)
        if transaction.provider_id is None:
            raise PaymentInvalidError("Transaction has no payment provider")
        provider = await self._session.get(PaymentProvider, transaction.provider_id)
        if provider is None:
            raise PaymentInvalidError("Payment provider is unavailable")
        adapter = self._registry.get(provider.code.value)
        if not transaction.attempts:
            raise PaymentInvalidError("Transaction has no payment attempt")
        attempt = transaction.attempts[-1]
        request = ProviderPaymentRequest(
            reference=transaction.reference,
            amount=transaction.amount,
            currency=transaction.currency,
            merchant_id=str(transaction.merchant_id),
            customer_phone=transaction.customer_phone,
            narration=transaction.description,
            idempotency_key=f"{transaction.reference}:{attempt.attempt_number}",
        )
        request_data = asdict(request)
        request_data["amount"] = str(request.amount)
        attempt.provider_request = request_data
        started = monotonic()
        try:
            result = await adapter.initiate_payment(request)
        except ProviderError as exc:
            attempt.status = (
                PaymentAttemptStatus.TIMEOUT
                if exc.code.value == "timeout"
                else PaymentAttemptStatus.FAILED
            )
            attempt.failure_reason = str(exc)
            attempt.provider_status = exc.code.value
            await self._advance_to(
                transaction,
                TransactionStatus.TIMEOUT
                if exc.code.value == "timeout"
                else TransactionStatus.FAILED,
            )
            await self._session.commit()
            logger.warning(
                "provider_failure",
                reference=reference,
                provider=provider.code.value,
                retryable=exc.retryable,
            )
            return transaction
        attempt.duration_ms = int((monotonic() - started) * 1000)
        attempt.provider_reference = result.provider_reference
        attempt.provider_status = result.provider_status
        attempt.provider_response = {key: str(value) for key, value in asdict(result).items()}
        attempt.status = self._attempt_status(result.outcome)
        if result.message:
            attempt.failure_reason = result.message
        target = {
            ProviderOutcome.SUCCESS: TransactionStatus.SUCCESS,
            ProviderOutcome.PENDING: TransactionStatus.PENDING,
            ProviderOutcome.FAILED: TransactionStatus.FAILED,
            ProviderOutcome.REJECTED: TransactionStatus.FAILED,
            ProviderOutcome.TIMEOUT: TransactionStatus.TIMEOUT,
        }[result.outcome]
        await self._advance_to(transaction, target)
        await self._session.commit()
        logger.info(
            "provider_payment_result",
            reference=reference,
            provider=provider.code.value,
            outcome=result.outcome.value,
        )
        return transaction

    async def _advance_to(self, transaction: Transaction, target: TransactionStatus) -> None:
        if transaction.status is target:
            return
        path = [TransactionStatus.PENDING, TransactionStatus.PROCESSING, target]
        if target is TransactionStatus.PENDING:
            path = [target]
        for next_status in path:
            if transaction.status is next_status:
                continue
            validate_transition(transaction.status, next_status)
            transaction.status = next_status
            if next_status in {
                TransactionStatus.SUCCESS,
                TransactionStatus.FAILED,
                TransactionStatus.TIMEOUT,
            }:
                transaction.completed_at = datetime.now(UTC)

    @staticmethod
    def _attempt_status(outcome: ProviderOutcome) -> PaymentAttemptStatus:
        return {
            ProviderOutcome.SUCCESS: PaymentAttemptStatus.SUCCESS,
            ProviderOutcome.PENDING: PaymentAttemptStatus.PENDING,
            ProviderOutcome.FAILED: PaymentAttemptStatus.FAILED,
            ProviderOutcome.REJECTED: PaymentAttemptStatus.FAILED,
            ProviderOutcome.TIMEOUT: PaymentAttemptStatus.TIMEOUT,
        }[outcome]

    async def _validate_scope(
        self, actor: User, merchant_id: uuid.UUID, branch_id: uuid.UUID, till_id: uuid.UUID
    ) -> None:
        if not await self._is_platform_admin(actor) and (
            actor.merchant_id != merchant_id
            or (actor.branch_id is not None and actor.branch_id != branch_id)
        ):
            raise PaymentForbiddenError("Payment is outside actor scope")
        merchant = await self._session.scalar(
            select(Merchant).where(
                Merchant.id == merchant_id,
                Merchant.deleted_at.is_(None),
                Merchant.is_active.is_(True),
            )
        )
        branch = await self._session.scalar(
            select(Branch).where(
                Branch.id == branch_id,
                Branch.merchant_id == merchant_id,
                Branch.deleted_at.is_(None),
                Branch.is_active.is_(True),
            )
        )
        till = await self._session.scalar(
            select(Till).where(
                Till.id == till_id,
                Till.branch_id == branch_id,
                Till.deleted_at.is_(None),
                Till.is_active.is_(True),
            )
        )
        if merchant is None or branch is None or till is None:
            raise PaymentInvalidError("Merchant, branch, or till is unavailable")

    async def _is_platform_admin(self, actor: User) -> bool:
        role = await self._authorization.get_user_role(actor)
        return role is not None and role.code == "platform_admin"

    async def _require(self, actor: User, permission: str) -> None:
        if not await self._authorization.has_permission(actor, permission):
            raise PaymentForbiddenError("Insufficient authority")

    @staticmethod
    def _fingerprint(values: dict[str, Any]) -> str:
        payload = {key: str(value) for key, value in values.items() if key != "idempotency_key"}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

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
                entity_type="payment",
                entity_id=str(entity_id),
                before_state=before,
                after_state=after,
            )
        )
