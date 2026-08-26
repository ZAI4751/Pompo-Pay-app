"""Deterministic sandbox adapters used until real provider contracts exist."""

from __future__ import annotations

from decimal import Decimal

from app.payments.providers import (
    ProviderCapabilities,
    ProviderOutcome,
    ProviderPaymentRequest,
    ProviderRejected,
    ProviderResult,
    ProviderTimeout,
)


class MockProvider:
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
        return ProviderResult(self.outcome, provider_reference, self.outcome.value)

    async def cancel_payment(self, provider_reference: str) -> ProviderResult:
        return ProviderResult(ProviderOutcome.FAILED, provider_reference, "cancelled")

    async def refund_payment(self, provider_reference: str, amount: Decimal) -> ProviderResult:
        return ProviderResult(ProviderOutcome.SUCCESS, provider_reference, "refunded")


class MockSuccessProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__("mock_success", ProviderOutcome.SUCCESS)


class MockPendingProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__("mock_pending", ProviderOutcome.PENDING)


class MockFailureProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__("mock_failure", ProviderOutcome.REJECTED)


class MockTimeoutProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__("mock_timeout", ProviderOutcome.TIMEOUT)
