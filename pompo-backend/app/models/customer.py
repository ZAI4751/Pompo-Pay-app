"""M015 customer-product domain: preferences, favorites, requests, notifications, support.

These records are instructions, memory, and communication. They never store
customer currency or wallet balances.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    BillSplitStatus,
    NotificationType,
    PaymentRequestStatus,
    SupportCategory,
    SupportRequestStatus,
)


def _enum_values(enum_cls: type) -> list[str]:
    return [member.value for member in enum_cls]


if TYPE_CHECKING:
    from app.models.organization import Branch, Merchant, Till
    from app.models.payment import Transaction
    from app.models.user import User


class CustomerPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-user notification and mode preferences. Not financial settings."""

    __tablename__ = "customer_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    notify_payment_success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_payment_failed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_payment_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_payment_requests: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preferred_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)

    user: Mapped["User"] = relationship()


class MerchantFavorite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A customer's shortcut to a merchant. Not a social follow graph."""

    __tablename__ = "merchant_favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "merchant_id", name="uq_merchant_favorite_user_merchant"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    user: Mapped["User"] = relationship()
    merchant: Mapped["Merchant"] = relationship()


class BillSplit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A group of payment requests that together cover one merchant bill."""

    __tablename__ = "bill_splits"
    __table_args__ = (
        UniqueConstraint("creator_id", "idempotency_key", name="uq_bill_split_creator_idempotency"),
        CheckConstraint("total_amount > 0", name="ck_bill_split_amount_positive"),
    )

    public_identifier: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    creator_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False
    )
    till_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("tills.id", ondelete="RESTRICT"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="MWK", nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[BillSplitStatus] = mapped_column(
        SAEnum(
            BillSplitStatus,
            name="bill_split_status",
            native_enum=False,
            length=16,
            values_callable=_enum_values,
        ),
        default=BillSplitStatus.PENDING,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)

    creator: Mapped["User"] = relationship()
    merchant: Mapped["Merchant"] = relationship()
    branch: Mapped["Branch"] = relationship()
    till: Mapped["Till"] = relationship()
    requests: Mapped[list["PaymentRequest"]] = relationship(back_populates="bill_split")


class PaymentRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Instruction for another user to pay a merchant. POMPO never holds the funds."""

    __tablename__ = "payment_requests"
    __table_args__ = (
        UniqueConstraint(
            "requester_id", "idempotency_key", name="uq_payment_request_requester_idempotency"
        ),
        CheckConstraint("amount > 0", name="ck_payment_request_amount_positive"),
    )

    public_identifier: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    requester_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False
    )
    till_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("tills.id", ondelete="RESTRICT"), nullable=False
    )
    bill_split_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("bill_splits.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="MWK", nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[PaymentRequestStatus] = mapped_column(
        SAEnum(
            PaymentRequestStatus,
            name="payment_request_status",
            native_enum=False,
            length=16,
            values_callable=_enum_values,
        ),
        default=PaymentRequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    last_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payment_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    share_code: Mapped[str] = mapped_column(String(80), nullable=False)

    requester: Mapped["User"] = relationship(foreign_keys=[requester_id])
    payer: Mapped["User | None"] = relationship(foreign_keys=[payer_user_id])
    merchant: Mapped["Merchant"] = relationship()
    branch: Mapped["Branch"] = relationship()
    till: Mapped["Till"] = relationship()
    bill_split: Mapped["BillSplit | None"] = relationship(back_populates="requests")
    payment: Mapped["Transaction | None"] = relationship(foreign_keys=[payment_id])


class AppNotification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """In-app notification for a real payment or request event."""

    __tablename__ = "app_notifications"
    __table_args__ = (UniqueConstraint("event_key", name="uq_app_notifications_event_key"),)

    public_identifier: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        SAEnum(
            NotificationType,
            name="notification_type",
            native_enum=False,
            length=64,
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_key: Mapped[str] = mapped_column(String(160), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship()


class SupportRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Lightweight customer support record. Not a full ticketing platform."""

    __tablename__ = "support_requests"

    public_identifier: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    category: Mapped[SupportCategory] = mapped_column(
        SAEnum(
            SupportCategory,
            name="support_category",
            native_enum=False,
            length=32,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=False)
    payment_reference: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payment_request_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("payment_requests.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[SupportRequestStatus] = mapped_column(
        SAEnum(
            SupportRequestStatus,
            name="support_request_status",
            native_enum=False,
            length=16,
            values_callable=_enum_values,
        ),
        default=SupportRequestStatus.OPEN,
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship()
