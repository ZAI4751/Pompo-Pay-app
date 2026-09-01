"""Provider management domain, health state, and attempt failure classification."""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0008_provider_management"
down_revision = "0007_operational_tills_providers"
branch_labels = None
depends_on = None

PERMISSIONS = (("providers:create", "Register payment provider catalog entries."),)

ROLE_GRANTS = (("platform_admin", ("providers:create",)),)


def upgrade() -> None:
    op.add_column(
        "payment_providers",
        sa.Column(
            "provider_type",
            sa.String(length=32),
            nullable=False,
            server_default="simulated",
        ),
    )
    op.add_column(
        "payment_providers",
        sa.Column(
            "health_state",
            sa.String(length=32),
            nullable=False,
            server_default="disabled",
        ),
    )
    op.add_column(
        "payment_providers",
        sa.Column("config_refs", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_payment_providers_health_state", "payment_providers", ["health_state"])

    op.execute(
        sa.text(
            "UPDATE payment_providers SET provider_type = 'mobile_money' "
            "WHERE code IN ('airtel_money', 'tnm_mpamba')"
        )
    )
    op.execute(
        sa.text(
            "UPDATE payment_providers SET provider_type = 'bank' "
            "WHERE code IN ('national_bank', 'fdh_bank', 'standard_bank')"
        )
    )
    op.execute(
        sa.text(
            "UPDATE payment_providers SET health_state = 'unavailable' "
            "WHERE code IN ('airtel_money', 'tnm_mpamba', 'national_bank', "
            "'fdh_bank', 'standard_bank')"
        )
    )
    op.execute(
        sa.text(
            "UPDATE payment_providers SET health_state = 'active' "
            "WHERE is_active IS TRUE AND code LIKE 'simulated%'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE payment_providers SET health_state = 'disabled' "
            "WHERE is_active IS FALSE AND code LIKE 'simulated%'"
        )
    )

    op.add_column("payment_attempts", sa.Column("failure_code", sa.String(length=64), nullable=True))
    op.add_column("payment_attempts", sa.Column("retryable", sa.Boolean(), nullable=True))

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
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = 'providers:create')"
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code = 'providers:create'"))
    op.drop_column("payment_attempts", "retryable")
    op.drop_column("payment_attempts", "failure_code")
    op.drop_index("ix_payment_providers_health_state", table_name="payment_providers")
    op.drop_column("payment_providers", "config_refs")
    op.drop_column("payment_providers", "health_state")
    op.drop_column("payment_providers", "provider_type")
