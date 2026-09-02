"""Database access for merchant QR codes."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.enums import QRStatus, QRType
from app.models.payment import QRCode
from app.repositories.base import BaseRepository


class QRCodeRepository(BaseRepository[QRCode]):
    model = QRCode

    async def get_by_public_identifier(self, public_identifier: str) -> QRCode | None:
        result = await self._session.execute(
            select(QRCode)
            .where(QRCode.public_identifier == public_identifier)
            .options(
                selectinload(QRCode.merchant),
                selectinload(QRCode.branch),
                selectinload(QRCode.till),
                selectinload(QRCode.transaction),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_merchant(
        self,
        merchant_id: uuid.UUID,
        *,
        branch_id: uuid.UUID | None = None,
        till_id: uuid.UUID | None = None,
        qr_type: QRType | None = None,
    ) -> list[QRCode]:
        query = (
            select(QRCode)
            .where(QRCode.merchant_id == merchant_id)
            .order_by(QRCode.created_at.desc())
        )
        if branch_id is not None:
            query = query.where(QRCode.branch_id == branch_id)
        if till_id is not None:
            query = query.where(QRCode.till_id == till_id)
        if qr_type is not None:
            query = query.where(QRCode.qr_type == qr_type)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_active_static_for_till(self, till_id: uuid.UUID) -> list[QRCode]:
        result = await self._session.execute(
            select(QRCode).where(
                QRCode.till_id == till_id,
                QRCode.qr_type == QRType.STATIC,
                QRCode.status == QRStatus.ACTIVE,
            )
        )
        return list(result.scalars().all())
