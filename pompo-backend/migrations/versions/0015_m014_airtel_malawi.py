"""M014 Airtel Money Malawi catalog metadata.

Revision ID: 0015_m014_airtel_malawi
Revises: 0014_m013_webhook_endpoints
Create Date: 2026-09-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_m014_airtel_malawi"
down_revision = "0014_m013_webhook_endpoints"
branch_labels = None
depends_on = None

_CAPABILITIES = (
    '{"supports_push_payment": true, "supports_status_query": true, '
    '"supports_cancel": false, "supports_refund": false, '
    '"supports_webhooks": true, "supports_qr": false}'
)


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE payment_providers
            SET
                display_name = 'Airtel Money Malawi',
                is_simulated = false,
                is_active = false,
                health_state = 'disabled',
                capabilities = CAST(:capabilities AS json),
                config_refs = CAST(
                    '{"base_url_env": "PROVIDER_AIRTEL_MONEY_BASE_URL", '
                    '"timeout_env": "PROVIDER_AIRTEL_MONEY_TIMEOUT_SECONDS", '
                    '"client_id_env": "PROVIDER_AIRTEL_MONEY_CLIENT_ID", '
                    '"credential_env": "PROVIDER_AIRTEL_MONEY_CREDENTIAL_REF", '
                    '"webhook_secret_env": "PROVIDER_AIRTEL_MONEY_WEBHOOK_SECRET_REF"}'
                    AS json
                )
            WHERE code = 'airtel_money'
            """
        ).bindparams(capabilities=_CAPABILITIES)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE payment_providers
            SET
                display_name = 'Airtel Money (live contract not implemented)',
                is_simulated = true,
                is_active = false,
                health_state = 'unavailable'
            WHERE code = 'airtel_money'
            """
        )
    )
