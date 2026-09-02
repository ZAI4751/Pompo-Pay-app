"""Database access for inbound webhook events."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.enums import WebhookProcessingStatus
from app.models.payment import WebhookEvent
from app.repositories.base import BaseRepository


class WebhookEventRepository(BaseRepository[WebhookEvent]):
    model = WebhookEvent

    async def get_by_public_identifier(self, public_identifier: str) -> WebhookEvent | None:
        result = await self._session.execute(
            select(WebhookEvent).where(WebhookEvent.public_identifier == public_identifier)
        )
        return result.scalar_one_or_none()

    async def get_by_provider_event(
        self, provider_id: uuid.UUID, provider_event_id: str
    ) -> WebhookEvent | None:
        result = await self._session.execute(
            select(WebhookEvent).where(
                WebhookEvent.provider_id == provider_id,
                WebhookEvent.provider_event_id == provider_event_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_processing(self, event_id: uuid.UUID) -> WebhookEvent | None:
        from app.models.payment import Transaction

        result = await self._session.execute(
            select(WebhookEvent)
            .where(WebhookEvent.id == event_id)
            .options(
                selectinload(WebhookEvent.transaction).selectinload(Transaction.attempts),
                selectinload(WebhookEvent.provider),
            )
        )
        return result.scalar_one_or_none()

    async def list_events(
        self,
        *,
        provider_code: str | None = None,
        processing_status: WebhookProcessingStatus | None = None,
        event_type: str | None = None,
        payment_reference: str | None = None,
        received_after: datetime | None = None,
        received_before: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WebhookEvent]:
        from app.models.enums import ProviderCode
        from app.models.payment import PaymentProvider

        stmt = select(WebhookEvent).order_by(WebhookEvent.received_at.desc()).limit(limit).offset(offset)
        if provider_code is not None:
            try:
                code = ProviderCode(provider_code)
            except ValueError:
                return []
            stmt = stmt.join(PaymentProvider).where(PaymentProvider.code == code)
        if processing_status is not None:
            stmt = stmt.where(WebhookEvent.processing_status == processing_status)
        if event_type is not None:
            stmt = stmt.where(WebhookEvent.event_type == event_type)
        if payment_reference is not None:
            stmt = stmt.where(WebhookEvent.payment_reference == payment_reference)
        if received_after is not None:
            stmt = stmt.where(WebhookEvent.received_at >= received_after)
        if received_before is not None:
            stmt = stmt.where(WebhookEvent.received_at <= received_before)
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())
