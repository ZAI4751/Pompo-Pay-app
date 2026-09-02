"""M013 partner webhook destinations — multiple endpoints per client.

Revision ID: 0014_m013_webhook_endpoints
Revises: 0013_m013_integrations
Create Date: 2026-09-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.models.base import GUID

revision = "0014_m013_webhook_endpoints"
down_revision = "0013_m013_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_webhook_endpoints",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("client_id", GUID(), nullable=False),
        sa.Column("destination_url", sa.String(1000), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_category", sa.String(32), nullable=True),
        sa.Column("last_response_status_code", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["integration_clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "client_id",
            "destination_url",
            name="uq_integration_webhook_endpoint_url",
        ),
    )
    op.create_index(
        "ix_integration_webhook_endpoints_client_id",
        "integration_webhook_endpoints",
        ["client_id"],
    )

    op.add_column(
        "outbound_webhook_deliveries",
        sa.Column("endpoint_id", GUID(), nullable=True),
    )
    op.create_index(
        "ix_outbound_webhook_deliveries_endpoint_id",
        "outbound_webhook_deliveries",
        ["endpoint_id"],
    )
    op.create_foreign_key(
        "fk_outbound_webhook_deliveries_endpoint_id",
        "outbound_webhook_deliveries",
        "integration_webhook_endpoints",
        ["endpoint_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_outbound_webhook_deliveries_public_event_id",
        "outbound_webhook_deliveries",
        ["public_event_id"],
    )

    op.drop_constraint("uq_outbound_webhook_event_id", "outbound_webhook_deliveries", type_="unique")
    op.drop_constraint(
        "uq_outbound_webhook_client_txn_type", "outbound_webhook_deliveries", type_="unique"
    )
    op.create_unique_constraint(
        "uq_outbound_webhook_client_txn_type_dest",
        "outbound_webhook_deliveries",
        ["client_id", "transaction_id", "event_type", "destination_url"],
    )

    op.execute(
        sa.text(
            "INSERT INTO integration_webhook_endpoints "
            "(id, created_at, updated_at, client_id, destination_url, is_active) "
            "SELECT gen_random_uuid(), now(), now(), id, webhook_url, true "
            "FROM integration_clients "
            "WHERE webhook_url IS NOT NULL AND btrim(webhook_url) <> ''"
        )
    )
    op.execute(
        sa.text(
            "UPDATE outbound_webhook_deliveries d "
            "SET endpoint_id = e.id "
            "FROM integration_webhook_endpoints e "
            "WHERE e.client_id = d.client_id AND e.destination_url = d.destination_url"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM outbound_webhook_deliveries a "
            "USING outbound_webhook_deliveries b "
            "WHERE a.ctid < b.ctid "
            "AND a.client_id = b.client_id "
            "AND a.transaction_id = b.transaction_id "
            "AND a.event_type = b.event_type"
        )
    )
    op.drop_constraint(
        "uq_outbound_webhook_client_txn_type_dest",
        "outbound_webhook_deliveries",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_outbound_webhook_event_id",
        "outbound_webhook_deliveries",
        ["public_event_id"],
    )
    op.create_unique_constraint(
        "uq_outbound_webhook_client_txn_type",
        "outbound_webhook_deliveries",
        ["client_id", "transaction_id", "event_type"],
    )
    op.drop_constraint(
        "fk_outbound_webhook_deliveries_endpoint_id",
        "outbound_webhook_deliveries",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_outbound_webhook_deliveries_public_event_id",
        table_name="outbound_webhook_deliveries",
    )
    op.drop_index(
        "ix_outbound_webhook_deliveries_endpoint_id",
        table_name="outbound_webhook_deliveries",
    )
    op.drop_column("outbound_webhook_deliveries", "endpoint_id")
    op.drop_index(
        "ix_integration_webhook_endpoints_client_id",
        table_name="integration_webhook_endpoints",
    )
    op.drop_table("integration_webhook_endpoints")
