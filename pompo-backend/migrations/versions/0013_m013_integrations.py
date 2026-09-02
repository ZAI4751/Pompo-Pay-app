"""M013 POS + developer platform — integration clients, API keys, outbound webhooks.

Revision ID: 0013_m013_integrations
Revises: 0012_m012_mobile
Create Date: 2026-09-02
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

from app.models.base import GUID

revision = "0013_m013_integrations"
down_revision = "0012_m012_mobile"
branch_labels = None
depends_on = None

PERMISSIONS: tuple[tuple[str, str], ...] = ()

ROLE_GRANTS = (
    ("platform_admin", ("api_keys:read", "api_keys:create", "api_keys:revoke")),
    ("merchant_owner", ("api_keys:read", "api_keys:create", "api_keys:revoke")),
)


def upgrade() -> None:
    op.create_table(
        "integration_clients",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("client_type", sa.String(32), nullable=False),
        sa.Column("environment", sa.String(16), nullable=False, server_default="sandbox"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("merchant_id", GUID(), nullable=False),
        sa.Column("branch_id", GUID(), nullable=True),
        sa.Column("till_id", GUID(), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("webhook_url", sa.String(1000), nullable=True),
        sa.Column("webhook_secret_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("webhook_secret_prefix", sa.String(16), nullable=True),
        sa.Column("rate_limit_requests", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", GUID(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["till_id"], ["tills.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_integration_clients_client_type", "integration_clients", ["client_type"])
    op.create_index("ix_integration_clients_status", "integration_clients", ["status"])
    op.create_index("ix_integration_clients_merchant_id", "integration_clients", ["merchant_id"])
    op.create_index("ix_integration_clients_branch_id", "integration_clients", ["branch_id"])
    op.create_index("ix_integration_clients_till_id", "integration_clients", ["till_id"])

    op.add_column("api_keys", sa.Column("client_id", GUID(), nullable=True))
    op.add_column("api_keys", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_api_keys_client_id", "api_keys", ["client_id"])
    op.create_foreign_key(
        "fk_api_keys_client_id",
        "api_keys",
        "integration_clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.add_column("transactions", sa.Column("api_client_id", GUID(), nullable=True))
    op.create_index("ix_transactions_api_client_id", "transactions", ["api_client_id"])
    op.create_foreign_key(
        "fk_transactions_api_client_id",
        "transactions",
        "integration_clients",
        ["api_client_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("audit_logs", sa.Column("api_client_id", GUID(), nullable=True))
    op.create_index("ix_audit_logs_api_client_id", "audit_logs", ["api_client_id"])
    op.create_foreign_key(
        "fk_audit_logs_api_client_id",
        "audit_logs",
        "integration_clients",
        ["api_client_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "outbound_webhook_deliveries",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("public_event_id", sa.String(80), nullable=False),
        sa.Column("client_id", GUID(), nullable=False),
        sa.Column("transaction_id", GUID(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("destination_url", sa.String(1000), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("first_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("failure_category", sa.String(32), nullable=True),
        sa.Column("failure_code", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["integration_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_event_id", name="uq_outbound_webhook_event_id"),
        sa.UniqueConstraint(
            "client_id",
            "transaction_id",
            "event_type",
            name="uq_outbound_webhook_client_txn_type",
        ),
    )
    op.create_index(
        "ix_outbound_webhook_deliveries_client_id", "outbound_webhook_deliveries", ["client_id"]
    )
    op.create_index(
        "ix_outbound_webhook_deliveries_transaction_id",
        "outbound_webhook_deliveries",
        ["transaction_id"],
    )
    op.create_index(
        "ix_outbound_webhook_deliveries_event_type", "outbound_webhook_deliveries", ["event_type"]
    )
    op.create_index(
        "ix_outbound_webhook_deliveries_status", "outbound_webhook_deliveries", ["status"]
    )
    op.create_index(
        "ix_outbound_webhook_deliveries_next_retry_at",
        "outbound_webhook_deliveries",
        ["next_retry_at"],
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
    op.drop_table("outbound_webhook_deliveries")
    op.drop_constraint("fk_audit_logs_api_client_id", "audit_logs", type_="foreignkey")
    op.drop_index("ix_audit_logs_api_client_id", table_name="audit_logs")
    op.drop_column("audit_logs", "api_client_id")
    op.drop_constraint("fk_transactions_api_client_id", "transactions", type_="foreignkey")
    op.drop_index("ix_transactions_api_client_id", table_name="transactions")
    op.drop_column("transactions", "api_client_id")
    op.drop_constraint("fk_api_keys_client_id", "api_keys", type_="foreignkey")
    op.drop_index("ix_api_keys_client_id", table_name="api_keys")
    op.drop_column("api_keys", "revoked_at")
    op.drop_column("api_keys", "client_id")
    op.drop_table("integration_clients")
