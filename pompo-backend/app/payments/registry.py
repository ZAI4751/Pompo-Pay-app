"""Provider adapter registry. Payment core looks up adapters by code only."""

from __future__ import annotations

from app.payments.adapters import (
    MockFailureProvider,
    MockPendingProvider,
    MockSuccessProvider,
    MockTimeoutProvider,
)
from app.payments.providers import (
    ProviderAdapter,
    ProviderCapabilities,
    ProviderUnavailable,
)
from app.payments.live import build_live_rail_adapter


def default_adapters() -> tuple[ProviderAdapter, ...]:
    return (
        MockSuccessProvider(),
        MockPendingProvider(),
        MockFailureProvider(),
        MockTimeoutProvider(),
        build_live_rail_adapter("airtel_money"),
        build_live_rail_adapter("tnm_mpamba"),
        build_live_rail_adapter("national_bank"),
        build_live_rail_adapter("fdh_bank"),
        build_live_rail_adapter("standard_bank"),
    )


class ProviderRegistry:
    def __init__(self, adapters: tuple[ProviderAdapter, ...] | None = None) -> None:
        selected = adapters or default_adapters()
        self._adapters = {adapter.code: adapter for adapter in selected}

    def get(self, code: str) -> ProviderAdapter:
        adapter = self._adapters.get(code)
        if adapter is None:
            raise ProviderUnavailable(f"Provider '{code}' is not configured")
        return adapter

    def get_optional(self, code: str) -> ProviderAdapter | None:
        return self._adapters.get(code)

    def list(self) -> list[ProviderAdapter]:
        return list(self._adapters.values())

    def capabilities(self, code: str) -> ProviderCapabilities:
        return self.get(code).capabilities
