"""Outbound partner/POS webhook queueing, signing, and bounded delivery."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.base import get_settings
from app.core.logging import get_logger
from app.integrations.keys import derive_webhook_secret
from app.integrations.signing import (
    EVENT_ID_HEADER,
    EVENT_TYPE_HEADER,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    sign_outbound_body,
)
from app.models import AuditLog, IntegrationClient, OutboundWebhookDelivery, Transaction
from app.models.enums import (
    OutboundWebhookFailureCategory,
    OutboundWebhookStatus,
    TransactionStatus,
)
from app.payments.webhooks import sanitize_payload
from app.repositories.integration import (
    IntegrationClientRepository,
    IntegrationWebhookEndpointRepository,
    OutboundWebhookDeliveryRepository,
)

logger = get_logger(__name__)

EVENT_BY_STATUS: dict[TransactionStatus, str] = {
    TransactionStatus.CREATED: "payment.pending",
    TransactionStatus.QR_GENERATED: "payment.pending",
    TransactionStatus.PENDING: "payment.pending",
    TransactionStatus.PENDING_USER_PIN: "payment.processing",
    TransactionStatus.PROCESSING: "payment.processing",
    TransactionStatus.SUCCESS: "payment.success",
    TransactionStatus.FAILED: "payment.failed",
    TransactionStatus.TIMEOUT: "payment.timeout",
}

RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
BACKOFF_SECONDS = (10, 30, 120, 300, 900)


class OutboundWebhookRetryableError(Exception):
    """Raised when Celery should retry a delivery attempt."""


class OutboundWebhookService:
    def __init__(self, session: AsyncSession, http_client: httpx.AsyncClient | None = None) -> None:
        self._session = session
        self._deliveries = OutboundWebhookDeliveryRepository(session)
        self._clients = IntegrationClientRepository(session)
        self._endpoints = IntegrationWebhookEndpointRepository(session)
        self._settings = get_settings()
        self._http = http_client

    async def queue_for_transaction(self, transaction: Transaction) -> OutboundWebhookDelivery | None:
        if transaction.api_client_id is None:
            return None
        event_type = EVENT_BY_STATUS.get(transaction.status)
        if event_type is None:
            return None
        client = await self._clients.get_by_id(transaction.api_client_id)
        if client is None:
            return None

        event_id = f"evt_{transaction.reference}_{event_type.split('.', 1)[-1]}"
        payload = sanitize_payload(
            {
                "event_id": event_id,
                "event_type": event_type,
                "created_at": datetime.now(UTC).isoformat(),
                "data": {
                    "reference": transaction.reference,
                    "status": transaction.status.value,
                    "amount": str(transaction.amount),
                    "currency": transaction.currency,
                    "merchant_id": str(transaction.merchant_id),
                    "branch_id": str(transaction.branch_id),
                    "till_id": str(transaction.till_id),
                },
            }
        )
        endpoints = await self._endpoints.list_for_client(client.id, active_only=True)
        destinations: list[tuple[uuid.UUID | None, str]] = [
            (endpoint.id, endpoint.destination_url) for endpoint in endpoints
        ]
        if not destinations and client.webhook_url:
            destinations = [(None, client.webhook_url)]
        if not destinations:
            logger.info(
                "outbound_webhook_skipped",
                client_id=str(client.id),
                reference=transaction.reference,
                reason="webhook_not_configured",
            )
            return None

        created: list[OutboundWebhookDelivery] = []
        queued: list[OutboundWebhookDelivery] = []
        for endpoint_id, destination_url in destinations:
            existing = await self._deliveries.get_by_identity(
                client_id=client.id,
                transaction_id=transaction.id,
                event_type=event_type,
                destination_url=destination_url,
            )
            if existing is not None:
                created.append(existing)
                continue
            delivery = OutboundWebhookDelivery(
                public_event_id=event_id,
                client_id=client.id,
                endpoint_id=endpoint_id,
                transaction_id=transaction.id,
                event_type=event_type,
                destination_url=destination_url,
                payload=payload,
                status=OutboundWebhookStatus.PENDING,
                max_attempts=self._settings.outbound_webhook_max_attempts,
                next_retry_at=datetime.now(UTC),
            )
            try:
                async with self._session.begin_nested():
                    self._session.add(delivery)
                    await self._session.flush()
            except IntegrityError:
                existing = await self._deliveries.get_by_identity(
                    client_id=client.id,
                    transaction_id=transaction.id,
                    event_type=event_type,
                    destination_url=destination_url,
                )
                logger.info(
                    "outbound_webhook_duplicate",
                    event_id=event_id,
                    client_id=str(client.id),
                    reference=transaction.reference,
                )
                if existing is not None:
                    created.append(existing)
                continue
            await self._audit_system(
                "outbound_webhook_queued",
                delivery.id,
                None,
                {
                    "event_id": event_id,
                    "event_type": event_type,
                    "client_id": str(client.id),
                    "reference": transaction.reference,
                },
                merchant_id=transaction.merchant_id,
                api_client_id=client.id,
            )
            created.append(delivery)
            queued.append(delivery)

        await self._session.commit()
        logger.info(
            "outbound_webhook_queued",
            event_id=event_id,
            client_id=str(client.id),
            reference=transaction.reference,
            request_id=_request_id(),
            destinations=len(created),
        )
        for delivery in queued:
            self._enqueue(delivery.id)
        return created[0] if created else None

    async def deliver(self, delivery_id: uuid.UUID) -> OutboundWebhookDelivery:
        delivery = await self._deliveries.get_by_id(delivery_id)
        if delivery is None:
            raise OutboundWebhookRetryableError("Outbound webhook delivery not found")
        if delivery.status is OutboundWebhookStatus.SENT:
            return delivery
        if delivery.status is OutboundWebhookStatus.FAILED:
            return delivery
        if delivery.attempt_count >= delivery.max_attempts:
            delivery.status = OutboundWebhookStatus.FAILED
            delivery.failure_category = OutboundWebhookFailureCategory.EXHAUSTED
            delivery.failure_code = "max_attempts_exceeded"
            await self._session.commit()
            return delivery

        client = await self._clients.get_by_id(delivery.client_id)
        if client is None:
            delivery.status = OutboundWebhookStatus.FAILED
            delivery.failure_category = OutboundWebhookFailureCategory.INVALID_DESTINATION
            delivery.failure_code = "client_missing"
            await self._session.commit()
            return delivery

        if not _safe_destination(delivery.destination_url):
            delivery.status = OutboundWebhookStatus.FAILED
            delivery.failure_category = OutboundWebhookFailureCategory.INVALID_DESTINATION
            delivery.failure_code = "invalid_destination"
            delivery.attempt_count += 1
            delivery.last_attempted_at = datetime.now(UTC)
            delivery.first_attempted_at = delivery.first_attempted_at or delivery.last_attempted_at
            await self._session.commit()
            logger.warning(
                "outbound_webhook_failed",
                event_id=delivery.public_event_id,
                client_id=str(client.id),
                failure_category="invalid_destination",
            )
            return delivery

        now = datetime.now(UTC)
        delivery.attempt_count += 1
        delivery.first_attempted_at = delivery.first_attempted_at or now
        delivery.last_attempted_at = now
        body = json.dumps(delivery.payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        timestamp = str(int(time.time()))
        secret = derive_webhook_secret(
            self._settings.secret_key, client.id, client.webhook_secret_version
        )
        signature = sign_outbound_body(secret, timestamp, body)
        headers = {
            "Content-Type": "application/json",
            SIGNATURE_HEADER: signature,
            TIMESTAMP_HEADER: timestamp,
            EVENT_ID_HEADER: delivery.public_event_id,
            EVENT_TYPE_HEADER: delivery.event_type,
        }
        try:
            response = await self._post(delivery.destination_url, body, headers)
        except httpx.TimeoutException:
            return await self._retry_or_fail(
                delivery, client, OutboundWebhookFailureCategory.TIMEOUT, "timeout"
            )
        except httpx.RequestError:
            return await self._retry_or_fail(
                delivery, client, OutboundWebhookFailureCategory.NETWORK, "network"
            )

        delivery.response_status_code = response.status_code
        if 200 <= response.status_code < 300:
            delivery.status = OutboundWebhookStatus.SENT
            delivery.failure_category = None
            delivery.failure_code = None
            delivery.next_retry_at = None
            if delivery.endpoint_id is not None:
                endpoint = await self._endpoints.get_by_id(delivery.endpoint_id)
                if endpoint is not None:
                    endpoint.last_delivered_at = now
                    endpoint.last_failure_category = None
                    endpoint.last_response_status_code = response.status_code
            await self._audit_system(
                "outbound_webhook_delivered",
                delivery.id,
                None,
                {
                    "event_id": delivery.public_event_id,
                    "response_status": response.status_code,
                    "attempt_count": delivery.attempt_count,
                },
                merchant_id=client.merchant_id,
                api_client_id=client.id,
            )
            await self._session.commit()
            logger.info(
                "outbound_webhook_delivered",
                event_id=delivery.public_event_id,
                client_id=str(client.id),
                response_status=response.status_code,
                attempt_count=delivery.attempt_count,
            )
            return delivery

        category = OutboundWebhookFailureCategory.HTTP_ERROR
        code = f"http_{response.status_code}"
        if response.status_code in RETRYABLE_STATUS_CODES:
            return await self._retry_or_fail(delivery, client, category, code)
        delivery.status = OutboundWebhookStatus.FAILED
        delivery.failure_category = category
        delivery.failure_code = code
        delivery.next_retry_at = None
        if delivery.endpoint_id is not None:
            endpoint = await self._endpoints.get_by_id(delivery.endpoint_id)
            if endpoint is not None:
                endpoint.last_failure_category = category
                endpoint.last_response_status_code = response.status_code
        await self._fail_audit(delivery, client)
        await self._session.commit()
        return delivery

    async def _retry_or_fail(
        self,
        delivery: OutboundWebhookDelivery,
        client: IntegrationClient,
        category: OutboundWebhookFailureCategory,
        code: str,
    ) -> OutboundWebhookDelivery:
        delivery.failure_category = category
        delivery.failure_code = code
        if delivery.attempt_count >= delivery.max_attempts:
            delivery.status = OutboundWebhookStatus.FAILED
            delivery.failure_category = OutboundWebhookFailureCategory.EXHAUSTED
            delivery.next_retry_at = None
            await self._fail_audit(delivery, client)
            await self._session.commit()
            return delivery
        delay_index = min(delivery.attempt_count - 1, len(BACKOFF_SECONDS) - 1)
        delivery.status = OutboundWebhookStatus.RETRYING
        delivery.next_retry_at = datetime.now(UTC) + timedelta(seconds=BACKOFF_SECONDS[delay_index])
        await self._session.commit()
        logger.warning(
            "outbound_webhook_retrying",
            event_id=delivery.public_event_id,
            client_id=str(client.id),
            attempt_count=delivery.attempt_count,
            failure_category=category.value,
        )
        raise OutboundWebhookRetryableError(code)

    async def _post(self, url: str, body: bytes, headers: dict[str, str]) -> httpx.Response:
        timeout = httpx.Timeout(self._settings.outbound_webhook_timeout_seconds)
        if self._http is not None:
            return await self._http.post(url, content=body, headers=headers)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            return await client.post(url, content=body, headers=headers)

    def _enqueue(self, delivery_id: uuid.UUID) -> None:
        try:
            from app.tasks.outbound_webhooks import deliver_outbound_webhook

            deliver_outbound_webhook.delay(str(delivery_id))
        except Exception as exc:  # pragma: no cover - broker optional in unit tests
            logger.warning(
                "outbound_webhook_enqueue_failed",
                delivery_id=str(delivery_id),
                error=str(exc),
            )

    async def _fail_audit(self, delivery: OutboundWebhookDelivery, client: IntegrationClient) -> None:
        await self._audit_system(
            "outbound_webhook_failed",
            delivery.id,
            None,
            {
                "event_id": delivery.public_event_id,
                "failure_category": delivery.failure_category.value if delivery.failure_category else None,
                "attempt_count": delivery.attempt_count,
            },
            merchant_id=client.merchant_id,
            api_client_id=client.id,
        )
        logger.warning(
            "outbound_webhook_failed",
            event_id=delivery.public_event_id,
            client_id=str(client.id),
            failure_category=delivery.failure_category.value if delivery.failure_category else None,
            attempt_count=delivery.attempt_count,
        )

    async def _audit_system(
        self,
        action: str,
        entity_id: uuid.UUID,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        *,
        merchant_id: uuid.UUID | None,
        api_client_id: uuid.UUID | None,
    ) -> None:
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=None,
                api_client_id=api_client_id,
                merchant_id=merchant_id,
                action=action,
                entity_type="outbound_webhook",
                entity_id=str(entity_id),
                before_state=before,
                after_state=after,
            )
        )


def _safe_destination(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        return False
    host = parsed.hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    return bool(host)


def _request_id() -> str | None:
    from structlog.contextvars import get_contextvars

    value = get_contextvars().get("request_id")
    return str(value) if value else None
