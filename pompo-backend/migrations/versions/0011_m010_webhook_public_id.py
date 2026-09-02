"""Widen webhook public_identifier to fit WHK- plus UUID hex."""

import sqlalchemy as sa
from alembic import op

revision = "0011_m010_webhook_public_id"
down_revision = "0010_m010_webhooks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "webhook_events",
        "public_identifier",
        existing_type=sa.String(32),
        type_=sa.String(40),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "webhook_events",
        "public_identifier",
        existing_type=sa.String(40),
        type_=sa.String(32),
        existing_nullable=False,
    )
