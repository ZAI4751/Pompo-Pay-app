"""Deterministic provider routing."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    Branch,
    Merchant,
    Permission,
    Role,
    RolePermission,
    Till,
    User,
)
from app.models.base import Base
from app.models.enums import ProviderCode, ProviderHealthState
from app.models.payment import PaymentProvider
from app.payments.catalog import seed_provider_catalog
from app.payments.registry import ProviderRegistry
from app.payments.routing import ProviderRoutingError, RoutingRequest, select_provider
from app.services.payment import PaymentInvalidError, PaymentService
from app.services.providers import ProviderCatalogService


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


def _provider(**overrides) -> PaymentProvider:
    values = {
        "code": ProviderCode.SIMULATED,
        "display_name": "Simulated",
        "is_active": True,
        "is_simulated": True,
        "environment": "sandbox",
        "health_state": ProviderHealthState.ACTIVE,
        "priority": 1,
        "supported_currencies": ["MWK"],
        "supported_payment_methods": ["mobile_money"],
    }
    values.update(overrides)
    return PaymentProvider(**values)


def test_routing_selects_lowest_priority_supported_provider() -> None:
    registry = ProviderRegistry()
    low = _provider(code=ProviderCode.SIMULATED, priority=20)
    high = _provider(code=ProviderCode.SIMULATED_PENDING, priority=5)
    selected = select_provider(
        [low, high],
        RoutingRequest(payment_method="mobile_money", currency="MWK"),
        registry,
    )
    assert selected.code is ProviderCode.SIMULATED_PENDING


def test_routing_rejects_disabled_explicit_provider() -> None:
    registry = ProviderRegistry()
    provider = _provider(is_active=False, health_state=ProviderHealthState.DISABLED)
    with pytest.raises(ProviderRoutingError, match="disabled"):
        select_provider(
            [provider],
            RoutingRequest(
                payment_method="mobile_money",
                currency="MWK",
                provider_code="simulated",
            ),
            registry,
        )


def test_routing_rejects_unavailable_provider() -> None:
    registry = ProviderRegistry()
    provider = _provider(
        code=ProviderCode.AIRTEL_MONEY,
        is_active=True,
        health_state=ProviderHealthState.UNAVAILABLE,
        supported_payment_methods=["mobile_money"],
    )
    with pytest.raises(ProviderRoutingError, match="unavailable"):
        select_provider(
            [provider],
            RoutingRequest(
                payment_method="mobile_money",
                currency="MWK",
                provider_code="airtel_money",
            ),
            registry,
        )


def test_routing_rejects_unsupported_method() -> None:
    registry = ProviderRegistry()
    provider = _provider(supported_payment_methods=["bank"])
    with pytest.raises(ProviderRoutingError, match="does not support"):
        select_provider(
            [provider],
            RoutingRequest(
                payment_method="mobile_money",
                currency="MWK",
                provider_code="simulated",
            ),
            registry,
        )


def test_routing_skips_stub_rails_even_if_active() -> None:
    registry = ProviderRegistry()
    stub = _provider(
        code=ProviderCode.AIRTEL_MONEY,
        is_active=True,
        health_state=ProviderHealthState.ACTIVE,
        priority=1,
    )
    simulated = _provider(priority=50)
    selected = select_provider(
        [stub, simulated],
        RoutingRequest(payment_method="mobile_money", currency="MWK"),
        registry,
    )
    assert selected.code is ProviderCode.SIMULATED


def test_routing_skips_tnm_even_if_marked_active() -> None:
    registry = ProviderRegistry()
    tnm = _provider(
        code=ProviderCode.TNM_MPAMBA,
        is_active=True,
        health_state=ProviderHealthState.ACTIVE,
        priority=1,
    )
    simulated = _provider(priority=50)
    selected = select_provider(
        [tnm, simulated],
        RoutingRequest(payment_method="mobile_money", currency="MWK"),
        registry,
    )
    assert selected.code is ProviderCode.SIMULATED
    with pytest.raises(ProviderRoutingError, match="cannot process payments"):
        select_provider(
            [tnm, simulated],
            RoutingRequest(
                payment_method="mobile_money",
                currency="MWK",
                provider_code="tnm_mpamba",
            ),
            registry,
        )


def test_routing_rejects_production_rail_outside_production() -> None:
    registry = ProviderRegistry()
    provider = _provider(
        environment="live",
        is_active=True,
        health_state=ProviderHealthState.ACTIVE,
    )
    with pytest.raises(ProviderRoutingError, match="production rail"):
        select_provider(
            [provider],
            RoutingRequest(
                payment_method="mobile_money",
                currency="MWK",
                provider_code="simulated",
            ),
            registry,
        )


@pytest.mark.asyncio
async def test_payment_service_uses_router_when_provider_omitted(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    permissions = [
        Permission(code=code)
        for code in ("transactions:create", "transactions:read", "transactions:update")
    ]
    role = Role(code=f"route_{uuid.uuid4().hex}", name="Route")
    role.permissions.extend(RolePermission(permission=permission) for permission in permissions)
    merchant = Merchant(
        name="Merchant",
        contact_email=f"{uuid.uuid4().hex}@example.com",
        contact_phone="+265991000000",
    )
    branch = Branch(merchant=merchant, name="Main")
    till = Till(branch=branch, code="T1", name="Counter")
    actor = User(
        merchant=merchant,
        branch=branch,
        role=role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Operator",
        hashed_password="hash",
    )
    session.add_all([*permissions, role, merchant, branch, till, actor])
    await session.commit()

    service = PaymentService(session)
    payment = await service.create_payment(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("10.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": None,
            "idempotency_key": "route-1",
        },
    )
    provider = await session.get(PaymentProvider, payment.provider_id)
    assert provider is not None
    assert provider.code is ProviderCode.SIMULATED


@pytest.mark.asyncio
async def test_disabled_provider_cannot_create_payments(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    admin_permissions = [
        Permission(code=code)
        for code in (
            "providers:read",
            "providers:update",
            "transactions:create",
            "transactions:read",
        )
    ]
    role = Role(code="platform_admin", name="Platform administrator")
    role.permissions.extend(
        RolePermission(permission=permission) for permission in admin_permissions
    )
    merchant = Merchant(
        name="Merchant",
        contact_email=f"{uuid.uuid4().hex}@example.com",
        contact_phone="+265991000000",
    )
    branch = Branch(merchant=merchant, name="Main")
    till = Till(branch=branch, code="T1", name="Counter")
    actor = User(
        merchant=merchant,
        branch=branch,
        role=role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Admin",
        hashed_password="hash",
        is_active=True,
    )
    session.add_all([*admin_permissions, role, merchant, branch, till, actor])
    await session.commit()

    catalog = ProviderCatalogService(session)
    await catalog.disable_provider(actor, "simulated")
    service = PaymentService(session)
    with pytest.raises(PaymentInvalidError, match="disabled"):
        await service.create_payment(
            actor,
            {
                "merchant_id": merchant.id,
                "branch_id": branch.id,
                "till_id": till.id,
                "amount": Decimal("10.00"),
                "currency": "MWK",
                "payment_method": "mobile_money",
                "provider_code": "simulated",
                "idempotency_key": "disabled-1",
            },
        )
