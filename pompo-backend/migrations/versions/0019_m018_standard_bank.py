"""M018 Standard Bank Malawi catalog metadata.

Revision ID: 0019_m018_standard_bank
Revises: 0018_m017_tnm_mpamba
Create Date: 2026-09-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_m018_standard_bank"
down_revision = "0018_m017_tnm_mpamba"
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
                display_name = 'Standard Bank Malawi',
                is_simulated = false,
                is_active = false,
                health_state = 'disabled',
                supported_payment_methods = CAST(:methods AS json),
                capabilities = CAST(:capabilities AS json),
                config_refs = CAST(
                    '{"base_url_env": "PROVIDER_STANDARD_BANK_BASE_URL", '
                    '"timeout_env": "PROVIDER_STANDARD_BANK_TIMEOUT_SECONDS", '
                    '"client_id_env": "PROVIDER_STANDARD_BANK_CLIENT_ID", '
                    '"credential_env": "PROVIDER_STANDARD_BANK_CREDENTIAL_REF", '
                    '"webhook_secret_env": "PROVIDER_STANDARD_BANK_WEBHOOK_SECRET_REF"}'
                    AS json
                )
            WHERE code = 'standard_bank'
            """
        ).bindparams(capabilities=_CAPABILITIES, methods='["card"]')
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE payment_providers
            SET
                display_name = 'Standard Bank (live contract not implemented)',
                is_simulated = true,
                is_active = false,
                health_state = 'unavailable',
                supported_payment_methods = CAST(:methods AS json)
            WHERE code = 'standard_bank'
            """
        ).bindparams(methods='["bank"]')
    )
