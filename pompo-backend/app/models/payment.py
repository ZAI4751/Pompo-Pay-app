"""Payment domain: providers, transactions, attempts, webhooks, QR codes, receipts.

This milestone (M002) only establishes the persistence shape of the payment
domain. No provider adapters, state-machine enforcement, or orchestration
logic live here — see app/providers and the future transaction-engine
milestone for that.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentAttemptStatus, ProviderCode, TransactionStatus

if TYPE_CHECKING:
    from app.models.organization import Branch, Merchant, Till
    from app.models.user import User


class PaymentProvider(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A payment rail Pompo can (or will) bridge to."""

    __tablename__ = "payment_providers"

    code: Mapped[ProviderCode] = mapped_column(
        SAEnum(ProviderCode, name="provider_code", native_enum=False, length=32),
        nullable=False,
        unique=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    environment: Mapped[str] = mapped_column(String(32), default="sandbox", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False, index=True)
    supported_currencies: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=lambda: ["MWK"]
    )
    supported_payment_methods: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=lambda: ["mobile_money"]
    )
    capabilities: Mapped[dict[str, bool]] = mapped_column(JSON, nullable=False, default=dict)

    attempts: Mapped[list[PaymentAttempt]] = relationship(back_populates="provider")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PaymentProvider code={self.code!r}>"


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A single payment lifecycle from checkout creation to settlement."""

    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint(
            "merchant_id", "idempotency_key", name="uq_transaction_merchant_idempotency"
        ),
    )

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    till_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("tills.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("payment_providers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    cashier_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    reference: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, default=lambda: f"legacy-{uuid.uuid4().hex}"
    )
    request_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, default=lambda: uuid.uuid4().hex
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="MWK", nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    customer_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[TransactionStatus] = mapped_column(
        SAEnum(TransactionStatus, name="transaction_status", native_enum=False, length=32),
        default=TransactionStatus.CREATED,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )

    merchant: Mapped[Merchant] = relationship(back_populates="transactions")
    provider: Mapped[PaymentProvider | None] = relationship()
    branch: Mapped[Branch] = relationship()
    till: Mapped[Till] = relationship()
    cashier: Mapped[User | None] = relationship()
    attempts: Mapped[list[PaymentAttempt]] = relationship(
        back_populates="transaction",
        cascade="all, delete-orphan",
        order_by="PaymentAttempt.attempt_number",
    )
    qr_code: Mapped[QRCode | None] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", uselist=False
    )
    receipt: Mapped[Receipt | None] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", uselist=False
    )
    webhook_events: Mapped[list[WebhookEvent]] = relationship(back_populates="transaction")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Transaction id={self.id} status={self.status!r}>"


class PaymentAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One attempt to move a Transaction through a specific provider."""

    __tablename__ = "payment_attempts"
    __table_args__ = (
        UniqueConstraint("transaction_id", "attempt_number", name="uq_attempt_per_transaction"),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("payment_providers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PaymentAttemptStatus] = mapped_column(
        SAEnum(PaymentAttemptStatus, name="payment_attempt_status", native_enum=False, length=32),
        default=PaymentAttemptStatus.INITIATED,
        nullable=False,
    )
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_request: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provider_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )

    transaction: Mapped[Transaction] = relationship(back_populates="attempts")
    provider: Mapped[PaymentProvider] = relationship(back_populates="attempts")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PaymentAttempt id={self.id} status={self.status!r}>"


class WebhookEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An inbound webhook notification from a payment provider."""

    __tablename__ = "webhook_events"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("payment_providers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    signature_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )

    transaction: Mapped[Transaction | None] = relationship(back_populates="webhook_events")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WebhookEvent id={self.id} type={self.event_type!r}>"


class QRCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A generated QR payload for a checkout, scoped 1:1 to a Transaction."""

    __tablename__ = "qr_codes"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    payload: Mapped[str] = mapped_column(String(2000), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    transaction: Mapped[Transaction] = relationship(back_populates="qr_code")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<QRCode id={self.id} transaction_id={self.transaction_id}>"


class Receipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A generated receipt for a completed Transaction."""

    __tablename__ = "receipts"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    receipt_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    transaction: Mapped[Transaction] = relationship(back_populates="receipt")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Receipt id={self.id} number={self.receipt_number!r}>"
