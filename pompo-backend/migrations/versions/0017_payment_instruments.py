"""Payment instruments — saved methods, not a wallet.

Revision ID: 0017_payment_instruments
Revises: 0016_m015_customer_product
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID

revision = "0017_payment_instruments"
down_revision = "0016_m015_customer_product"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_instruments",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("customer_id", GUID(), nullable=False),
        sa.Column("provider_id", GUID(), nullable=False),
        sa.Column("public_identifier", sa.String(40), nullable=False),
        sa.Column("instrument_type", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("masked_identifier", sa.String(64), nullable=False),
        sa.Column("token_reference", sa.String(128), nullable=False),
        sa.Column("provider_customer_reference", sa.String(128), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("authorization_state", sa.String(32), nullable=False, server_default="completed"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_sandbox", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_id"], ["payment_providers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_identifier", name="uq_payment_instruments_public_id"),
    )
    op.create_index("ix_payment_instruments_customer_id", "payment_instruments", ["customer_id"])
    op.create_index("ix_payment_instruments_provider_id", "payment_instruments", ["provider_id"])
    op.create_index("ix_payment_instruments_status", "payment_instruments", ["status"])
    op.create_index(
        "uq_payment_instruments_one_default",
        "payment_instruments",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("is_default IS TRUE AND status = 'active' AND revoked_at IS NULL"),
        sqlite_where=sa.text("is_default = 1 AND status = 'active' AND revoked_at IS NULL"),
    )
    op.create_index(
        "uq_payment_instruments_customer_provider_mask",
        "payment_instruments",
        ["customer_id", "provider_id", "instrument_type", "masked_identifier"],
        unique=True,
        postgresql_where=sa.text("status != 'revoked'"),
        sqlite_where=sa.text("status != 'revoked'"),
    )
    op.add_column(
        "transactions",
        sa.Column("payment_instrument_id", GUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_payment_instrument_id",
        "transactions",
        "payment_instruments",
        ["payment_instrument_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_transactions_payment_instrument_id", "transactions", ["payment_instrument_id"])
    op.execute(
        sa.text(
            "UPDATE payment_providers SET supported_payment_methods = "
            "'[\"mobile_money\", \"bank\", \"card\"]' "
            "WHERE code = 'simulated'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE payment_providers SET supported_payment_methods = "
            "'[\"mobile_money\", \"bank\"]' "
            "WHERE code = 'simulated'"
        )
    )
    op.drop_index("ix_transactions_payment_instrument_id", table_name="transactions")
    op.drop_constraint("fk_transactions_payment_instrument_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "payment_instrument_id")
    op.drop_index("uq_payment_instruments_customer_provider_mask", table_name="payment_instruments")
    op.drop_index("uq_payment_instruments_one_default", table_name="payment_instruments")
    op.drop_index("ix_payment_instruments_status", table_name="payment_instruments")
    op.drop_index("ix_payment_instruments_provider_id", table_name="payment_instruments")
    op.drop_index("ix_payment_instruments_customer_id", table_name="payment_instruments")
    op.drop_table("payment_instruments")
