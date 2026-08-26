"""Document M005 organization administration permission catalog additions."""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0004_m005_org_permissions"
down_revision = "0003_rbac_authorization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    permissions = (
        ("merchants:create", "Create merchants."),
        ("merchants:delete", "Deactivate merchants."),
        ("branches:create", "Create branches."),
        ("branches:update", "Update branches."),
        ("branches:delete", "Deactivate branches."),
    )
    for code, description in permissions:
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, description, created_at, updated_at) "
                "VALUES (:id, :code, :description, now(), now()) "
                "ON CONFLICT (code) DO NOTHING"
            ).bindparams(id=uuid.uuid4(), code=code, description=description)
        )
    for role_code, permission_codes in (
        (
            "platform_admin",
            (
                "merchants:create",
                "merchants:delete",
                "branches:create",
                "branches:update",
                "branches:delete",
            ),
        ),
        ("merchant_owner", ("branches:create", "branches:update", "branches:delete")),
    ):
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
            "(SELECT id FROM permissions WHERE code IN "
            "('merchants:create', 'merchants:delete', 'branches:create', "
            "'branches:update', 'branches:delete'))"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM permissions WHERE code IN "
            "('merchants:create', 'merchants:delete', 'branches:create', "
            "'branches:update', 'branches:delete')"
        )
    )
