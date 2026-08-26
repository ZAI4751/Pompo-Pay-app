"""Add refresh_sessions table (M003 authentication).

Cross-checked against ``CreateTable(...).compile(dialect=postgresql.dialect())``
for the ``RefreshSession`` model, the same process used for revision
0001 — no live PostgreSQL instance was reachable to autogenerate against.
Run ``alembic upgrade head`` followed by ``alembic check`` against a real
database before trusting this in a live environment.

Revision ID: 0002_refresh_sessions
Revises: 0001_initial_domain_schema
Create Date: 2026-08-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID

# revision identifiers, used by Alembic.
revision = "0002_refresh_sessions"
down_revision = "0001_initial_domain_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_sessions",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("family_id", GUID(), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", GUID(), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["replaced_by_id"], ["refresh_sessions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])
    op.create_index("ix_refresh_sessions_family_id", "refresh_sessions", ["family_id"])


def downgrade() -> None:
    op.drop_table("refresh_sessions")
