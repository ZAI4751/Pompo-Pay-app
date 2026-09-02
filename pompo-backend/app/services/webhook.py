"""Provider webhook ingestion and asynchronous processing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import AuditLog, PaymentAttempt, Transaction, User, WebhookEvent
from app.models.enums import (
    TERMINAL_TRANSACTION_STATUSES,
    PaymentAttemptStatus,
    TransactionStatus,
    WebhookFailureCategory,
    WebhookProcessingStatus,
)
from app.payments.credentials import resolve_provider_credentials
from app.payments.providers import ProviderOutcome, UnsupportedProviderOperation
from app.payments.registry import ProviderRegistry
from app.payments.webhooks import (
    NormalizedWebhookEvent,
    sanitize_payload,
)
from app.repositories.payment import PaymentAttemptRepository, PaymentProviderRepository, TransactionRepository
from app.repositories.rbac import AuthorizationRepository
from app.repositories.webhook import WebhookEventRepository
from app.services.authorization import AuthorizationService
from app.services.payment import PaymentService, WebhookApplyOutcome

logger = get_logger(__name__)

WEBHOOK_MAX_PROCESSING_ATTEMPTS = 5


class WebhookError(Exception):
    """Base class for webhook subsystem failures."""


class WebhookNotFoundError(WebhookError):
    pass


class WebhookForbiddenError(WebhookError):
    pass


class WebhookInvalidError(WebhookError):
    pass


class WebhookSignatureError(WebhookError):
    pass


class WebhookDuplicateError(WebhookError):
    def __init__(self, event: WebhookEvent) -> None:
        super().__init__("Duplicate provider event")
        self.event = event


class WebhookRetryableError(WebhookError):
    pass


class WebhookService:
    def __init__(
        self,
        session: AsyncSession,
        registry: ProviderRegistry | None = None,
        *,
        sync_processing: bool = False,
    ) -> None:
        self._session = session
        self._events = WebhookEventRepository(session)
        self._providers = PaymentProviderRepository(session)
        self._transactions = TransactionRepository(session)
        self._attempts = PaymentAttemptRepository(session)
        self._authorization = AuthorizationService(AuthorizationRepository(session))
        self._payments = PaymentService(session, registry)
        self._registry = registry or ProviderRegistry()
        self._sync_processing = sync_processing

    async def ingest(
        self,
        provider_code: str,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> WebhookEvent:
        provider = await self._providers.get_by_code(provider_code)
        if provider is None:
            raise WebhookInvalidError("Unknown provider")
        adapter = self._registry.get_optional(provider_code)
        if adapter is None or not hasattr(adapter, "verify_webhook") or not hasattr(adapter, "parse_webhook"):
            raise WebhookInvalidError("Provider does not support webhooks")

        credentials = resolve_provider_credentials(provider_code, catalog_environment=provider.environment)
        verification = await adapter.verify_webhook(
            headers=headers,
            body=body,
            credentials=credentials,
        )
        if not verification.verified:
            logger.warning(
                "webhook_rejected",
                provider=provider_code,
                reason=verification.failure_reason,
            )
            raise WebhookSignatureError(verification.failure_reason or "Invalid signature")

        try:
            normalized = await adapter.parse_webhook(headers=headers, body=body)
        except (ValueError, UnsupportedProviderOperation) as exc:
            raise WebhookInvalidError(str(exc)) from exc

        existing = await self._events.get_by_provider_event(provider.id, normalized.provider_event_id)
        if existing is not None:
            logger.info(
                "webhook_deduplicated",
                provider=provider_code,
                provider_event_id=normalized.provider_event_id,
                webhook_event_id=str(existing.id),
            )
            raise WebhookDuplicateError(existing)

        received_at = datetime.now(UTC)
        event = WebhookEvent(
            public_identifier=f"WHK-{uuid.uuid4().hex.upper()}",
            provider_id=provider.id,
            provider_event_id=normalized.provider_event_id,
            event_type=normalized.event_type,
            event_version=normalized.event_version,
            payment_reference=normalized.payment_reference,
            provider_transaction_reference=normalized.provider_transaction_reference,
            received_at=received_at,
            payload=sanitize_payload(
                {
                    "event_id": normalized.provider_event_id,
                    "event_type": normalized.event_type,
                    "event_version": normalized.event_version,
                    "payment_reference": normalized.payment_reference,
                    "provider_transaction_reference": normalized.provider_transaction_reference,
                    "outcome": normalized.outcome.value if normalized.outcome else None,
                    "message": normalized.message,
                    "metadata": normalized.metadata,
                }
            ),
            signature_verified=True,
            timestamp_validated=verification.timestamp_validated,
            processing_status=WebhookProcessingStatus.QUEUED,
            processing_attempts=0,
            processed=False,
        )
        self._session.add(event)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            duplicate = await self._events.get_by_provider_event(
                provider.id, normalized.provider_event_id
            )
            if duplicate is not None:
                raise WebhookDuplicateError(duplicate) from None
            raise

        await self._session.refresh(event)
        await self._audit_system(
            "webhook_received",
            event.id,
            None,
            {
                "provider": provider_code,
                "provider_event_id": normalized.provider_event_id,
                "event_type": normalized.event_type,
            },
        )
        logger.info(
            "webhook_received",
            webhook_event_id=str(event.id),
            provider=provider_code,
            provider_event_id=normalized.provider_event_id,
        )
        await self._enqueue_processing(event.id)
        return event

    async def process_event(self, event_id: uuid.UUID) -> WebhookEvent:
        event = await self._events.get_for_processing(event_id)
        if event is None:
            raise WebhookNotFoundError("Webhook event not found")

        if event.processing_status in {
            WebhookProcessingStatus.PROCESSED,
            WebhookProcessingStatus.DUPLICATE,
            WebhookProcessingStatus.REJECTED,
        }:
            return event

        if event.processing_attempts >= WEBHOOK_MAX_PROCESSING_ATTEMPTS:
            event.processing_status = WebhookProcessingStatus.FAILED
            event.failure_category = WebhookFailureCategory.INFRASTRUCTURE
            event.failure_code = "max_attempts_exceeded"
            event.processed = True
            event.processed_at = datetime.now(UTC)
            await self._session.commit()
            return event

        event.processing_status = WebhookProcessingStatus.PROCESSING
        event.processing_attempts += 1
        await self._session.flush()
        logger.info(
            "webhook_processing_started",
            webhook_event_id=str(event.id),
            attempt=event.processing_attempts,
        )

        try:
            normalized = self._normalized_from_event(event)
            transaction, attempt = await self._correlate(event, normalized)
        except WebhookInvalidError as exc:
            return await self._mark_failed(
                event,
                category=self._failure_category_for(exc),
                code=str(exc),
                permanent=True,
            )
        except WebhookRetryableError:
            event.processing_status = WebhookProcessingStatus.QUEUED
            await self._session.commit()
            raise

        event.transaction_id = transaction.id if transaction else None
        event.payment_attempt_id = attempt.id if attempt else None
        event.payment_reference = event.payment_reference or (
            transaction.reference if transaction else None
        )

        if transaction is None or attempt is None or normalized.outcome is None:
            return await self._mark_failed(
                event,
                category=WebhookFailureCategory.UNKNOWN_PAYMENT,
                code="payment_not_correlated",
                permanent=True,
            )

        apply_result = await self._payments.apply_webhook_outcome(
            transaction=transaction,
            attempt=attempt,
            outcome=normalized.outcome,
            provider_event_id=event.provider_event_id,
            webhook_event_id=event.id,
            failure_reason=normalized.message,
        )

        if apply_result is WebhookApplyOutcome.APPLIED:
            event.processing_status = WebhookProcessingStatus.PROCESSED
            event.processed = True
            event.processed_at = datetime.now(UTC)
            await self._audit_system(
                "payment_updated_by_webhook",
                transaction.id,
                None,
                {
                    "webhook_event_id": str(event.id),
                    "outcome": normalized.outcome.value,
                    "reference": transaction.reference,
                },
            )
            logger.info(
                "webhook_processing_succeeded",
                webhook_event_id=str(event.id),
                reference=transaction.reference,
            )
        elif apply_result is WebhookApplyOutcome.DUPLICATE:
            event.processing_status = WebhookProcessingStatus.DUPLICATE
            event.processed = True
            event.processed_at = datetime.now(UTC)
            logger.info(
                "webhook_terminal_duplicate",
                webhook_event_id=str(event.id),
                reference=transaction.reference,
            )
        elif apply_result is WebhookApplyOutcome.RECONCILIATION:
            event.processing_status = WebhookProcessingStatus.RECONCILIATION
            event.failure_category = WebhookFailureCategory.STATE_CONFLICT
            event.failure_code = "terminal_state_conflict"
            event.processed = True
            event.processed_at = datetime.now(UTC)
            logger.warning(
                "webhook_reconciliation_required",
                webhook_event_id=str(event.id),
                reference=transaction.reference,
            )
        else:
            event.processing_status = WebhookProcessingStatus.PROCESSED
            event.processed = True
            event.processed_at = datetime.now(UTC)

        await self._audit_system(
            "webhook_processed",
            event.id,
            None,
            {"processing_status": event.processing_status.value},
        )
        await self._session.commit()
        return event

    async def get_event(self, actor: User, event_id: uuid.UUID) -> WebhookEvent:
        await self._require(actor, "webhooks:read")
        event = await self._events.get_by_id(event_id)
        if event is None:
            raise WebhookNotFoundError("Webhook event not found")
        return event

    async def list_events(
        self,
        actor: User,
        *,
        provider_code: str | None = None,
        processing_status: str | None = None,
        event_type: str | None = None,
        payment_reference: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WebhookEvent]:
        await self._require(actor, "webhooks:read")
        status = None
        if processing_status:
            try:
                status = WebhookProcessingStatus(processing_status)
            except ValueError as exc:
                raise WebhookInvalidError("Invalid processing status filter") from exc
        return await self._events.list_events(
            provider_code=provider_code,
            processing_status=status,
            event_type=event_type,
            payment_reference=payment_reference,
            limit=min(limit, 100),
            offset=offset,
        )

    async def _correlate(
        self,
        event: WebhookEvent,
        normalized: NormalizedWebhookEvent,
    ) -> tuple[Transaction | None, PaymentAttempt | None]:
        transaction: Transaction | None = None
        attempt: PaymentAttempt | None = None

        if normalized.payment_reference:
            transaction = await self._transactions.get_active_by_reference(normalized.payment_reference)

        if transaction is None and normalized.provider_transaction_reference:
            attempt = await self._attempts.find_by_provider_reference(
                event.provider_id, normalized.provider_transaction_reference
            )
            if attempt is not None:
                transaction = await self._transactions.get_active_by_reference(
                    attempt.transaction.reference
                )

        if transaction is None:
            return None, None

        if transaction.provider_id != event.provider_id:
            raise WebhookInvalidError("Provider mismatch for correlated payment")

        if attempt is None and transaction.attempts:
            attempt = transaction.attempts[-1]
            if normalized.provider_transaction_reference:
                matched = [
                    item
                    for item in transaction.attempts
                    if item.provider_reference == normalized.provider_transaction_reference
                    or (
                        item.provider_response
                        and item.provider_response.get("provider_transaction_id")
                        == normalized.provider_transaction_reference
                    )
                ]
                if len(matched) > 1:
                    raise WebhookInvalidError("Ambiguous payment attempt correlation")
                if len(matched) == 1:
                    attempt = matched[0]

        if attempt is not None and attempt.provider_id != event.provider_id:
            raise WebhookInvalidError("Provider mismatch for payment attempt")

        return transaction, attempt

    async def _mark_failed(
        self,
        event: WebhookEvent,
        *,
        category: WebhookFailureCategory,
        code: str,
        permanent: bool,
    ) -> WebhookEvent:
        event.processing_status = WebhookProcessingStatus.FAILED
        event.failure_category = category
        event.failure_code = code[:64]
        event.processed = permanent
        event.processed_at = datetime.now(UTC) if permanent else None
        await self._audit_system(
            "webhook_processing_failed",
            event.id,
            None,
            {"failure_category": category.value, "failure_code": code[:64]},
        )
        await self._session.commit()
        logger.warning(
            "webhook_processing_failed",
            webhook_event_id=str(event.id),
            failure_category=category.value,
            failure_code=code[:64],
        )
        return event

    async def _enqueue_processing(self, event_id: uuid.UUID) -> None:
        if self._sync_processing:
            await self.process_event(event_id)
            return
        from app.tasks.webhooks import process_webhook_event

        process_webhook_event.delay(str(event_id))

    @staticmethod
    def _normalized_from_event(event: WebhookEvent) -> NormalizedWebhookEvent:
        payload = event.payload
        outcome = payload.get("outcome")
        parsed_outcome = ProviderOutcome(outcome) if outcome else None
        return NormalizedWebhookEvent(
            provider_event_id=event.provider_event_id,
            event_type=event.event_type,
            event_version=event.event_version,
            payment_reference=event.payment_reference,
            provider_transaction_reference=event.provider_transaction_reference,
            outcome=parsed_outcome,
            message=payload.get("message"),
            metadata={
                key: str(value)
                for key, value in (payload.get("metadata") or {}).items()
                if isinstance(value, (str, int, float, bool))
            },
        )

    @staticmethod
    def _failure_category_for(exc: WebhookInvalidError) -> WebhookFailureCategory:
        message = str(exc).lower()
        if "provider mismatch" in message:
            return WebhookFailureCategory.PROVIDER_MISMATCH
        if "ambiguous" in message:
            return WebhookFailureCategory.UNKNOWN_PAYMENT
        if "unsupported" in message:
            return WebhookFailureCategory.UNSUPPORTED_EVENT
        if "malformed" in message or "missing" in message:
            return WebhookFailureCategory.MALFORMED
        return WebhookFailureCategory.UNKNOWN_PAYMENT

    async def _require(self, actor: User, permission: str) -> None:
        if not await self._authorization.has_permission(actor, permission):
            raise WebhookForbiddenError("Insufficient authority")

    async def _audit_system(
        self,
        action: str,
        entity_id: uuid.UUID,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=None,
                merchant_id=None,
                action=action,
                entity_type="webhook",
                entity_id=str(entity_id),
                before_state=before,
                after_state=after,
            )
        )
