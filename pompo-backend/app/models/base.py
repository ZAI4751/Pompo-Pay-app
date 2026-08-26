"""Declarative base, portable column types, and shared mixins for all domain models.

Design notes
------------
* Primary keys are UUIDs everywhere (per architecture requirements). We use a
  portable ``GUID`` TypeDecorator rather than ``postgresql.UUID`` directly so
  the same model layer can be exercised against SQLite in fast unit tests
  while still using native ``uuid`` columns on PostgreSQL in production.
* Every table gets ``created_at`` / ``updated_at`` via ``TimestampMixin``.
* Tables that support soft-deletion get ``deleted_at`` via ``SoftDeleteMixin``.
  Soft-deleted rows are never filtered automatically by the ORM — repositories
  are responsible for excluding them (see app/repositories/base.py) so that
  the query behavior stays explicit and auditable.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import CHAR


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp (used for portable server-side defaults)."""
    return datetime.now(timezone.utc)


class GUID(TypeDecorator):
    """Platform-independent UUID column.

    Uses PostgreSQL's native UUID type when available, otherwise stores the
    value as a 32-character hex string (e.g. for SQLite in tests).
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        return value.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key generated client-side."""

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4, nullable=False
    )


class TimestampMixin:
    """Adds created_at / updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SoftDeleteMixin:
    """Adds a nullable deleted_at column for soft deletion.

    A row is considered active when ``deleted_at IS NULL``. Repositories must
    filter on this explicitly (see ``BaseRepository.not_deleted``) — it is
    intentionally NOT enforced via a global ORM event so that admin/audit
    tooling can still query soft-deleted rows when it needs to.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
