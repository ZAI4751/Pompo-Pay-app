"""Deterministic sandbox adapters used until real provider contracts exist."""

from __future__ import annotations

from decimal import Decimal

from app.payments.providers import (
    ProviderCapabilities,
    ProviderHealth,
    ProviderOutcome,
    ProviderPaymentRequest,
    ProviderRejected,
    ProviderResult,
    ProviderTimeout,
    UnsupportedProviderOperation,
)


class MockProvider:
    live_contract_ready = True

    def __init__(self, code: str, outcome: ProviderOutcome) -> None:
        self.code = code
        self.outcome = outcome
        self.capabilities = ProviderCapabilities(
            supports_cancel=True,
            supports_status_query=True,
            supports_push_payment=True,
        )

    async def initiate_payment(self, request: ProviderPaymentRequest) -> ProviderResult:
        if self.outcome is ProviderOutcome.REJECTED:
            raise ProviderRejected()
        if self.outcome is ProviderOutcome.TIMEOUT:
            raise ProviderTimeout()
        return ProviderResult(
            outcome=self.outcome,
            provider_reference=f"{self.code}-{request.reference}",
            provider_status=self.outcome.value,
            retryable=self.outcome is ProviderOutcome.PENDING,
        )

    async def get_payment_status(self, provider_reference: str) -> ProviderResult:
        if not self.capabilities.supports_status_query:
            raise UnsupportedProviderOperation("status_query")
        return ProviderResult(self.outcome, provider_reference, self.outcome.value)

    async def cancel_payment(self, provider_reference: str) -> ProviderResult:
        if not self.capabilities.supports_cancel:
            raise UnsupportedProviderOperation("cancel")
        return ProviderResult(ProviderOutcome.FAILED, provider_reference, "cancelled")

    async def refund_payment(self, provider_reference: str, amount: Decimal) -> ProviderResult:
        if not self.capabilities.supports_refund:
            raise UnsupportedProviderOperation("refund")
        return ProviderResult(ProviderOutcome.SUCCESS, provider_reference, "refunded")

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            configured=True,
            contract_ready=True,
            supports_health_check=True,
            reachable=True,
            message="Simulated adapter is local and deterministic",
        )


class MockSuccessProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__("simulated", ProviderOutcome.SUCCESS)


class MockPendingProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__("simulated_pending", ProviderOutcome.PENDING)


class MockFailureProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__("simulated_failure", ProviderOutcome.REJECTED)


class MockTimeoutProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__("simulated_timeout", ProviderOutcome.TIMEOUT)
