"""M015 customer product — favorites, payment requests, notifications, support.

Revision ID: 0016_m015_customer_product
Revises: 0015_m014_airtel_malawi
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID

revision = "0016_m015_customer_product"
down_revision = "0015_m014_airtel_malawi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_users_phone_active",
        "users",
        ["phone"],
        unique=True,
        postgresql_where=sa.text("phone IS NOT NULL AND deleted_at IS NULL"),
        sqlite_where=sa.text("phone IS NOT NULL AND deleted_at IS NULL"),
    )

    op.create_table(
        "customer_preferences",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("notify_payment_success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_payment_failed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_payment_updates", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_payment_requests", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("preferred_mode", sa.String(16), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "merchant_favorites",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("merchant_id", GUID(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "merchant_id", name="uq_merchant_favorite_user_merchant"),
    )
    op.create_index("ix_merchant_favorites_user_id", "merchant_favorites", ["user_id"])
    op.create_index("ix_merchant_favorites_merchant_id", "merchant_favorites", ["merchant_id"])

    op.create_table(
        "bill_splits",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_identifier", sa.String(40), nullable=False),
        sa.Column("creator_id", GUID(), nullable=False),
        sa.Column("merchant_id", GUID(), nullable=False),
        sa.Column("branch_id", GUID(), nullable=False),
        sa.Column("till_id", GUID(), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MWK"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.CheckConstraint("total_amount > 0", name="ck_bill_split_amount_positive"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["till_id"], ["tills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_identifier"),
        sa.UniqueConstraint("creator_id", "idempotency_key", name="uq_bill_split_creator_idempotency"),
    )
    op.create_index("ix_bill_splits_creator_id", "bill_splits", ["creator_id"])
    op.create_index("ix_bill_splits_merchant_id", "bill_splits", ["merchant_id"])
    op.create_index("ix_bill_splits_status", "bill_splits", ["status"])

    op.create_table(
        "payment_requests",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_identifier", sa.String(40), nullable=False),
        sa.Column("requester_id", GUID(), nullable=False),
        sa.Column("payer_user_id", GUID(), nullable=True),
        sa.Column("merchant_id", GUID(), nullable=False),
        sa.Column("branch_id", GUID(), nullable=False),
        sa.Column("till_id", GUID(), nullable=False),
        sa.Column("bill_split_id", GUID(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MWK"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_id", GUID(), nullable=True),
        sa.Column("last_payment_id", GUID(), nullable=True),
        sa.Column("payment_reference", sa.String(64), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("share_code", sa.String(80), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payment_request_amount_positive"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["till_id"], ["tills.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["bill_split_id"], ["bill_splits.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["last_payment_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_identifier"),
        sa.UniqueConstraint("payment_id"),
        sa.UniqueConstraint(
            "requester_id", "idempotency_key", name="uq_payment_request_requester_idempotency"
        ),
    )
    op.create_index("ix_payment_requests_public_identifier", "payment_requests", ["public_identifier"])
    op.create_index("ix_payment_requests_requester_id", "payment_requests", ["requester_id"])
    op.create_index("ix_payment_requests_payer_user_id", "payment_requests", ["payer_user_id"])
    op.create_index("ix_payment_requests_merchant_id", "payment_requests", ["merchant_id"])
    op.create_index("ix_payment_requests_bill_split_id", "payment_requests", ["bill_split_id"])
    op.create_index("ix_payment_requests_status", "payment_requests", ["status"])
    op.create_index("ix_payment_requests_expires_at", "payment_requests", ["expires_at"])
    op.create_index("ix_payment_requests_last_payment_id", "payment_requests", ["last_payment_id"])

    op.create_table(
        "app_notifications",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_identifier", sa.String(40), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("notification_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.String(500), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("payment_reference", sa.String(64), nullable=True),
        sa.Column("event_key", sa.String(160), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_identifier"),
        sa.UniqueConstraint("event_key", name="uq_app_notifications_event_key"),
    )
    op.create_index("ix_app_notifications_user_id", "app_notifications", ["user_id"])
    op.create_index("ix_app_notifications_notification_type", "app_notifications", ["notification_type"])
    op.create_index("ix_app_notifications_payment_reference", "app_notifications", ["payment_reference"])

    op.create_table(
        "support_requests",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_identifier", sa.String(40), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("message", sa.String(2000), nullable=False),
        sa.Column("payment_reference", sa.String(64), nullable=True),
        sa.Column("payment_request_id", GUID(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payment_request_id"], ["payment_requests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_identifier"),
    )
    op.create_index("ix_support_requests_user_id", "support_requests", ["user_id"])
    op.create_index("ix_support_requests_status", "support_requests", ["status"])
    op.create_index("ix_support_requests_payment_reference", "support_requests", ["payment_reference"])


def downgrade() -> None:
    op.drop_table("support_requests")
    op.drop_table("app_notifications")
    op.drop_table("payment_requests")
    op.drop_table("bill_splits")
    op.drop_table("merchant_favorites")
    op.drop_table("customer_preferences")
    op.drop_index("uq_users_phone_active", table_name="users")
