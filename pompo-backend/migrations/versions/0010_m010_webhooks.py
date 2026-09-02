"""M010 webhooks — expand webhook_events for provider-neutral ingestion."""

import uuid

import sqlalchemy as sa
from alembic import op

from app.models.base import GUID

revision = "0010_m010_webhooks"
down_revision = "0009_m009_qr_payments"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("webhooks:read", "View inbound provider webhook events."),
)

ROLE_GRANTS = (
    ("platform_admin", ("webhooks:read",)),
    ("merchant_owner", ("webhooks:read",)),
)


def upgrade() -> None:
    op.add_column(
        "webhook_events",
        sa.Column("public_identifier", sa.String(32), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("provider_event_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("payment_attempt_id", GUID(), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("event_version", sa.String(16), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("payment_reference", sa.String(64), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("provider_transaction_reference", sa.String(128), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("timestamp_validated", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("processing_status", sa.String(32), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("processing_attempts", sa.Integer(), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("failure_category", sa.String(32), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("failure_code", sa.String(64), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE webhook_events
            SET public_identifier = 'WHK-' || UPPER(REPLACE(CAST(id AS TEXT), '-', '')),
                provider_event_id = 'legacy-' || CAST(id AS TEXT),
                received_at = created_at,
                timestamp_validated = FALSE,
                processing_status = CASE WHEN processed THEN 'processed' ELSE 'received' END,
                processing_attempts = 0
            WHERE public_identifier IS NULL
            """
        )
    )

    op.alter_column("webhook_events", "public_identifier", nullable=False)
    op.alter_column("webhook_events", "provider_event_id", nullable=False)
    op.alter_column("webhook_events", "received_at", nullable=False)
    op.alter_column("webhook_events", "timestamp_validated", nullable=False, server_default=sa.false())
    op.alter_column("webhook_events", "processing_status", nullable=False, server_default="received")
    op.alter_column("webhook_events", "processing_attempts", nullable=False, server_default="0")

    op.create_unique_constraint("uq_webhook_events_public_identifier", "webhook_events", ["public_identifier"])
    op.create_unique_constraint("uq_webhook_provider_event", "webhook_events", ["provider_id", "provider_event_id"])
    op.create_index("ix_webhook_events_event_type", "webhook_events", ["event_type"])
    op.create_index("ix_webhook_events_payment_reference", "webhook_events", ["payment_reference"])
    op.create_index("ix_webhook_events_processing_status", "webhook_events", ["processing_status"])
    op.create_index("ix_webhook_events_payment_attempt_id", "webhook_events", ["payment_attempt_id"])
    op.create_foreign_key(
        "fk_webhook_events_payment_attempt_id",
        "webhook_events",
        "payment_attempts",
        ["payment_attempt_id"],
        ["id"],
        ondelete="SET NULL",
    )

    for code, description in PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, description, created_at, updated_at) "
                "VALUES (:id, :code, :description, now(), now()) "
                "ON CONFLICT (code) DO NOTHING"
            ).bindparams(id=uuid.uuid4(), code=code, description=description)
        )

    for role_code, permission_codes in ROLE_GRANTS:
        for permission_code in permission_codes:
            op.execute(
                sa.text(
                    "INSERT INTO role_permissions (id, role_id, permission_id, granted_at) "
                    "SELECT :assignment_id, r.id, p.id, now() "
                    "FROM roles r CROSS JOIN permissions p "
                    "WHERE r.code = :role_code AND p.code = :permission_code "
                    "ON CONFLICT (role_id, permission_id) DO NOTHING"
                ).bindparams(
                    assignment_id=uuid.uuid4(),
                    role_code=role_code,
                    permission_code=permission_code,
                )
            )


def downgrade() -> None:
    permission_codes = ", ".join(f"'{code}'" for code, _ in PERMISSIONS)
    op.execute(
        sa.text(
            f"DELETE FROM role_permissions WHERE permission_id IN "
            f"(SELECT id FROM permissions WHERE code IN ({permission_codes}))"
        )
    )
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ({permission_codes})"))

    op.drop_constraint("fk_webhook_events_payment_attempt_id", "webhook_events", type_="foreignkey")
    op.drop_index("ix_webhook_events_payment_attempt_id", table_name="webhook_events")
    op.drop_index("ix_webhook_events_processing_status", table_name="webhook_events")
    op.drop_index("ix_webhook_events_payment_reference", table_name="webhook_events")
    op.drop_index("ix_webhook_events_event_type", table_name="webhook_events")
    op.drop_constraint("uq_webhook_provider_event", "webhook_events", type_="unique")
    op.drop_constraint("uq_webhook_events_public_identifier", "webhook_events", type_="unique")

    op.drop_column("webhook_events", "failure_code")
    op.drop_column("webhook_events", "failure_category")
    op.drop_column("webhook_events", "processing_attempts")
    op.drop_column("webhook_events", "processing_status")
    op.drop_column("webhook_events", "timestamp_validated")
    op.drop_column("webhook_events", "received_at")
    op.drop_column("webhook_events", "provider_transaction_reference")
    op.drop_column("webhook_events", "payment_reference")
    op.drop_column("webhook_events", "event_version")
    op.drop_column("webhook_events", "payment_attempt_id")
    op.drop_column("webhook_events", "provider_event_id")
    op.drop_column("webhook_events", "public_identifier")
