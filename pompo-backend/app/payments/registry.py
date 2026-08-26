"""Provider adapter registry and deterministic routing."""

from __future__ import annotations

from app.payments.adapters import (
    MockFailureProvider,
    MockPendingProvider,
    MockProvider,
    MockSuccessProvider,
    MockTimeoutProvider,
)
from app.payments.providers import (
    ProviderAdapter,
    ProviderCapabilities,
    ProviderOutcome,
    ProviderUnavailable,
)


class ProviderRegistry:
    def __init__(self, adapters: tuple[ProviderAdapter, ...] | None = None) -> None:
        selected = adapters or (
            MockSuccessProvider(),
            MockPendingProvider(),
            MockFailureProvider(),
            MockTimeoutProvider(),
            MockProvider("simulated", ProviderOutcome.SUCCESS),
        )
        self._adapters = {adapter.code: adapter for adapter in selected}

    def get(self, code: str) -> ProviderAdapter:
        adapter = self._adapters.get(code)
        if adapter is None:
            raise ProviderUnavailable(f"Provider '{code}' is not configured")
        return adapter

    def list(self) -> list[ProviderAdapter]:
        return list(self._adapters.values())

    def capabilities(self, code: str) -> ProviderCapabilities:
        return self.get(code).capabilities
