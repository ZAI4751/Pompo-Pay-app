"""Enforce one reusable static QR per merchant branch and till."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0022_persistent_static_qr"
down_revision = "0021_account_lifecycle"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_qr_codes_one_active_static_per_till"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "qr_codes",
        ["merchant_id", "branch_id", "till_id"],
        unique=True,
        postgresql_where=sa.text("qr_type = 'static' AND status = 'active'"),
        sqlite_where=sa.text("qr_type = 'static' AND status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="qr_codes")
