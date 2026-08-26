"""Add active-state support for M004 RBAC roles.

Revision ID: 0003_rbac_authorization
Revises: 0002_refresh_sessions
Create Date: 2026-08-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_rbac_authorization"
down_revision = "0002_refresh_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "roles",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("roles", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("roles", "is_active")