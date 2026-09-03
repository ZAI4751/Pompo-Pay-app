"""Add account security tokens and email verification columns.

Revision ID: 0020_account_security
Revises: 0019_m018_standard_bank
Create Date: 2026-09-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID

revision = "0020_account_security"
down_revision = "0019_m018_standard_bank"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing users default to verified; new user records insert false
    op.add_column(
        "users",
        sa.Column("is_email_verified", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "account_security_tokens",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("token_type", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_account_security_tokens_user_id", "account_security_tokens", ["user_id"]
    )
    op.create_index(
        "ix_account_security_tokens_token_type", "account_security_tokens", ["token_type"]
    )
    op.create_index(
        "ix_account_security_tokens_expires_at", "account_security_tokens", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_account_security_tokens_expires_at", table_name="account_security_tokens")
    op.drop_index("ix_account_security_tokens_token_type", table_name="account_security_tokens")
    op.drop_index("ix_account_security_tokens_user_id", table_name="account_security_tokens")
    op.drop_table("account_security_tokens")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "is_email_verified")
