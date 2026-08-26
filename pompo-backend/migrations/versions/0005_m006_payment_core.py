"""Add M006 payment-core transaction metadata and idempotency."""

import uuid

import sqlalchemy as sa
from alembic import op

from app.models.base import GUID

revision = "0005_m006_payment_core"
down_revision = "0004_m005_org_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("provider_id", GUID(), nullable=True))
    op.add_column("transactions", sa.Column("idempotency_key", sa.String(128), nullable=True))
    op.add_column("transactions", sa.Column("request_fingerprint", sa.String(64), nullable=True))
    op.add_column("transactions", sa.Column("payment_method", sa.String(32), nullable=True))
    op.add_column("transactions", sa.Column("customer_phone", sa.String(32), nullable=True))
    op.add_column("transactions", sa.Column("failure_reason", sa.String(500), nullable=True))
    op.create_index("ix_transactions_provider_id", "transactions", ["provider_id"])
    op.create_foreign_key(
        "fk_transactions_provider_id",
        "transactions",
        "payment_providers",
        ["provider_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute(
        sa.text(
            "UPDATE transactions SET idempotency_key = 'legacy-' || id, "
            "request_fingerprint = md5(id::text), payment_method = 'unknown' "
            "WHERE idempotency_key IS NULL"
        )
    )
    op.alter_column("transactions", "idempotency_key", nullable=False)
    op.alter_column("transactions", "request_fingerprint", nullable=False)
    op.alter_column("transactions", "payment_method", nullable=False)
    op.create_unique_constraint(
        "uq_transaction_merchant_idempotency", "transactions", ["merchant_id", "idempotency_key"]
    )
    op.execute(
        sa.text(
            "INSERT INTO permissions (id, code, description, created_at, updated_at) "
            "VALUES (:id, 'transactions:cancel', 'Cancel transactions.', now(), now()) "
            "ON CONFLICT (code) DO NOTHING"
        ).bindparams(id=uuid.uuid4())
    )
    for role_code in ("platform_admin", "merchant_owner", "branch_manager"):
        op.execute(
            sa.text(
                "INSERT INTO role_permissions (id, role_id, permission_id, granted_at) "
                "SELECT :id, r.id, p.id, now() FROM roles r CROSS JOIN permissions p "
                "WHERE r.code = :role_code AND p.code = 'transactions:cancel' "
                "ON CONFLICT (role_id, permission_id) DO NOTHING"
            ).bindparams(id=uuid.uuid4(), role_code=role_code)
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = 'transactions:cancel')"
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code = 'transactions:cancel'"))
    op.drop_constraint("uq_transaction_merchant_idempotency", "transactions", type_="unique")
    op.drop_constraint("fk_transactions_provider_id", "transactions", type_="foreignkey")
    op.drop_index("ix_transactions_provider_id", table_name="transactions")
    for column in (
        "failure_reason",
        "customer_phone",
        "payment_method",
        "request_fingerprint",
        "idempotency_key",
        "provider_id",
    ):
        op.drop_column("transactions", column)
