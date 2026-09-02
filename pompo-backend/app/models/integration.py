"""Integration application identity and outbound partner webhook deliveries."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    APIClientEnvironment,
    APIClientStatus,
    APIClientType,
    OutboundWebhookFailureCategory,
    OutboundWebhookStatus,
)

if TYPE_CHECKING:
    from app.models.audit import APIKey
    from app.models.organization import Branch, Merchant, Till
    from app.models.payment import Transaction
    from app.models.user import User


def _enum_values(enum_cls: type) -> list[str]:
    return [member.value for member in enum_cls]


class IntegrationClient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A machine identity for POS, developer, or partner integrations."""

    __tablename__ = "integration_clients"

    public_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_type: Mapped[APIClientType] = mapped_column(
        SAEnum(
            APIClientType,
            name="api_client_type",
            native_enum=False,
            length=32,
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )
    environment: Mapped[APIClientEnvironment] = mapped_column(
        SAEnum(
            APIClientEnvironment,
            name="api_client_environment",
            native_enum=False,
            length=16,
            values_callable=_enum_values,
        ),
        default=APIClientEnvironment.SANDBOX,
        nullable=False,
    )
    status: Mapped[APIClientStatus] = mapped_column(
        SAEnum(
            APIClientStatus,
            name="api_client_status",
            native_enum=False,
            length=16,
            values_callable=_enum_values,
        ),
        default=APIClientStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    till_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("tills.id", ondelete="SET NULL"), nullable=True, index=True
    )
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    webhook_secret_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    webhook_secret_prefix: Mapped[str | None] = mapped_column(String(16), nullable=True)
    rate_limit_requests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )

    merchant: Mapped["Merchant"] = relationship(back_populates="integration_clients")
    branch: Mapped["Branch | None"] = relationship()
    till: Mapped["Till | None"] = relationship()
    created_by: Mapped["User | None"] = relationship()
    api_keys: Mapped[list["APIKey"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    deliveries: Mapped[list["OutboundWebhookDelivery"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<IntegrationClient public_id={self.public_id!r} type={self.client_type!r}>"


class OutboundWebhookDelivery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persistent delivery record for POMPO → partner/POS webhooks."""

    __tablename__ = "outbound_webhook_deliveries"
    __table_args__ = (
        UniqueConstraint("public_event_id", name="uq_outbound_webhook_event_id"),
        UniqueConstraint(
            "client_id",
            "transaction_id",
            "event_type",
            name="uq_outbound_webhook_client_txn_type",
        ),
    )

    public_event_id: Mapped[str] = mapped_column(String(80), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("integration_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    destination_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[OutboundWebhookStatus] = mapped_column(
        SAEnum(
            OutboundWebhookStatus,
            name="outbound_webhook_status",
            native_enum=False,
            length=16,
            values_callable=_enum_values,
        ),
        default=OutboundWebhookStatus.PENDING,
        nullable=False,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    first_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )
    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True, index=True
    )
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_category: Mapped[OutboundWebhookFailureCategory | None] = mapped_column(
        SAEnum(
            OutboundWebhookFailureCategory,
            name="outbound_webhook_failure_category",
            native_enum=False,
            length=32,
            values_callable=_enum_values,
        ),
        nullable=True,
    )
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    client: Mapped[IntegrationClient] = relationship(back_populates="deliveries")
    transaction: Mapped["Transaction"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OutboundWebhookDelivery event={self.public_event_id!r} status={self.status!r}>"
