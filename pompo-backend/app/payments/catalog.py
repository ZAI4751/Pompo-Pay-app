"""Database-backed provider catalog.

Identifiers here must match ``ProviderCode`` and the in-process registry.
TNM Mpamba Malawi is a named adapter with no live HTTP contract yet.
Standard Bank Malawi is a named card/acquiring adapter with no live HTTP
contract yet. Other bank adapters remain structured stubs. Airtel Money
Malawi is a live contract (inactive until credentials are configured and
an admin enables it).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.base import AppEnvironment
from app.models.enums import ProviderCode, ProviderHealthState, ProviderType
from app.models.payment import PaymentProvider
from app.payments.providers import ProviderCapabilities
from app.payments.registry import ProviderRegistry
from app.payments.tnm_mpamba import TNM_CAPABILITIES
from app.payments.standard_bank import STANDARD_BANK_CAPABILITIES


class ProductionCatalogSeedError(RuntimeError):
    """Raised when sandbox catalog seeding is attempted in production."""


def ensure_non_production_catalog_seed(app_env: AppEnvironment) -> None:
    if app_env is AppEnvironment.PRODUCTION:
        raise ProductionCatalogSeedError("Refusing to seed sandbox providers in production")


SANDBOX_CAPABILITIES = asdict(
    ProviderCapabilities(
        supports_push_payment=True,
        supports_status_query=True,
        supports_cancel=True,
        supports_refund=False,
        supports_webhooks=True,
        supports_qr=False,
        supports_payment_instruments=True,
        supports_instrument_enroll=True,
        supports_instrument_charge=True,
        supports_instrument_verify=True,
        supports_instrument_remove=True,
    )
)

PLANNED_CAPABILITIES = asdict(
    ProviderCapabilities(
        supports_push_payment=True,
        supports_status_query=True,
        supports_cancel=False,
        supports_refund=False,
        supports_webhooks=False,
        supports_qr=False,
    )
)


@dataclass(frozen=True)
class ProviderCatalogDefinition:
    code: ProviderCode
    display_name: str
    provider_type: ProviderType
    is_active: bool
    is_simulated: bool
    environment: str
    health_state: ProviderHealthState
    priority: int
    supported_currencies: tuple[str, ...]
    supported_payment_methods: tuple[str, ...]
    capabilities: dict[str, bool]
    config_refs: dict[str, str]


def _refs(code: str) -> dict[str, str]:
    prefix = f"PROVIDER_{code.upper()}"
    return {
        "base_url_env": f"{prefix}_BASE_URL",
        "timeout_env": f"{prefix}_TIMEOUT_SECONDS",
        "client_id_env": f"{prefix}_CLIENT_ID",
        "credential_env": f"{prefix}_CREDENTIAL_REF",
        "webhook_secret_env": f"{prefix}_WEBHOOK_SECRET_REF",
    }


PROVIDER_CATALOG: tuple[ProviderCatalogDefinition, ...] = (
    ProviderCatalogDefinition(
        code=ProviderCode.SIMULATED,
        display_name="Simulated sandbox",
        provider_type=ProviderType.SIMULATED,
        is_active=True,
        is_simulated=True,
        environment="sandbox",
        health_state=ProviderHealthState.ACTIVE,
        priority=1,
        supported_currencies=("MWK",),
        supported_payment_methods=("mobile_money", "bank", "card"),
        capabilities=SANDBOX_CAPABILITIES,
        config_refs=_refs("simulated"),
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.SIMULATED_PENDING,
        display_name="Simulated pending",
        provider_type=ProviderType.SIMULATED,
        is_active=False,
        is_simulated=True,
        environment="sandbox",
        health_state=ProviderHealthState.DISABLED,
        priority=2,
        supported_currencies=("MWK",),
        supported_payment_methods=("mobile_money",),
        capabilities=SANDBOX_CAPABILITIES,
        config_refs=_refs("simulated_pending"),
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.SIMULATED_FAILURE,
        display_name="Simulated failure",
        provider_type=ProviderType.SIMULATED,
        is_active=False,
        is_simulated=True,
        environment="sandbox",
        health_state=ProviderHealthState.DISABLED,
        priority=3,
        supported_currencies=("MWK",),
        supported_payment_methods=("mobile_money",),
        capabilities=SANDBOX_CAPABILITIES,
        config_refs=_refs("simulated_failure"),
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.SIMULATED_TIMEOUT,
        display_name="Simulated timeout",
        provider_type=ProviderType.SIMULATED,
        is_active=False,
        is_simulated=True,
        environment="sandbox",
        health_state=ProviderHealthState.DISABLED,
        priority=4,
        supported_currencies=("MWK",),
        supported_payment_methods=("mobile_money",),
        capabilities=SANDBOX_CAPABILITIES,
        config_refs=_refs("simulated_timeout"),
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.AIRTEL_MONEY,
        display_name="Airtel Money Malawi",
        provider_type=ProviderType.MOBILE_MONEY,
        is_active=False,
        is_simulated=False,
        environment="sandbox",
        health_state=ProviderHealthState.DISABLED,
        priority=10,
        supported_currencies=("MWK",),
        supported_payment_methods=("mobile_money",),
        capabilities=asdict(
            ProviderCapabilities(
                supports_push_payment=True,
                supports_status_query=True,
                supports_cancel=False,
                supports_refund=False,
                supports_webhooks=True,
                supports_qr=False,
            )
        ),
        config_refs=_refs("airtel_money"),
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.TNM_MPAMBA,
        display_name="TNM Mpamba Malawi",
        provider_type=ProviderType.MOBILE_MONEY,
        is_active=False,
        is_simulated=False,
        environment="sandbox",
        health_state=ProviderHealthState.DISABLED,
        priority=20,
        supported_currencies=("MWK",),
        supported_payment_methods=("mobile_money",),
        capabilities=asdict(TNM_CAPABILITIES),
        config_refs=_refs("tnm_mpamba"),
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.NATIONAL_BANK,
        display_name="National Bank (live contract not implemented)",
        provider_type=ProviderType.BANK,
        is_active=False,
        is_simulated=True,
        environment="sandbox",
        health_state=ProviderHealthState.UNAVAILABLE,
        priority=30,
        supported_currencies=("MWK",),
        supported_payment_methods=("bank",),
        capabilities=PLANNED_CAPABILITIES,
        config_refs=_refs("national_bank"),
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.FDH_BANK,
        display_name="FDH Bank (live contract not implemented)",
        provider_type=ProviderType.BANK,
        is_active=False,
        is_simulated=True,
        environment="sandbox",
        health_state=ProviderHealthState.UNAVAILABLE,
        priority=40,
        supported_currencies=("MWK",),
        supported_payment_methods=("bank",),
        capabilities=PLANNED_CAPABILITIES,
        config_refs=_refs("fdh_bank"),
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.STANDARD_BANK,
        display_name="Standard Bank Malawi",
        provider_type=ProviderType.BANK,
        is_active=False,
        is_simulated=False,
        environment="sandbox",
        health_state=ProviderHealthState.DISABLED,
        priority=50,
        supported_currencies=("MWK",),
        supported_payment_methods=("card",),
        capabilities=asdict(STANDARD_BANK_CAPABILITIES),
        config_refs=_refs("standard_bank"),
    ),
)

CATALOG_BY_CODE = {definition.code: definition for definition in PROVIDER_CATALOG}


async def seed_provider_catalog(
    session: AsyncSession, registry: ProviderRegistry | None = None
) -> int:
    """Insert missing catalog rows.

    Existing rows keep operator-controlled flags (``is_active``, health).
    Additive catalog fields (payment methods, new capability keys) are merged
    so sandbox rails pick up later instrument/card support without a recreate.

    Returns the number of rows created.
    """
    registry = registry or ProviderRegistry()
    created = 0
    for definition in PROVIDER_CATALOG:
        existing = await session.scalar(
            select(PaymentProvider).where(PaymentProvider.code == definition.code)
        )
        if existing is not None:
            methods = list(existing.supported_payment_methods or [])
            method_changed = False
            for method in definition.supported_payment_methods:
                if method not in methods:
                    methods.append(method)
                    method_changed = True
            if method_changed:
                existing.supported_payment_methods = methods
            capabilities = dict(existing.capabilities or {})
            capability_changed = False
            for key, value in definition.capabilities.items():
                if key not in capabilities:
                    capabilities[key] = value
                    capability_changed = True
            if capability_changed:
                existing.capabilities = capabilities
            continue
        adapter = registry.get_optional(definition.code.value)
        adapter_ready = adapter is not None and adapter.live_contract_ready
        session.add(
            PaymentProvider(
                code=definition.code,
                display_name=definition.display_name,
                provider_type=definition.provider_type,
                is_active=definition.is_active and adapter_ready,
                is_simulated=definition.is_simulated,
                environment=definition.environment,
                health_state=(
                    ProviderHealthState.ACTIVE
                    if definition.is_active and adapter_ready
                    else definition.health_state
                ),
                priority=definition.priority,
                supported_currencies=list(definition.supported_currencies),
                supported_payment_methods=list(definition.supported_payment_methods),
                capabilities=dict(definition.capabilities),
                config_refs=dict(definition.config_refs),
            )
        )
        created += 1
    if created:
        await session.flush()
    return created
