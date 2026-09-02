"""Asynchronous outbound partner webhook delivery."""

from __future__ import annotations

import asyncio
import uuid

from app.core.logging import get_logger
from app.database.engine import create_engine, dispose_engine
from app.database.session import create_session_factory, reset_session_factory
from app.services.outbound_webhook import OutboundWebhookRetryableError, OutboundWebhookService
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _deliver_async(delivery_id: str) -> dict[str, str]:
    from app.core.config.base import get_settings

    settings = get_settings()
    create_engine(settings)
    factory = create_session_factory()
    try:
        async with factory() as session:
            service = OutboundWebhookService(session)
            delivery = await service.deliver(uuid.UUID(delivery_id))
            return {
                "status": delivery.status.value,
                "event_id": delivery.public_event_id,
            }
    finally:
        await dispose_engine()
        reset_session_factory()


@celery_app.task(
    name="app.tasks.outbound_webhooks.deliver_outbound_webhook",
    bind=True,
    autoretry_for=(OutboundWebhookRetryableError,),
    retry_backoff=True,
    retry_backoff_max=900,
    max_retries=5,
)
def deliver_outbound_webhook(self, delivery_id: str) -> dict[str, str]:
    """Deliver a queued partner/POS webhook with bounded retries."""
    logger.info("outbound_webhook_task_started", task_id=self.request.id, delivery_id=delivery_id)
    try:
        result = asyncio.run(_deliver_async(delivery_id))
    except OutboundWebhookRetryableError:
        logger.warning("outbound_webhook_task_retry", task_id=self.request.id, delivery_id=delivery_id)
        raise
    except Exception:
        logger.exception("outbound_webhook_task_failed", task_id=self.request.id, delivery_id=delivery_id)
        raise
    logger.info("outbound_webhook_task_completed", task_id=self.request.id, **result)
    return result
