"""M009 QR payments — expand qr_codes for static/dynamic merchant QR."""

import uuid

import sqlalchemy as sa
from alembic import op

from app.models.base import GUID

revision = "0009_m009_qr_payments"
down_revision = "0008_provider_management"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("qr:read", "View merchant QR codes."),
    ("qr:create", "Create static and dynamic QR codes."),
    ("qr:revoke", "Revoke merchant QR codes."),
)

ROLE_GRANTS = (
    ("platform_admin", ("qr:read", "qr:create", "qr:revoke")),
    ("merchant_owner", ("qr:read", "qr:create", "qr:revoke")),
    ("branch_manager", ("qr:read", "qr:create", "qr:revoke")),
    ("cashier", ("qr:read", "qr:create")),
)


def upgrade() -> None:
    op.add_column("qr_codes", sa.Column("public_identifier", sa.String(32), nullable=True))
    op.add_column("qr_codes", sa.Column("merchant_id", GUID(), nullable=True))
    op.add_column("qr_codes", sa.Column("branch_id", GUID(), nullable=True))
    op.add_column("qr_codes", sa.Column("till_id", GUID(), nullable=True))
    op.add_column(
        "qr_codes",
        sa.Column("qr_type", sa.String(16), nullable=True),
    )
    op.add_column(
        "qr_codes",
        sa.Column("status", sa.String(16), nullable=True, server_default="active"),
    )
    op.add_column(
        "qr_codes",
        sa.Column("version", sa.Integer(), nullable=True, server_default="1"),
    )
    op.add_column("qr_codes", sa.Column("payment_reference", sa.String(64), nullable=True))
    op.add_column("qr_codes", sa.Column("amount", sa.Numeric(18, 2), nullable=True))
    op.add_column(
        "qr_codes",
        sa.Column("currency", sa.String(3), nullable=True, server_default="MWK"),
    )
    op.add_column("qr_codes", sa.Column("payload_metadata", sa.JSON(), nullable=True))
    op.add_column("qr_codes", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("qr_codes", "transaction_id", existing_type=GUID(), nullable=True)
    op.alter_column("qr_codes", "expires_at", existing_type=sa.DateTime(timezone=True), nullable=True)

    op.execute(
        sa.text(
            "UPDATE qr_codes SET public_identifier = 'LEGACY-' || substr(id::text, 1, 8), "
            "qr_type = 'dynamic', status = CASE WHEN is_used THEN 'consumed' ELSE 'active' END, "
            "version = 1, currency = 'MWK' "
            "WHERE public_identifier IS NULL"
        )
    )

    op.execute(
        sa.text(
            "UPDATE qr_codes q SET merchant_id = t.merchant_id, branch_id = t.branch_id, "
            "till_id = t.till_id, payment_reference = t.reference, amount = t.amount "
            "FROM transactions t WHERE q.transaction_id = t.id AND q.merchant_id IS NULL"
        )
    )

    op.alter_column("qr_codes", "public_identifier", nullable=False)
    op.alter_column("qr_codes", "qr_type", nullable=False)
    op.alter_column("qr_codes", "status", nullable=False)
    op.alter_column("qr_codes", "version", nullable=False)
    op.alter_column("qr_codes", "currency", nullable=False)

    op.create_foreign_key(
        "fk_qr_codes_merchant_id",
        "qr_codes",
        "merchants",
        ["merchant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_qr_codes_branch_id",
        "qr_codes",
        "branches",
        ["branch_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_qr_codes_till_id",
        "qr_codes",
        "tills",
        ["till_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_qr_codes_merchant_id", "qr_codes", ["merchant_id"])
    op.create_index("ix_qr_codes_branch_id", "qr_codes", ["branch_id"])
    op.create_index("ix_qr_codes_till_id", "qr_codes", ["till_id"])
    op.create_index("ix_qr_codes_qr_type", "qr_codes", ["qr_type"])
    op.create_index("ix_qr_codes_status", "qr_codes", ["status"])
    op.create_index("ix_qr_codes_payment_reference", "qr_codes", ["payment_reference"])
    op.create_unique_constraint("uq_qr_codes_public_identifier", "qr_codes", ["public_identifier"])

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

    op.drop_constraint("uq_qr_codes_public_identifier", "qr_codes", type_="unique")
    op.drop_index("ix_qr_codes_payment_reference", table_name="qr_codes")
    op.drop_index("ix_qr_codes_status", table_name="qr_codes")
    op.drop_index("ix_qr_codes_qr_type", table_name="qr_codes")
    op.drop_index("ix_qr_codes_till_id", table_name="qr_codes")
    op.drop_index("ix_qr_codes_branch_id", table_name="qr_codes")
    op.drop_index("ix_qr_codes_merchant_id", table_name="qr_codes")
    op.drop_constraint("fk_qr_codes_till_id", "qr_codes", type_="foreignkey")
    op.drop_constraint("fk_qr_codes_branch_id", "qr_codes", type_="foreignkey")
    op.drop_constraint("fk_qr_codes_merchant_id", "qr_codes", type_="foreignkey")

    for column in (
        "revoked_at",
        "payload_metadata",
        "currency",
        "amount",
        "payment_reference",
        "version",
        "status",
        "qr_type",
        "till_id",
        "branch_id",
        "merchant_id",
        "public_identifier",
    ):
        op.drop_column("qr_codes", column)

    op.alter_column("qr_codes", "transaction_id", existing_type=GUID(), nullable=False)
    op.alter_column("qr_codes", "expires_at", existing_type=sa.DateTime(timezone=True), nullable=False)
