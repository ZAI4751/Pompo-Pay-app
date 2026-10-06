"""Deterministic provider selection. No heuristics, no learning."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config.base import AppEnvironment, get_settings
from app.models.enums import SANDBOX_PROVIDER_CODES, ProviderHealthState
from app.models.payment import PaymentProvider
from app.payments.credentials import normalize_rail_environment, production_rails_permitted
from app.payments.registry import ProviderRegistry


class ProviderRoutingError(Exception):
    """Raised when no provider satisfies the routing constraints."""


@dataclass(frozen=True)
class RoutingRequest:
    payment_method: str
    currency: str
    provider_code: str | None = None
    environment: str | None = None


def _matches(provider: PaymentProvider, request: RoutingRequest) -> bool:
    methods = {item.lower() for item in (provider.supported_payment_methods or [])}
    currencies = {item.upper() for item in (provider.supported_currencies or [])}
    if request.payment_method.lower() not in methods:
        return False
    if request.currency.upper() not in currencies:
        return False
    if request.environment and provider.environment != request.environment:
        return False
    return True


def _environment_allowed(
    provider: PaymentProvider,
    app_env: AppEnvironment | None = None,
) -> bool:
    return (
        normalize_rail_environment(provider.environment) != "production"
        or production_rails_permitted(app_env)
    )


def _is_routable(
    provider: PaymentProvider,
    registry: ProviderRegistry,
    app_env: AppEnvironment | None = None,
) -> bool:
    if not provider.is_active:
        return False
    if not _environment_allowed(provider, app_env):
        return False
    if provider.health_state is ProviderHealthState.UNAVAILABLE:
        return False
    adapter = registry.get_optional(provider.code.value)
    return adapter is not None and adapter.live_contract_ready


def _is_sandbox_provider(provider: PaymentProvider) -> bool:
    return provider.is_simulated or provider.code in SANDBOX_PROVIDER_CODES


def select_provider(
    candidates: list[PaymentProvider],
    request: RoutingRequest,
    registry: ProviderRegistry,
    *,
    sandbox_payments_enabled: bool | None = None,
    app_env: AppEnvironment | None = None,
) -> PaymentProvider:
    settings = get_settings()
    sandbox_enabled = (
        settings.sandbox_payments_enabled
        if sandbox_payments_enabled is None
        else sandbox_payments_enabled
    )
    environment = app_env or settings.app_env
    explicit_sandbox_request = request.provider_code in {
        code.value for code in SANDBOX_PROVIDER_CODES
    }
    eligible = [
        row
        for row in candidates
        if _matches(row, request)
        and _is_routable(row, registry, environment)
        and (
            not _is_sandbox_provider(row)
            or (
                sandbox_enabled
                and normalize_rail_environment(row.environment) == "sandbox"
                and explicit_sandbox_request
            )
        )
    ]
    eligible.sort(key=lambda row: (row.priority, row.code.value))

    if request.provider_code:
        explicit = next(
            (row for row in eligible if row.code.value == request.provider_code),
            None,
        )
        if explicit is None:
            named = next((row for row in candidates if row.code.value == request.provider_code), None)
            if named is None:
                raise ProviderRoutingError("Requested provider is not registered")
            if not named.is_active:
                raise ProviderRoutingError("Requested provider is disabled")
            if named.health_state is ProviderHealthState.UNAVAILABLE:
                raise ProviderRoutingError("Requested provider is unavailable")
            if not _environment_allowed(named, environment):
                raise ProviderRoutingError(
                    "Requested provider production rail is not allowed in this environment"
                )
            if _is_sandbox_provider(named) and not sandbox_enabled:
                raise ProviderRoutingError("Sandbox payments are disabled in this environment")
            if (
                _is_sandbox_provider(named)
                and normalize_rail_environment(named.environment) != "sandbox"
            ):
                raise ProviderRoutingError("Sandbox providers must remain on the sandbox rail")
            if not _matches(named, request):
                raise ProviderRoutingError("Requested provider does not support this payment")
            raise ProviderRoutingError("Requested provider cannot process payments")
        return explicit

    if not eligible:
        raise ProviderRoutingError("No provider supports this payment")
    return eligible[0]
