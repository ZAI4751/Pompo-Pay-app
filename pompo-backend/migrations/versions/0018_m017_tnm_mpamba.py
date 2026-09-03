"""M017 TNM Mpamba Malawi catalog metadata.

Revision ID: 0018_m017_tnm_mpamba
Revises: 0017_payment_instruments
Create Date: 2026-09-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_m017_tnm_mpamba"
down_revision = "0017_payment_instruments"
branch_labels = None
depends_on = None

_CAPABILITIES = (
    '{"supports_push_payment": false, "supports_status_query": false, '
    '"supports_cancel": false, "supports_refund": false, '
    '"supports_webhooks": false, "supports_qr": false, '
    '"supports_payment_instruments": false, "supports_instrument_enroll": false, '
    '"supports_instrument_charge": false, "supports_instrument_verify": false, '
    '"supports_instrument_remove": false}'
)


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE payment_providers
            SET
                display_name = 'TNM Mpamba Malawi',
                is_simulated = false,
                is_active = false,
                health_state = 'disabled',
                capabilities = CAST(:capabilities AS json),
                config_refs = CAST(
                    '{"base_url_env": "PROVIDER_TNM_MPAMBA_BASE_URL", '
                    '"timeout_env": "PROVIDER_TNM_MPAMBA_TIMEOUT_SECONDS", '
                    '"client_id_env": "PROVIDER_TNM_MPAMBA_CLIENT_ID", '
                    '"credential_env": "PROVIDER_TNM_MPAMBA_CREDENTIAL_REF", '
                    '"webhook_secret_env": "PROVIDER_TNM_MPAMBA_WEBHOOK_SECRET_REF"}'
                    AS json
                )
            WHERE code = 'tnm_mpamba'
            """
        ).bindparams(capabilities=_CAPABILITIES)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE payment_providers
            SET
                display_name = 'TNM Mpamba (live contract not implemented)',
                is_simulated = true,
                is_active = false,
                health_state = 'unavailable'
            WHERE code = 'tnm_mpamba'
            """
        )
    )
