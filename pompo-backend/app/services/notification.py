"""In-app notification recording. Delivery is idempotent by event_key."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.customer import AppNotification, CustomerPreference
from app.models.enums import NotificationType
from app.models.user import User
from app.repositories.customer import AppNotificationRepository, CustomerPreferenceRepository

logger = get_logger(__name__)


class NotificationError(Exception):
    pass


class NotificationNotFoundError(NotificationError):
    pass


class NotificationForbiddenError(NotificationError):
    pass


def _public_id() -> str:
    return f"NTF-{uuid.uuid4().hex[:12].upper()}"


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._notifications = AppNotificationRepository(session)
        self._preferences = CustomerPreferenceRepository(session)

    async def record(
        self,
        *,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        body: str,
        event_key: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        payment_reference: str | None = None,
        commit: bool = False,
    ) -> AppNotification | None:
        existing = await self._notifications.get_by_event_key(event_key)
        if existing is not None:
            return existing
        if not await self._allowed(user_id, notification_type):
            return None
        row = AppNotification(
            public_identifier=_public_id(),
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
            payment_reference=payment_reference,
            event_key=event_key,
        )
        self._session.add(row)
        try:
            async with self._session.begin_nested():
                await self._session.flush()
        except IntegrityError:
            existing = await self._notifications.get_by_event_key(event_key)
            return existing
        logger.info(
            "notification_recorded",
            notification_id=str(row.id),
            user_id=str(user_id),
            notification_type=notification_type.value,
            payment_reference=payment_reference,
        )
        if commit:
            await self._session.commit()
        self._enqueue_delivery(row.id)
        return row

    async def list_for_user(
        self, actor: User, *, unread_only: bool = False, limit: int = 50, offset: int = 0
    ) -> tuple[list[AppNotification], int]:
        items = await self._notifications.list_for_user(
            actor.id, unread_only=unread_only, limit=min(limit, 100), offset=max(offset, 0)
        )
        unread = await self._notifications.unread_count(actor.id)
        return items, unread

    async def mark_read(self, actor: User, notification_id: uuid.UUID) -> AppNotification:
        row = await self._notifications.get_by_id(notification_id)
        if row is None or row.user_id != actor.id:
            raise NotificationNotFoundError("Notification not found")
        if row.read_at is None:
            row.read_at = datetime.now(UTC)
            await self._session.commit()
        return row

    async def mark_all_read(self, actor: User) -> int:
        count = await self._notifications.mark_all_read(actor.id)
        await self._session.commit()
        return count

    async def mark_delivered(self, notification_id: uuid.UUID) -> None:
        row = await self._notifications.get_by_id(notification_id)
        if row is None:
            return
        if row.delivered_at is None:
            row.delivered_at = datetime.now(UTC)
            await self._session.commit()
        logger.info("notification_delivered", notification_id=str(notification_id), user_id=str(row.user_id))

    async def _allowed(self, user_id: uuid.UUID, notification_type: NotificationType) -> bool:
        prefs = await self._preferences.get_by_user_id(user_id)
        if prefs is None:
            return True
        if notification_type in {
            NotificationType.PAYMENT_SUCCESS,
            NotificationType.MERCHANT_PAYMENT_RECEIVED,
        }:
            return prefs.notify_payment_success
        if notification_type in {
            NotificationType.PAYMENT_FAILED,
            NotificationType.MERCHANT_PAYMENT_FAILED,
        }:
            return prefs.notify_payment_failed
        if notification_type is NotificationType.PAYMENT_PENDING:
            return prefs.notify_payment_updates
        if notification_type in {
            NotificationType.PAYMENT_REQUEST_RECEIVED,
            NotificationType.PAYMENT_REQUEST_PAID,
            NotificationType.PAYMENT_REQUEST_EXPIRING,
            NotificationType.PAYMENT_REQUEST_EXPIRED,
        }:
            return prefs.notify_payment_requests
        return True

    @staticmethod
    def _enqueue_delivery(notification_id: uuid.UUID) -> None:
        try:
            from app.tasks.notifications import deliver_notification

            deliver_notification.delay(str(notification_id))
        except Exception:
            logger.info(
                "notification_enqueue_skipped",
                notification_id=str(notification_id),
            )
