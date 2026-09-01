"""Combine catalog enablement with adapter health into a lifecycle state."""

from __future__ import annotations

from app.models.enums import ProviderHealthState
from app.payments.providers import ProviderAdapter, ProviderHealth


def operational_health_state(
    *,
    is_active: bool,
    adapter: ProviderAdapter | None,
    adapter_health: ProviderHealth | None,
) -> ProviderHealthState:
    if not is_active:
        return ProviderHealthState.DISABLED
    if adapter is None or not adapter.live_contract_ready:
        return ProviderHealthState.UNAVAILABLE
    if adapter_health is None:
        return ProviderHealthState.ACTIVE
    if not adapter_health.configured or not adapter_health.contract_ready:
        return ProviderHealthState.UNAVAILABLE
    if adapter_health.supports_health_check and adapter_health.reachable is False:
        return ProviderHealthState.UNAVAILABLE
    if adapter_health.supports_health_check and adapter_health.reachable is None:
        return ProviderHealthState.DEGRADED
    return ProviderHealthState.ACTIVE
