"""Database-backed sandbox provider catalog.

Identifiers here must match ``ProviderCode`` and the in-process registry.
Live Airtel/TNM/bank adapters are not registered; those rows stay inactive
and simulated until a later milestone.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.base import AppEnvironment
from app.models.enums import ProviderCode
from app.models.payment import PaymentProvider
from app.payments.providers import ProviderCapabilities
from app.payments.registry import ProviderRegistry


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
        supports_webhooks=False,
        supports_qr=False,
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
    is_active: bool
    is_simulated: bool
    environment: str
    priority: int
    supported_currencies: tuple[str, ...]
    supported_payment_methods: tuple[str, ...]
    capabilities: dict[str, bool]


PROVIDER_CATALOG: tuple[ProviderCatalogDefinition, ...] = (
    ProviderCatalogDefinition(
        code=ProviderCode.SIMULATED,
        display_name="Simulated sandbox",
        is_active=True,
        is_simulated=True,
        environment="sandbox",
        priority=1,
        supported_currencies=("MWK",),
        supported_payment_methods=("mobile_money",),
        capabilities=SANDBOX_CAPABILITIES,
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.AIRTEL_MONEY,
        display_name="Airtel Money (sandbox placeholder — not live)",
        is_active=False,
        is_simulated=True,
        environment="sandbox",
        priority=10,
        supported_currencies=("MWK",),
        supported_payment_methods=("mobile_money",),
        capabilities=PLANNED_CAPABILITIES,
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.TNM_MPAMBA,
        display_name="TNM Mpamba (sandbox placeholder — not live)",
        is_active=False,
        is_simulated=True,
        environment="sandbox",
        priority=20,
        supported_currencies=("MWK",),
        supported_payment_methods=("mobile_money",),
        capabilities=PLANNED_CAPABILITIES,
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.NATIONAL_BANK,
        display_name="National Bank (sandbox placeholder — not live)",
        is_active=False,
        is_simulated=True,
        environment="sandbox",
        priority=30,
        supported_currencies=("MWK",),
        supported_payment_methods=("bank",),
        capabilities=PLANNED_CAPABILITIES,
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.FDH_BANK,
        display_name="FDH Bank (sandbox placeholder — not live)",
        is_active=False,
        is_simulated=True,
        environment="sandbox",
        priority=40,
        supported_currencies=("MWK",),
        supported_payment_methods=("bank",),
        capabilities=PLANNED_CAPABILITIES,
    ),
    ProviderCatalogDefinition(
        code=ProviderCode.STANDARD_BANK,
        display_name="Standard Bank (sandbox placeholder — not live)",
        is_active=False,
        is_simulated=True,
        environment="sandbox",
        priority=50,
        supported_currencies=("MWK",),
        supported_payment_methods=("bank",),
        capabilities=PLANNED_CAPABILITIES,
    ),
)


async def seed_provider_catalog(
    session: AsyncSession, registry: ProviderRegistry | None = None
) -> int:
    """Insert missing catalog rows. Existing rows are not overwritten.

    Returns the number of rows created.
    """
    registry = registry or ProviderRegistry()
    created = 0
    for definition in PROVIDER_CATALOG:
        existing = await session.scalar(
            select(PaymentProvider).where(PaymentProvider.code == definition.code)
        )
        if existing is not None:
            continue
        adapter_configured = definition.code.value in {adapter.code for adapter in registry.list()}
        session.add(
            PaymentProvider(
                code=definition.code,
                display_name=definition.display_name,
                is_active=definition.is_active and adapter_configured,
                is_simulated=definition.is_simulated,
                environment=definition.environment,
                priority=definition.priority,
                supported_currencies=list(definition.supported_currencies),
                supported_payment_methods=list(definition.supported_payment_methods),
                capabilities=dict(definition.capabilities),
            )
        )
        created += 1
    if created:
        await session.flush()
    return created
