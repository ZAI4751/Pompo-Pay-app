"""Payment instrument persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import PaymentInstrumentStatus
from app.models.payment import PaymentInstrument
from app.repositories.base import BaseRepository


class PaymentInstrumentRepository(BaseRepository[PaymentInstrument]):
    model = PaymentInstrument

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    def _base(self):
        return select(PaymentInstrument).options(
            selectinload(PaymentInstrument.provider),
            selectinload(PaymentInstrument.customer),
        )

    async def get_by_public_id(self, public_identifier: str) -> PaymentInstrument | None:
        return await self._session.scalar(
            self._base().where(PaymentInstrument.public_identifier == public_identifier)
        )

    async def list_for_customer(self, customer_id: uuid.UUID) -> list[PaymentInstrument]:
        result = await self._session.scalars(
            self._base()
            .where(PaymentInstrument.customer_id == customer_id)
            .where(PaymentInstrument.status != PaymentInstrumentStatus.REVOKED)
            .order_by(PaymentInstrument.is_default.desc(), PaymentInstrument.created_at.desc())
        )
        return list(result)

    async def list_all_safe(self, *, limit: int, offset: int) -> list[PaymentInstrument]:
        result = await self._session.scalars(
            self._base()
            .order_by(PaymentInstrument.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result)

    async def get_default(self, customer_id: uuid.UUID) -> PaymentInstrument | None:
        return await self._session.scalar(
            self._base().where(
                PaymentInstrument.customer_id == customer_id,
                PaymentInstrument.is_default.is_(True),
                PaymentInstrument.status == PaymentInstrumentStatus.ACTIVE,
            )
        )
