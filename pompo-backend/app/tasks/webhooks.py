"""Asynchronous webhook event processing tasks."""

from __future__ import annotations

import asyncio
import uuid

from app.core.logging import get_logger
from app.database.engine import create_engine, dispose_engine
from app.database.session import create_session_factory, reset_session_factory
from app.services.webhook import WebhookRetryableError, WebhookService
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _process_webhook_event_async(event_id: str) -> dict[str, str]:
    from app.core.config.base import get_settings

    settings = get_settings()
    create_engine(settings)
    factory = create_session_factory()
    try:
        async with factory() as session:
            service = WebhookService(session)
            event = await service.process_event(uuid.UUID(event_id))
            return {
                "status": event.processing_status.value,
                "event_id": str(event.id),
            }
    finally:
        await dispose_engine()
        reset_session_factory()


@celery_app.task(
    name="app.tasks.webhooks.process_webhook_event",
    bind=True,
    autoretry_for=(WebhookRetryableError,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5,
)
def process_webhook_event(self, event_id: str) -> dict[str, str]:
    """Process a persisted webhook event through the payment engine."""
    logger.info("webhook_task_started", task_id=self.request.id, event_id=event_id)
    try:
        result = asyncio.run(_process_webhook_event_async(event_id))
    except WebhookRetryableError:
        logger.warning("webhook_task_retry", task_id=self.request.id, event_id=event_id)
        raise
    except Exception:
        logger.exception("webhook_task_failed", task_id=self.request.id, event_id=event_id)
        raise
    logger.info("webhook_task_completed", task_id=self.request.id, event_id=event_id, **result)
    return result
