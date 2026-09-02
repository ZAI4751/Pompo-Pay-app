"""Settlement and reconciliation financial control models.

PAYMENT, PROVIDER TRANSACTION, SETTLEMENT, and RECONCILIATION remain distinct.
These tables never mutate payment history; corrections are append-only.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    FeeType,
    MismatchCategory,
    ReconciliationRunStatus,
    ReconciliationStatus,
    SettlementBatchStatus,
    SettlementStatus,
)

if TYPE_CHECKING:
    from app.models.organization import Branch, Merchant
    from app.models.payment import PaymentAttempt, PaymentProvider, Transaction
    from app.models.user import User


def _enum_values(enum_cls: type) -> list[str]:
    return [member.value for member in enum_cls]


class PricingSchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Forward-compatible fee schedule. Not a full billing platform.

    Specificity: merchant+provider > merchant > provider > platform default.
    """

    __tablename__ = "pricing_schedules"
    __table_args__ = (
        UniqueConstraint("scope_key", name="uq_pricing_schedule_scope"),
        CheckConstraint("pompo_fixed_amount >= 0", name="ck_pricing_pompo_fixed_nonneg"),
        CheckConstraint("provider_cost_fixed >= 0", name="ck_pricing_provider_fixed_nonneg"),
        CheckConstraint("pompo_percentage_bps >= 0", name="ck_pricing_pompo_bps_nonneg"),
        CheckConstraint("provider_cost_percentage_bps >= 0", name="ck_pricing_provider_bps_nonneg"),
    )

    scope_key: Mapped[str] = mapped_column(String(160), nullable=False)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("payment_providers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="MWK", nullable=False)
    pompo_fee_type: Mapped[FeeType] = mapped_column(
        SAEnum(FeeType, name="fee_type", native_enum=False, length=16, values_callable=_enum_values),
        default=FeeType.ZERO,
        nullable=False,
    )
    pompo_fixed_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    pompo_percentage_bps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pompo_min_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    pompo_max_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    provider_cost_type: Mapped[FeeType] = mapped_column(
        SAEnum(
            FeeType,
            name="provider_cost_type",
            native_enum=False,
            length=16,
            values_callable=_enum_values,
        ),
        default=FeeType.ZERO,
        nullable=False,
    )
    provider_cost_fixed: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    provider_cost_percentage_bps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    provider: Mapped[PaymentProvider | None] = relationship()
    merchant: Mapped[Merchant | None] = relationship()


class SettlementBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A provider-reported settlement file/batch. Duplicate batches are rejected."""

    __tablename__ = "settlement_batches"
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "external_batch_reference",
            name="uq_settlement_batch_provider_reference",
        ),
        CheckConstraint("record_count >= 0", name="ck_settlement_batch_count_nonneg"),
        CheckConstraint("total_gross >= 0", name="ck_settlement_batch_gross_nonneg"),
        CheckConstraint("total_provider_fees >= 0", name="ck_settlement_batch_provider_fees_nonneg"),
        CheckConstraint("total_pompo_fees >= 0", name="ck_settlement_batch_pompo_fees_nonneg"),
    )

    public_identifier: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("payment_providers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    external_batch_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    settlement_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="MWK", nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_gross: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    total_provider_fees: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    total_pompo_fees: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    total_merchant_net: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    status: Mapped[SettlementBatchStatus] = mapped_column(
        SAEnum(
            SettlementBatchStatus,
            name="settlement_batch_status",
            native_enum=False,
            length=32,
            values_callable=_enum_values,
        ),
        default=SettlementBatchStatus.RECEIVED,
        nullable=False,
        index=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    provider: Mapped[PaymentProvider] = relationship()
    settlements: Mapped[list[Settlement]] = relationship(back_populates="batch")


class Settlement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """What a provider reports as financially settled. Not a payment record."""

    __tablename__ = "settlements"
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "provider_settlement_reference",
            name="uq_settlement_provider_reference",
        ),
        CheckConstraint("gross_amount >= 0", name="ck_settlement_gross_nonneg"),
        CheckConstraint("provider_fee >= 0", name="ck_settlement_provider_fee_nonneg"),
        CheckConstraint("pompo_fee >= 0", name="ck_settlement_pompo_fee_nonneg"),
        Index("ix_settlements_payment_reference", "payment_reference"),
        Index("ix_settlements_provider_txn_ref", "provider_transaction_reference"),
        Index("ix_settlements_settlement_date", "settlement_date"),
    )

    public_identifier: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("settlement_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("payment_providers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider_settlement_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    payment_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("payment_attempts.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    payment_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_transaction_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    provider_fee: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    pompo_fee: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    merchant_net: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="MWK", nullable=False)
    status: Mapped[SettlementStatus] = mapped_column(
        SAEnum(
            SettlementStatus,
            name="settlement_status",
            native_enum=False,
            length=32,
            values_callable=_enum_values,
        ),
        default=SettlementStatus.RECEIVED,
        nullable=False,
        index=True,
    )
    settlement_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    batch: Mapped[SettlementBatch] = relationship(back_populates="settlements")
    provider: Mapped[PaymentProvider] = relationship()
    transaction: Mapped[Transaction | None] = relationship()
    payment_attempt: Mapped[PaymentAttempt | None] = relationship()
    merchant: Mapped[Merchant | None] = relationship()
    branch: Mapped[Branch | None] = relationship()
    reconciliation: Mapped[ReconciliationRecord | None] = relationship(
        back_populates="settlement", uselist=False
    )


class ReconciliationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A dated window of settlement-versus-payment comparison."""

    __tablename__ = "reconciliation_runs"

    public_identifier: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("payment_providers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    records_examined: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unmatched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discrepancy_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    partial_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    investigation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_expected: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    total_actual: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    total_variance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    status: Mapped[ReconciliationRunStatus] = mapped_column(
        SAEnum(
            ReconciliationRunStatus,
            name="reconciliation_run_status",
            native_enum=False,
            length=32,
            values_callable=_enum_values,
        ),
        default=ReconciliationRunStatus.PENDING,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    provider: Mapped[PaymentProvider | None] = relationship()
    records: Mapped[list[ReconciliationRecord]] = relationship(back_populates="run")


class ReconciliationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Auditable comparison of expected POMPO amounts versus actual settlement."""

    __tablename__ = "reconciliation_records"
    __table_args__ = (
        UniqueConstraint("settlement_id", name="uq_recon_settlement"),
        Index(
            "uq_recon_missing_settlement_txn",
            "transaction_id",
            unique=True,
            sqlite_where=text("settlement_id IS NULL AND mismatch_category = 'missing_settlement'"),
            postgresql_where=text(
                "settlement_id IS NULL AND mismatch_category = 'missing_settlement'"
            ),
        ),
        Index("ix_recon_status", "status"),
        Index("ix_recon_category", "mismatch_category"),
    )

    public_identifier: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("reconciliation_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    settlement_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("settlements.id", ondelete="RESTRICT"), nullable=True
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    payment_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("payment_attempts.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[ReconciliationStatus] = mapped_column(
        SAEnum(
            ReconciliationStatus,
            name="reconciliation_status",
            native_enum=False,
            length=32,
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    mismatch_category: Mapped[MismatchCategory | None] = mapped_column(
        SAEnum(
            MismatchCategory,
            name="mismatch_category",
            native_enum=False,
            length=64,
            values_callable=_enum_values,
        ),
        nullable=True,
    )
    expected_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    actual_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    variance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    expected_provider_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    actual_provider_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    expected_pompo_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    actual_pompo_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    expected_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    actual_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    pompo_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    run: Mapped[ReconciliationRun | None] = relationship(back_populates="records")
    settlement: Mapped[Settlement | None] = relationship(back_populates="reconciliation")
    transaction: Mapped[Transaction | None] = relationship()
    payment_attempt: Mapped[PaymentAttempt | None] = relationship()
    resolved_by: Mapped[User | None] = relationship()
