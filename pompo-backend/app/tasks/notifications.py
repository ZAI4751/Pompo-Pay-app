"""Celery delivery for in-app notifications. Idempotent by delivered_at."""

from __future__ import annotations

import asyncio
import uuid

from app.core.logging import get_logger
from app.database.engine import create_engine, dispose_engine
from app.database.session import create_session_factory, reset_session_factory
from app.services.notification import NotificationService
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _deliver_async(notification_id: str) -> dict[str, str]:
    from app.core.config.base import get_settings

    settings = get_settings()
    create_engine(settings)
    factory = create_session_factory()
    try:
        async with factory() as session:
            service = NotificationService(session)
            await service.mark_delivered(uuid.UUID(notification_id))
            return {"status": "delivered", "notification_id": notification_id}
    finally:
        await dispose_engine()
        reset_session_factory()


@celery_app.task(
    name="app.tasks.notifications.deliver_notification",
    bind=True,
    max_retries=3,
    retry_backoff=True,
)
def deliver_notification(self, notification_id: str) -> dict[str, str]:
    """Mark a persisted notification as delivered. Safe to retry."""
    logger.info("notification_task_started", task_id=self.request.id, notification_id=notification_id)
    try:
        result = asyncio.run(_deliver_async(notification_id))
    except Exception:
        logger.exception("notification_task_failed", task_id=self.request.id, notification_id=notification_id)
        raise
    logger.info("notification_task_completed", task_id=self.request.id, **result)
    return result
