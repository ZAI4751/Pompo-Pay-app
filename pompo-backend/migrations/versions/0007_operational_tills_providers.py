"""Till administration, provider catalog metadata, and related RBAC grants."""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0007_operational_tills_providers"
down_revision = "0006_m007_attempt_metadata"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("tills:read", "View tills."),
    ("tills:create", "Create tills."),
    ("tills:update", "Update tills."),
    ("tills:delete", "Deactivate tills."),
    ("providers:read", "View the payment provider catalog."),
    ("providers:update", "Enable, disable, or prioritize payment providers."),
)

ROLE_GRANTS = (
    (
        "platform_admin",
        (
            "tills:read",
            "tills:create",
            "tills:update",
            "tills:delete",
            "providers:read",
            "providers:update",
        ),
    ),
    (
        "merchant_owner",
        (
            "tills:read",
            "tills:create",
            "tills:update",
            "tills:delete",
            "providers:read",
        ),
    ),
    ("branch_manager", ("tills:read", "tills:create", "tills:update")),
)


def upgrade() -> None:
    op.add_column(
        "payment_providers",
        sa.Column("environment", sa.String(length=32), nullable=False, server_default="sandbox"),
    )
    op.add_column(
        "payment_providers",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
    )
    op.add_column(
        "payment_providers",
        sa.Column(
            "supported_currencies",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[\"MWK\"]'"),
        ),
    )
    op.add_column(
        "payment_providers",
        sa.Column(
            "supported_payment_methods",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[\"mobile_money\"]'"),
        ),
    )
    op.add_column(
        "payment_providers",
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_payment_providers_priority", "payment_providers", ["priority"])

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
            "DELETE FROM role_permissions WHERE permission_id IN "
            f"(SELECT id FROM permissions WHERE code IN ({permission_codes}))"
        )
    )
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ({permission_codes})"))
    op.drop_index("ix_payment_providers_priority", table_name="payment_providers")
    op.drop_column("payment_providers", "capabilities")
    op.drop_column("payment_providers", "supported_payment_methods")
    op.drop_column("payment_providers", "supported_currencies")
    op.drop_column("payment_providers", "priority")
    op.drop_column("payment_providers", "environment")
