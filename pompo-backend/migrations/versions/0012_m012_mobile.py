"""M012 mobile contract — customer system role.

Revision ID: 0012_m012_mobile
Revises: 0011_m011_settlement
Create Date: 2026-09-02

Permissions used by the customer role already exist from M006.
This revision inserts the system role and its grants for existing
deployments that were seeded before the catalog included ``customer``.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0012_m012_mobile"
down_revision = "0011_m011_settlement"
branch_labels = None
depends_on = None

CUSTOMER_PERMISSIONS = (
    "transactions:read",
    "transactions:create",
    "transactions:update",
    "transactions:cancel",
)


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO roles "
            "(id, code, name, description, is_system_role, is_active, created_at, updated_at) "
            "VALUES (:id, :code, :name, :description, true, true, now(), now()) "
            "ON CONFLICT (code) DO NOTHING"
        ).bindparams(
            id=uuid.uuid4(),
            code="customer",
            name="Customer",
            description="Pay from a scanned QR and view own payment history.",
        )
    )
    for permission_code in CUSTOMER_PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO role_permissions (id, role_id, permission_id, granted_at) "
                "SELECT :assignment_id, r.id, p.id, now() "
                "FROM roles r CROSS JOIN permissions p "
                "WHERE r.code = 'customer' AND p.code = :permission_code "
                "ON CONFLICT (role_id, permission_id) DO NOTHING"
            ).bindparams(
                assignment_id=uuid.uuid4(),
                permission_code=permission_code,
            )
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE role_id IN "
            "(SELECT id FROM roles WHERE code = 'customer')"
        )
    )
    op.execute(sa.text("DELETE FROM roles WHERE code = 'customer' AND is_system_role IS TRUE"))
