"""Structured live-rail adapter boundaries.

These adapters implement the provider contract so the payment core stays
provider-neutral. They do not invent Airtel, TNM, or bank HTTP APIs. Calls
fail as unavailable until a real contract is implemented in a later milestone.
TNM Mpamba uses `TnmMpambaMalawiAdapter` in `tnm_mpamba.py` instead of this
generic stub.
"""

from __future__ import annotations

from decimal import Decimal

from app.payments.providers import (
    ProviderCapabilities,
    ProviderHealth,
    ProviderPaymentRequest,
    ProviderResult,
    ProviderUnavailable,
    UnsupportedProviderOperation,
)


PLANNED_CAPABILITIES = ProviderCapabilities(
    supports_push_payment=True,
    supports_status_query=True,
    supports_cancel=False,
    supports_refund=False,
    supports_webhooks=False,
    supports_qr=False,
)


class UnconfiguredRailAdapter:
    """Placeholder for a real payment institution whose contract is not in-repo."""

    live_contract_ready = False

    def __init__(self, code: str, capabilities: ProviderCapabilities | None = None) -> None:
        self.code = code
        self.capabilities = capabilities or PLANNED_CAPABILITIES

    async def initiate_payment(self, request: ProviderPaymentRequest) -> ProviderResult:
        raise ProviderUnavailable(
            f"Live {self.code} adapter is not implemented; payment {request.reference} was not sent"
        )

    async def get_payment_status(self, provider_reference: str) -> ProviderResult:
        raise ProviderUnavailable(f"Live {self.code} status query is not implemented")

    async def cancel_payment(self, provider_reference: str) -> ProviderResult:
        if not self.capabilities.supports_cancel:
            raise UnsupportedProviderOperation("cancel")
        raise ProviderUnavailable(f"Live {self.code} cancel is not implemented")

    async def refund_payment(self, provider_reference: str, amount: Decimal) -> ProviderResult:
        if not self.capabilities.supports_refund:
            raise UnsupportedProviderOperation("refund")
        raise ProviderUnavailable(f"Live {self.code} refund is not implemented")

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            configured=False,
            contract_ready=False,
            supports_health_check=False,
            reachable=None,
            message="Live provider contract is not implemented",
        )


class AirtelMoneyAdapter(UnconfiguredRailAdapter):
    def __init__(self) -> None:
        super().__init__("airtel_money")


class TnmMpambaAdapter(UnconfiguredRailAdapter):
    def __init__(self) -> None:
        super().__init__("tnm_mpamba")


class NationalBankAdapter(UnconfiguredRailAdapter):
    def __init__(self) -> None:
        super().__init__("national_bank")


class FdhBankAdapter(UnconfiguredRailAdapter):
    def __init__(self) -> None:
        super().__init__("fdh_bank")


class StandardBankAdapter(UnconfiguredRailAdapter):
    def __init__(self) -> None:
        super().__init__("standard_bank")
