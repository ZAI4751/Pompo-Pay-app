"""Add normalized provider metadata to payment attempts."""

import sqlalchemy as sa
from alembic import op

revision = "0006_m007_attempt_metadata"
down_revision = "0005_m006_payment_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payment_attempts", sa.Column("provider_status", sa.String(64), nullable=True))
    op.add_column("payment_attempts", sa.Column("provider_request", sa.JSON(), nullable=True))
    op.add_column("payment_attempts", sa.Column("provider_response", sa.JSON(), nullable=True))
    op.add_column("payment_attempts", sa.Column("duration_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    for column in ("duration_ms", "provider_response", "provider_request", "provider_status"):
        op.drop_column("payment_attempts", column)
