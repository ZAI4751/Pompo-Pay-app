"""Persistence for integration clients, API keys, and outbound deliveries."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import APIKey, IntegrationClient, IntegrationWebhookEndpoint, OutboundWebhookDelivery
from app.models.enums import OutboundWebhookStatus
from app.repositories.base import BaseRepository


class IntegrationClientRepository(BaseRepository[IntegrationClient]):
    model = IntegrationClient

    async def get_by_public_id(self, public_id: str) -> IntegrationClient | None:
        stmt = (
            select(IntegrationClient)
            .where(IntegrationClient.public_id == public_id)
            .options(
                selectinload(IntegrationClient.api_keys),
                selectinload(IntegrationClient.webhook_endpoints),
            )
        )
        return await self._session.scalar(stmt)

    async def get_with_keys(self, client_id: uuid.UUID) -> IntegrationClient | None:
        stmt = (
            select(IntegrationClient)
            .where(IntegrationClient.id == client_id)
            .options(
                selectinload(IntegrationClient.api_keys),
                selectinload(IntegrationClient.webhook_endpoints),
            )
        )
        return await self._session.scalar(stmt)

    async def list_clients(
        self,
        *,
        merchant_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[IntegrationClient]:
        stmt = (
            select(IntegrationClient)
            .options(
                selectinload(IntegrationClient.api_keys),
                selectinload(IntegrationClient.webhook_endpoints),
            )
            .order_by(IntegrationClient.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if merchant_id is not None:
            stmt = stmt.where(IntegrationClient.merchant_id == merchant_id)
        return list(await self._session.scalars(stmt))


class APIKeyRepository(BaseRepository[APIKey]):
    model = APIKey

    async def get_by_hashed_key(self, hashed_key: str) -> APIKey | None:
        stmt = (
            select(APIKey)
            .where(APIKey.hashed_key == hashed_key)
            .options(selectinload(APIKey.client))
        )
        return await self._session.scalar(stmt)

    async def list_for_client(self, client_id: uuid.UUID) -> list[APIKey]:
        stmt = (
            select(APIKey)
            .where(APIKey.client_id == client_id)
            .order_by(APIKey.created_at.desc())
        )
        return list(await self._session.scalars(stmt))


class IntegrationWebhookEndpointRepository(BaseRepository[IntegrationWebhookEndpoint]):
    model = IntegrationWebhookEndpoint

    async def list_for_client(
        self, client_id: uuid.UUID, *, active_only: bool = False
    ) -> list[IntegrationWebhookEndpoint]:
        stmt = (
            select(IntegrationWebhookEndpoint)
            .where(IntegrationWebhookEndpoint.client_id == client_id)
            .order_by(IntegrationWebhookEndpoint.created_at.asc())
        )
        if active_only:
            stmt = stmt.where(IntegrationWebhookEndpoint.is_active.is_(True))
        return list(await self._session.scalars(stmt))

    async def get_for_client(
        self, client_id: uuid.UUID, endpoint_id: uuid.UUID
    ) -> IntegrationWebhookEndpoint | None:
        stmt = select(IntegrationWebhookEndpoint).where(
            IntegrationWebhookEndpoint.id == endpoint_id,
            IntegrationWebhookEndpoint.client_id == client_id,
        )
        return await self._session.scalar(stmt)

    async def get_by_client_and_url(
        self, client_id: uuid.UUID, destination_url: str
    ) -> IntegrationWebhookEndpoint | None:
        stmt = select(IntegrationWebhookEndpoint).where(
            IntegrationWebhookEndpoint.client_id == client_id,
            IntegrationWebhookEndpoint.destination_url == destination_url,
        )
        return await self._session.scalar(stmt)


class OutboundWebhookDeliveryRepository(BaseRepository[OutboundWebhookDelivery]):
    model = OutboundWebhookDelivery

    async def get_by_identity(
        self,
        *,
        client_id: uuid.UUID,
        transaction_id: uuid.UUID,
        event_type: str,
        destination_url: str,
    ) -> OutboundWebhookDelivery | None:
        stmt = select(OutboundWebhookDelivery).where(
            OutboundWebhookDelivery.client_id == client_id,
            OutboundWebhookDelivery.transaction_id == transaction_id,
            OutboundWebhookDelivery.event_type == event_type,
            OutboundWebhookDelivery.destination_url == destination_url,
        )
        return await self._session.scalar(stmt)

    async def get_by_event_id(self, public_event_id: str) -> OutboundWebhookDelivery | None:
        stmt = select(OutboundWebhookDelivery).where(
            OutboundWebhookDelivery.public_event_id == public_event_id
        )
        return await self._session.scalar(stmt)

    async def list_for_client(
        self,
        client_id: uuid.UUID,
        *,
        status: OutboundWebhookStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[OutboundWebhookDelivery]:
        stmt = (
            select(OutboundWebhookDelivery)
            .where(OutboundWebhookDelivery.client_id == client_id)
            .order_by(OutboundWebhookDelivery.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            stmt = stmt.where(OutboundWebhookDelivery.status == status)
        return list(await self._session.scalars(stmt))

    async def list_due(self, now: datetime, *, limit: int = 50) -> list[OutboundWebhookDelivery]:
        stmt = (
            select(OutboundWebhookDelivery)
            .where(
                OutboundWebhookDelivery.status.in_(
                    (OutboundWebhookStatus.PENDING, OutboundWebhookStatus.RETRYING)
                ),
                OutboundWebhookDelivery.next_retry_at.is_not(None),
                OutboundWebhookDelivery.next_retry_at <= now,
            )
            .order_by(OutboundWebhookDelivery.next_retry_at.asc())
            .limit(limit)
        )
        return list(await self._session.scalars(stmt))
