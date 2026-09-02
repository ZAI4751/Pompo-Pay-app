"""M011 settlement and reconciliation financial control layer."""

import uuid

import sqlalchemy as sa
from alembic import op

from app.models.base import GUID

revision = "0011_m011_settlement"
down_revision = "0011_m010_webhook_public_id"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("settlements:read", "View settlement batches and records."),
    ("settlements:create", "Ingest provider settlement files."),
    ("reconciliation:read", "View reconciliation records and runs."),
    ("reconciliation:update", "Record reconciliation resolution."),
)

ROLE_GRANTS = (
    (
        "platform_admin",
        (
            "settlements:read",
            "settlements:create",
            "reconciliation:read",
            "reconciliation:update",
        ),
    ),
    ("merchant_owner", ("settlements:read", "reconciliation:read")),
)


def upgrade() -> None:
    op.create_table(
        "pricing_schedules",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("scope_key", sa.String(160), nullable=False),
        sa.Column("provider_id", GUID(), nullable=True),
        sa.Column("merchant_id", GUID(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MWK"),
        sa.Column("pompo_fee_type", sa.String(16), nullable=False, server_default="zero"),
        sa.Column("pompo_fixed_amount", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("pompo_percentage_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pompo_min_fee", sa.Numeric(18, 2), nullable=True),
        sa.Column("pompo_max_fee", sa.Numeric(18, 2), nullable=True),
        sa.Column("provider_cost_type", sa.String(16), nullable=False, server_default="zero"),
        sa.Column("provider_cost_fixed", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("provider_cost_percentage_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_key", name="uq_pricing_schedule_scope"),
        sa.ForeignKeyConstraint(["provider_id"], ["payment_providers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("pompo_fixed_amount >= 0", name="ck_pricing_pompo_fixed_nonneg"),
        sa.CheckConstraint("provider_cost_fixed >= 0", name="ck_pricing_provider_fixed_nonneg"),
        sa.CheckConstraint("pompo_percentage_bps >= 0", name="ck_pricing_pompo_bps_nonneg"),
        sa.CheckConstraint("provider_cost_percentage_bps >= 0", name="ck_pricing_provider_bps_nonneg"),
    )
    op.create_index("ix_pricing_schedules_provider_id", "pricing_schedules", ["provider_id"])
    op.create_index("ix_pricing_schedules_merchant_id", "pricing_schedules", ["merchant_id"])

    op.create_table(
        "settlement_batches",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("public_identifier", sa.String(40), nullable=False),
        sa.Column("provider_id", GUID(), nullable=False),
        sa.Column("external_batch_reference", sa.String(128), nullable=False),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MWK"),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_gross", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_provider_fees", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_pompo_fees", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_merchant_net", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(32), nullable=False, server_default="received"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_identifier"),
        sa.UniqueConstraint(
            "provider_id",
            "external_batch_reference",
            name="uq_settlement_batch_provider_reference",
        ),
        sa.ForeignKeyConstraint(["provider_id"], ["payment_providers.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("record_count >= 0", name="ck_settlement_batch_count_nonneg"),
        sa.CheckConstraint("total_gross >= 0", name="ck_settlement_batch_gross_nonneg"),
        sa.CheckConstraint(
            "total_provider_fees >= 0", name="ck_settlement_batch_provider_fees_nonneg"
        ),
        sa.CheckConstraint("total_pompo_fees >= 0", name="ck_settlement_batch_pompo_fees_nonneg"),
    )
    op.create_index("ix_settlement_batches_provider_id", "settlement_batches", ["provider_id"])
    op.create_index("ix_settlement_batches_settlement_date", "settlement_batches", ["settlement_date"])
    op.create_index("ix_settlement_batches_status", "settlement_batches", ["status"])

    op.create_table(
        "settlements",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("public_identifier", sa.String(40), nullable=False),
        sa.Column("batch_id", GUID(), nullable=False),
        sa.Column("provider_id", GUID(), nullable=False),
        sa.Column("provider_settlement_reference", sa.String(128), nullable=False),
        sa.Column("transaction_id", GUID(), nullable=True),
        sa.Column("payment_attempt_id", GUID(), nullable=True),
        sa.Column("merchant_id", GUID(), nullable=True),
        sa.Column("branch_id", GUID(), nullable=True),
        sa.Column("payment_reference", sa.String(64), nullable=True),
        sa.Column("provider_transaction_reference", sa.String(128), nullable=True),
        sa.Column("gross_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("provider_fee", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("pompo_fee", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("merchant_net", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MWK"),
        sa.Column("status", sa.String(32), nullable=False, server_default="received"),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_identifier"),
        sa.UniqueConstraint(
            "provider_id",
            "provider_settlement_reference",
            name="uq_settlement_provider_reference",
        ),
        sa.ForeignKeyConstraint(["batch_id"], ["settlement_batches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["provider_id"], ["payment_providers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payment_attempt_id"], ["payment_attempts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("gross_amount >= 0", name="ck_settlement_gross_nonneg"),
        sa.CheckConstraint("provider_fee >= 0", name="ck_settlement_provider_fee_nonneg"),
        sa.CheckConstraint("pompo_fee >= 0", name="ck_settlement_pompo_fee_nonneg"),
        sa.CheckConstraint(
            "merchant_net = gross_amount - provider_fee - pompo_fee",
            name="ck_settlement_net_identity",
        ),
    )
    op.create_index("ix_settlements_batch_id", "settlements", ["batch_id"])
    op.create_index("ix_settlements_provider_id", "settlements", ["provider_id"])
    op.create_index("ix_settlements_transaction_id", "settlements", ["transaction_id"])
    op.create_index("ix_settlements_payment_attempt_id", "settlements", ["payment_attempt_id"])
    op.create_index("ix_settlements_merchant_id", "settlements", ["merchant_id"])
    op.create_index("ix_settlements_branch_id", "settlements", ["branch_id"])
    op.create_index("ix_settlements_status", "settlements", ["status"])
    op.create_index("ix_settlements_payment_reference", "settlements", ["payment_reference"])
    op.create_index("ix_settlements_provider_txn_ref", "settlements", ["provider_transaction_reference"])
    op.create_index("ix_settlements_settlement_date", "settlements", ["settlement_date"])

    op.create_table(
        "reconciliation_runs",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("public_identifier", sa.String(40), nullable=False),
        sa.Column("provider_id", GUID(), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("records_examined", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unmatched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discrepancy_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("partial_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("investigation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_expected", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_actual", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_variance", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_identifier"),
        sa.ForeignKeyConstraint(["provider_id"], ["payment_providers.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_reconciliation_runs_provider_id", "reconciliation_runs", ["provider_id"])
    op.create_index("ix_reconciliation_runs_status", "reconciliation_runs", ["status"])

    op.create_table(
        "reconciliation_records",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("public_identifier", sa.String(40), nullable=False),
        sa.Column("run_id", GUID(), nullable=True),
        sa.Column("settlement_id", GUID(), nullable=True),
        sa.Column("transaction_id", GUID(), nullable=True),
        sa.Column("payment_attempt_id", GUID(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("mismatch_category", sa.String(64), nullable=True),
        sa.Column("expected_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("actual_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("variance", sa.Numeric(18, 2), nullable=True),
        sa.Column("expected_provider_fee", sa.Numeric(18, 2), nullable=True),
        sa.Column("actual_provider_fee", sa.Numeric(18, 2), nullable=True),
        sa.Column("expected_pompo_fee", sa.Numeric(18, 2), nullable=True),
        sa.Column("actual_pompo_fee", sa.Numeric(18, 2), nullable=True),
        sa.Column("expected_currency", sa.String(3), nullable=True),
        sa.Column("actual_currency", sa.String(3), nullable=True),
        sa.Column("pompo_reference", sa.String(64), nullable=True),
        sa.Column("provider_reference", sa.String(128), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", GUID(), nullable=True),
        sa.Column("resolution_note", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_identifier"),
        sa.UniqueConstraint("settlement_id", name="uq_recon_settlement"),
        sa.ForeignKeyConstraint(
            ["run_id"], ["reconciliation_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["settlement_id"], ["settlements.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["payment_attempt_id"], ["payment_attempts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_reconciliation_records_run_id", "reconciliation_records", ["run_id"])
    op.create_index(
        "ix_reconciliation_records_transaction_id", "reconciliation_records", ["transaction_id"]
    )
    op.create_index("ix_recon_status", "reconciliation_records", ["status"])
    op.create_index("ix_recon_category", "reconciliation_records", ["mismatch_category"])
    op.create_index(
        "uq_recon_missing_settlement_txn",
        "reconciliation_records",
        ["transaction_id"],
        unique=True,
        postgresql_where=sa.text(
            "settlement_id IS NULL AND mismatch_category = 'missing_settlement'"
        ),
        sqlite_where=sa.text(
            "settlement_id IS NULL AND mismatch_category = 'missing_settlement'"
        ),
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

    op.drop_index("uq_recon_missing_settlement_txn", table_name="reconciliation_records")
    op.drop_index("ix_recon_category", table_name="reconciliation_records")
    op.drop_index("ix_recon_status", table_name="reconciliation_records")
    op.drop_index("ix_reconciliation_records_transaction_id", table_name="reconciliation_records")
    op.drop_index("ix_reconciliation_records_run_id", table_name="reconciliation_records")
    op.drop_table("reconciliation_records")

    op.drop_index("ix_reconciliation_runs_status", table_name="reconciliation_runs")
    op.drop_index("ix_reconciliation_runs_provider_id", table_name="reconciliation_runs")
    op.drop_table("reconciliation_runs")

    op.drop_index("ix_settlements_settlement_date", table_name="settlements")
    op.drop_index("ix_settlements_provider_txn_ref", table_name="settlements")
    op.drop_index("ix_settlements_payment_reference", table_name="settlements")
    op.drop_index("ix_settlements_status", table_name="settlements")
    op.drop_index("ix_settlements_branch_id", table_name="settlements")
    op.drop_index("ix_settlements_merchant_id", table_name="settlements")
    op.drop_index("ix_settlements_payment_attempt_id", table_name="settlements")
    op.drop_index("ix_settlements_transaction_id", table_name="settlements")
    op.drop_index("ix_settlements_provider_id", table_name="settlements")
    op.drop_index("ix_settlements_batch_id", table_name="settlements")
    op.drop_table("settlements")

    op.drop_index("ix_settlement_batches_status", table_name="settlement_batches")
    op.drop_index("ix_settlement_batches_settlement_date", table_name="settlement_batches")
    op.drop_index("ix_settlement_batches_provider_id", table_name="settlement_batches")
    op.drop_table("settlement_batches")

    op.drop_index("ix_pricing_schedules_merchant_id", table_name="pricing_schedules")
    op.drop_index("ix_pricing_schedules_provider_id", table_name="pricing_schedules")
    op.drop_table("pricing_schedules")
