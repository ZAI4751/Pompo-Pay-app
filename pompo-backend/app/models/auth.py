"""Refresh-token session model.

A ``RefreshSession`` row is created every time a refresh token is issued
(at login, and again on every rotation). The raw JWT is never stored — only
a SHA-256 hash of it, keyed by the token's ``jti`` claim (which doubles as
this row's primary key).

Rotation lineage is tracked via ``family_id``: the first session in a chain
sets ``family_id = id``; every rotation carries the same ``family_id``
forward. If a session that has already been rotated (``revoked_at`` set) is
presented again, that is a replay — see ``app/services/auth.py`` for the
detection and family-wide revocation this enables.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, GUID, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshSession(UUIDPrimaryKeyMixin, Base):
    """A single issued refresh token, tracked server-side for revocation."""

    __tablename__ = "refresh_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )
    # Deliberately a plain column, not a self-referential relationship — this
    # is a lineage pointer for audit/debugging, not something the ORM needs
    # to traverse, so it doesn't need the extra join complexity.
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("refresh_sessions.id", ondelete="SET NULL"), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship()

    @property
    def is_active(self) -> bool:
        """True if this session has not been revoked (expiry checked separately)."""
        return self.revoked_at is None

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RefreshSession id={self.id} user_id={self.user_id} revoked={self.revoked_at is not None}>"


class AccountSecurityToken(UUIDPrimaryKeyMixin, Base):
    """Cryptographic single-use token for email verification and password reset.

    Raw tokens are never stored in the database or logged — only a SHA-256
    digest is persisted. Single-use is enforced via ``used_at``.
    """

    __tablename__ = "account_security_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship()

    @property
    def is_valid(self) -> bool:
        """True if the token has not been used and has not yet expired."""
        if self.used_at is not None:
            return False
        now = datetime.now(timezone.utc)
        expires = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
        return expires > now

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AccountSecurityToken id={self.id} user_id={self.user_id} type={self.token_type!r}>"

