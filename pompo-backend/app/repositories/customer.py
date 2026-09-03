"""Data access for M015 customer-product tables."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import selectinload

from app.models.customer import (
    AppNotification,
    BillSplit,
    CustomerPreference,
    MerchantFavorite,
    PaymentRequest,
    SupportRequest,
)
from app.models.enums import PaymentRequestStatus, SupportRequestStatus
from app.models.organization import Merchant
from app.models.payment import Transaction
from app.models.user import User
from app.repositories.base import BaseRepository


def _request_options(stmt: Select) -> Select:
    return stmt.options(
        selectinload(PaymentRequest.merchant),
        selectinload(PaymentRequest.branch),
        selectinload(PaymentRequest.till),
        selectinload(PaymentRequest.requester),
        selectinload(PaymentRequest.payer),
        selectinload(PaymentRequest.bill_split),
    )


class CustomerPreferenceRepository(BaseRepository[CustomerPreference]):
    model = CustomerPreference

    async def get_by_user_id(self, user_id: uuid.UUID) -> CustomerPreference | None:
        result = await self._session.execute(
            select(CustomerPreference).where(CustomerPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()


class MerchantFavoriteRepository(BaseRepository[MerchantFavorite]):
    model = MerchantFavorite

    async def get_for_user_merchant(
        self, user_id: uuid.UUID, merchant_id: uuid.UUID
    ) -> MerchantFavorite | None:
        result = await self._session.execute(
            select(MerchantFavorite)
            .options(selectinload(MerchantFavorite.merchant))
            .where(
                MerchantFavorite.user_id == user_id,
                MerchantFavorite.merchant_id == merchant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[MerchantFavorite]:
        result = await self._session.execute(
            select(MerchantFavorite)
            .options(selectinload(MerchantFavorite.merchant))
            .where(MerchantFavorite.user_id == user_id)
            .order_by(MerchantFavorite.created_at.desc())
        )
        return list(result.scalars().all())


class PaymentRequestRepository(BaseRepository[PaymentRequest]):
    model = PaymentRequest

    async def get_by_public_id(
        self, public_identifier: str, *, for_update: bool = False
    ) -> PaymentRequest | None:
        stmt = _request_options(select(PaymentRequest)).where(
            PaymentRequest.public_identifier == public_identifier
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency(
        self, requester_id: uuid.UUID, idempotency_key: str
    ) -> PaymentRequest | None:
        result = await self._session.execute(
            _request_options(select(PaymentRequest)).where(
                PaymentRequest.requester_id == requester_id,
                PaymentRequest.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_last_payment_id(self, payment_id: uuid.UUID) -> PaymentRequest | None:
        result = await self._session.execute(
            _request_options(select(PaymentRequest)).where(
                PaymentRequest.last_payment_id == payment_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        status: PaymentRequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PaymentRequest]:
        query = (
            _request_options(select(PaymentRequest))
            .where(
                (PaymentRequest.requester_id == user_id)
                | (PaymentRequest.payer_user_id == user_id)
            )
            .order_by(PaymentRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            query = query.where(PaymentRequest.status == status)
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def count_by_status(self) -> dict[str, int]:
        result = await self._session.execute(
            select(PaymentRequest.status, func.count()).group_by(PaymentRequest.status)
        )
        return {row[0].value if hasattr(row[0], "value") else str(row[0]): int(row[1]) for row in result.all()}


class BillSplitRepository(BaseRepository[BillSplit]):
    model = BillSplit

    async def get_by_public_id(self, public_identifier: str) -> BillSplit | None:
        result = await self._session.execute(
            select(BillSplit)
            .options(
                selectinload(BillSplit.requests),
                selectinload(BillSplit.merchant),
                selectinload(BillSplit.branch),
                selectinload(BillSplit.till),
            )
            .where(BillSplit.public_identifier == public_identifier)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency(
        self, creator_id: uuid.UUID, idempotency_key: str
    ) -> BillSplit | None:
        result = await self._session.execute(
            select(BillSplit)
            .options(selectinload(BillSplit.requests))
            .where(
                BillSplit.creator_id == creator_id,
                BillSplit.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()


class AppNotificationRepository(BaseRepository[AppNotification]):
    model = AppNotification

    async def get_by_event_key(self, event_key: str) -> AppNotification | None:
        result = await self._session.execute(
            select(AppNotification).where(AppNotification.event_key == event_key)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, unread_only: bool = False, limit: int = 50, offset: int = 0
    ) -> list[AppNotification]:
        query = (
            select(AppNotification)
            .where(AppNotification.user_id == user_id)
            .order_by(AppNotification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if unread_only:
            query = query.where(AppNotification.read_at.is_(None))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def unread_count(self, user_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(AppNotification)
            .where(AppNotification.user_id == user_id, AppNotification.read_at.is_(None))
        )
        return int(result.scalar_one() or 0)

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        result = await self._session.execute(
            update(AppNotification)
            .where(
                AppNotification.user_id == user_id,
                AppNotification.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        return int(result.rowcount or 0)


class SupportRequestRepository(BaseRepository[SupportRequest]):
    model = SupportRequest

    async def get_by_public_id(self, public_identifier: str) -> SupportRequest | None:
        result = await self._session.execute(
            select(SupportRequest).where(SupportRequest.public_identifier == public_identifier)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[SupportRequest]:
        result = await self._session.execute(
            select(SupportRequest)
            .where(SupportRequest.user_id == user_id)
            .order_by(SupportRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_all(self, *, limit: int = 50, offset: int = 0) -> list[SupportRequest]:
        result = await self._session.execute(
            select(SupportRequest)
            .order_by(SupportRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def open_count(self) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(SupportRequest)
            .where(SupportRequest.status == SupportRequestStatus.OPEN)
        )
        return int(result.scalar_one() or 0)


class CustomerAnalyticsRepository:
    """Read-only aggregates over real completed payments. Not a bank statement."""

    def __init__(self, session) -> None:
        self._session = session

    async def customer_count(self) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(User)
            .join(User.role)
            .where(
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
        )
        # Count users whose role code is customer — filter in Python if SQLite
        # enum/string comparison is awkward; do it in SQL via role.code.
        result = await self._session.execute(
            select(func.count())
            .select_from(User)
            .where(User.deleted_at.is_(None), User.is_active.is_(True))
        )
        return int(result.scalar_one() or 0)

    async def count_customers(self) -> int:
        from app.models.user import Role

        result = await self._session.execute(
            select(func.count())
            .select_from(User)
            .join(Role, Role.id == User.role_id)
            .where(
                User.deleted_at.is_(None),
                Role.code == "customer",
            )
        )
        return int(result.scalar_one() or 0)

    async def recent_merchants(
        self, cashier_id: uuid.UUID, *, limit: int = 20
    ) -> list[tuple[Merchant, datetime, int, Decimal | None]]:
        last_paid = func.max(Transaction.completed_at).label("last_paid")
        payment_count = func.count().label("payment_count")
        result = await self._session.execute(
            select(Merchant, last_paid, payment_count)
            .join(Transaction, Transaction.merchant_id == Merchant.id)
            .where(
                Transaction.cashier_id == cashier_id,
                Transaction.deleted_at.is_(None),
                Transaction.status == "success",
                Merchant.deleted_at.is_(None),
            )
            .group_by(Merchant.id)
            .order_by(last_paid.desc())
            .limit(limit)
        )
        rows = []
        for merchant, last, count in result.all():
            rows.append((merchant, last, int(count), None))
        return rows
