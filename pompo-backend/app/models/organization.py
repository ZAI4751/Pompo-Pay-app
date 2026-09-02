"""Organizational hierarchy: Merchant -> Branch -> Till."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, GUID, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.audit import APIKey
    from app.models.integration import IntegrationClient
    from app.models.payment import Transaction
    from app.models.user import User


class Merchant(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A registered business using Pompo to accept payments."""

    __tablename__ = "merchants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    branches: Mapped[list["Branch"]] = relationship(
        back_populates="merchant", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(back_populates="merchant")
    api_keys: Mapped[list["APIKey"]] = relationship(back_populates="merchant")
    integration_clients: Mapped[list["IntegrationClient"]] = relationship(
        back_populates="merchant"
    )
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="merchant")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Merchant id={self.id} name={self.name!r}>"


class Branch(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A physical or logical location belonging to a merchant."""

    __tablename__ = "branches"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    merchant: Mapped["Merchant"] = relationship(back_populates="branches")
    tills: Mapped[list["Till"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(back_populates="branch")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Branch id={self.id} name={self.name!r}>"


class Till(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A checkout point (physical or virtual) within a branch."""

    __tablename__ = "tills"
    __table_args__ = (UniqueConstraint("branch_id", "code", name="uq_till_branch_code"),)

    branch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    branch: Mapped["Branch"] = relationship(back_populates="tills")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Till id={self.id} code={self.code!r}>"
