"""Shared serialization for provider catalog resources. Never includes secrets."""

from __future__ import annotations

from app.models.payment import PaymentProvider
from app.payments.health import operational_health_state
from app.schemas.payment import (
    ProviderCapabilityResponse,
    ProviderCatalogResponse,
    ProviderConfigurationStatus,
    ProviderHealthResponse,
)
from app.services.providers import ProviderCatalogService


async def catalog_response(
    provider: PaymentProvider, service: ProviderCatalogService
) -> ProviderCatalogResponse:
    capabilities = service.capabilities_for(provider)
    adapter = service.adapter_for(provider.code.value)
    health = await service.adapter_health(provider)
    health_state = operational_health_state(
        is_active=provider.is_active,
        adapter=adapter,
        adapter_health=health,
    )
    configuration = service.configuration_status(provider)
    return ProviderCatalogResponse(
        code=provider.code.value,
        display_name=provider.display_name,
        provider_type=provider.provider_type.value,
        is_active=provider.is_active,
        is_simulated=provider.is_simulated,
        environment=provider.environment,
        health_state=health_state.value,
        priority=provider.priority,
        supported_currencies=list(provider.supported_currencies or []),
        supported_payment_methods=list(provider.supported_payment_methods or []),
        capabilities=ProviderCapabilityResponse(**capabilities),
        adapter_configured=adapter is not None,
        live_contract_ready=bool(adapter and adapter.live_contract_ready),
        configuration=ProviderConfigurationStatus(**configuration),
        health=ProviderHealthResponse(
            configured=health.configured,
            reachable=health.reachable,
            supports_health_check=health.supports_health_check,
            contract_ready=health.contract_ready,
            message=health.message,
        ),
    )
