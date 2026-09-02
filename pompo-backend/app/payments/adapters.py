"""Deterministic sandbox adapters used until real provider contracts exist."""

from __future__ import annotations

from decimal import Decimal

from app.payments.credentials import ProviderCredentials
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
from app.payments.webhooks import (
    NormalizedWebhookEvent,
    WebhookVerificationResult,
    is_supported_mock_event_type,
    parse_mock_webhook_body,
    verify_mock_signature,
)


class MockProvider:
    live_contract_ready = True

    def __init__(
        self,
        code: str,
        outcome: ProviderOutcome,
        *,
        supports_webhooks: bool = False,
    ) -> None:
        self.code = code
        self.outcome = outcome
        self.capabilities = ProviderCapabilities(
            supports_cancel=True,
            supports_status_query=True,
            supports_push_payment=True,
            supports_webhooks=supports_webhooks,
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
            provider_transaction_id=f"{self.code}-{request.reference}",
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

    async def verify_webhook(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
        credentials: ProviderCredentials,
    ) -> WebhookVerificationResult:
        if not self.capabilities.supports_webhooks:
            return WebhookVerificationResult(False, failure_reason="Provider does not support webhooks")
        return verify_mock_signature(
            headers=headers,
            body=body,
            secret=credentials.webhook_secret(),
        )

    async def parse_webhook(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> NormalizedWebhookEvent:
        if not self.capabilities.supports_webhooks:
            raise UnsupportedProviderOperation("webhook")
        event = parse_mock_webhook_body(body)
        if not is_supported_mock_event_type(event.event_type):
            raise ValueError(f"Unsupported event type: {event.event_type}")
        return event

    async def verify_settlement(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
        credentials: ProviderCredentials,
    ) -> WebhookVerificationResult:
        if not self.capabilities.supports_webhooks:
            return WebhookVerificationResult(
                False, failure_reason="Provider does not support settlement ingestion"
            )
        from app.payments.settlement import verify_mock_settlement

        return verify_mock_settlement(
            headers=headers,
            body=body,
            secret=credentials.webhook_secret(),
        )

    async def parse_settlement(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ):
        if not self.capabilities.supports_webhooks:
            raise UnsupportedProviderOperation("settlement")
        from app.payments.settlement import parse_mock_settlement_body

        return parse_mock_settlement_body(body)


class MockSuccessProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__("simulated", ProviderOutcome.SUCCESS, supports_webhooks=True)


class MockPendingProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__("simulated_pending", ProviderOutcome.PENDING, supports_webhooks=True)


class MockFailureProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__("simulated_failure", ProviderOutcome.REJECTED)


class MockTimeoutProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__("simulated_timeout", ProviderOutcome.TIMEOUT)
