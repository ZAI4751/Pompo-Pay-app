"""Add user account lifecycle status.

Revision ID: 0021_account_lifecycle
Revises: 0020_account_security
Create Date: 2026-09-03

Existing ``is_active=false`` rows are backfilled as SUSPENDED so they are
not treated as customer self-deactivation (which would allow the
reactivation flow). New customer deactivations write DEACTIVATED.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0021_account_lifecycle"
down_revision = "0020_account_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("account_status", sa.String(16), server_default="active", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("reactivated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_users_account_status",
        "users",
        "account_status IN ('active', 'deactivated', 'suspended')",
    )
    op.execute(
        sa.text(
            "UPDATE users SET account_status = 'suspended' "
            "WHERE is_active IS FALSE AND account_status = 'active'"
        )
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_account_status", "users", type_="check")
    op.drop_column("users", "reactivated_at")
    op.drop_column("users", "deactivated_at")
    op.drop_column("users", "account_status")
