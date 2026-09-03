"""TNM Mpamba Malawi adapter.

No TNM-owned HTTP contract is in the repository. This adapter encapsulates
TNM-specific *absence* of a live rail so PaymentService, webhooks, and
instruments fail closed without inventing URLs, payloads, or signatures.

See docs/providers/tnm-mpamba-malawi.md. This module never logs secrets.
"""

from __future__ import annotations

from decimal import Decimal

from app.core.logging import get_logger
from app.payments.credentials import ProviderCredentials, resolve_provider_credentials
from app.payments.providers import (
    ProviderCapabilities,
    ProviderHealth,
    ProviderPaymentRequest,
    ProviderResult,
    ProviderUnavailable,
    UnsupportedProviderOperation,
    require_capability,
)
from app.payments.webhooks import NormalizedWebhookEvent, WebhookVerificationResult

logger = get_logger(__name__)

PROVIDER_CODE = "tnm_mpamba"
COUNTRY = "MW"
CURRENCY = "MWK"
CONTRACT_SOURCE = "docs/providers/tnm-mpamba-malawi.md"
CONTRACT_MISSING = (
    "TNM Mpamba live HTTP contract is not in the repository. "
    "See docs/providers/tnm-mpamba-malawi.md."
)

TNM_CAPABILITIES = ProviderCapabilities(
    supports_push_payment=False,
    supports_status_query=False,
    supports_cancel=False,
    supports_refund=False,
    supports_webhooks=False,
    supports_qr=False,
    supports_payment_instruments=False,
    supports_instrument_enroll=False,
    supports_instrument_charge=False,
    supports_instrument_verify=False,
    supports_instrument_remove=False,
)


class TnmMpambaMalawiAdapter:
    """Named TNM rail. Never mutates transactions. Never calls invented hosts."""

    code = PROVIDER_CODE
    capabilities = TNM_CAPABILITIES

    def __init__(self, *, catalog_environment: str = "sandbox") -> None:
        self._catalog_environment = catalog_environment

    @property
    def live_contract_ready(self) -> bool:
        return False

    async def initiate_payment(self, request: ProviderPaymentRequest) -> ProviderResult:
        logger.info(
            "tnm_payment_blocked",
            provider=PROVIDER_CODE,
            transaction_reference=request.reference,
            outcome="unavailable",
            failure_category="unavailable",
            contract_source=CONTRACT_SOURCE,
        )
        require_capability(self, "initiate")
        raise ProviderUnavailable(CONTRACT_MISSING)

    async def get_payment_status(self, provider_reference: str) -> ProviderResult:
        require_capability(self, "status_query")
        logger.info(
            "tnm_status_blocked",
            provider=PROVIDER_CODE,
            provider_reference=provider_reference,
            failure_category="unavailable",
            contract_source=CONTRACT_SOURCE,
        )
        raise ProviderUnavailable(CONTRACT_MISSING)

    async def cancel_payment(self, provider_reference: str) -> ProviderResult:
        raise UnsupportedProviderOperation("cancel")

    async def refund_payment(self, provider_reference: str, amount: Decimal) -> ProviderResult:
        del amount
        raise UnsupportedProviderOperation("refund")

    async def health_check(self) -> ProviderHealth:
        try:
            credentials = self._credentials()
        except Exception as exc:
            return ProviderHealth(
                configured=False,
                contract_ready=False,
                supports_health_check=False,
                reachable=None,
                message=str(exc),
            )
        env_present = bool(credentials.base_url or credentials.secret_configured or credentials.client_id)
        return ProviderHealth(
            configured=env_present,
            contract_ready=False,
            supports_health_check=False,
            reachable=None,
            message=CONTRACT_MISSING,
        )

    async def verify_webhook(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
        credentials: ProviderCredentials,
    ) -> WebhookVerificationResult:
        del headers, body, credentials
        logger.warning(
            "tnm_webhook_rejected",
            provider=PROVIDER_CODE,
            reason="callback_contract_missing",
        )
        return WebhookVerificationResult(
            False,
            failure_reason="TNM Mpamba callback contract is not documented",
        )

    async def parse_webhook(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> NormalizedWebhookEvent:
        del headers, body
        raise ValueError("TNM Mpamba callback payload is not documented")

    def _credentials(self) -> ProviderCredentials:
        return resolve_provider_credentials(
            PROVIDER_CODE,
            catalog_environment=self._catalog_environment,
        )
