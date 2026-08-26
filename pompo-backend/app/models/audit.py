"""Developer-platform and audit models: APIKey, AuditLog."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, GUID, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.organization import Merchant
    from app.models.user import User


class APIKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A hashed API key issued to a merchant for server-to-server integration.

    The raw key is never stored — only ``key_prefix`` (shown to the merchant
    for identification) and ``hashed_key`` (for verification) persist.
    """

    __tablename__ = "api_keys"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    hashed_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )

    merchant: Mapped["Merchant"] = relationship(back_populates="api_keys")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<APIKey id={self.id} prefix={self.key_prefix!r}>"


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """An immutable record of a sensitive action taken in the system.

    Deliberately has no ``updated_at`` / soft-delete — audit rows must never
    be mutated or hidden. ``created_at`` alone establishes the timeline.
    """

    __tablename__ = "audit_logs"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    actor: Mapped["User | None"] = relationship()
    merchant: Mapped["Merchant | None"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog id={self.id} action={self.action!r}>"
