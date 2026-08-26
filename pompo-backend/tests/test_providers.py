"""M007 provider contracts, adapters, routing, and payment integration."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    Branch,
    Merchant,
    PaymentProvider,
    Permission,
    Role,
    RolePermission,
    Till,
    User,
)
from app.models.base import Base
from app.models.enums import ProviderCode, TransactionStatus
from app.payments.adapters import (
    MockFailureProvider,
    MockPendingProvider,
    MockSuccessProvider,
    MockTimeoutProvider,
)
from app.payments.providers import (
    ProviderError,
    ProviderOutcome,
    ProviderPaymentRequest,
    ProviderRejected,
    ProviderTimeout,
)
from app.payments.registry import ProviderRegistry
from app.services.payment import PaymentService


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_mock_adapters_normalize_success_pending_failure_and_timeout() -> None:
    request = ProviderPaymentRequest("PMP-1", Decimal("10.00"), "MWK", "merchant")
    success = await MockSuccessProvider().initiate_payment(request)
    pending = await MockPendingProvider().initiate_payment(request)
    assert success.outcome is ProviderOutcome.SUCCESS
    assert pending.outcome is ProviderOutcome.PENDING
    with pytest.raises(ProviderRejected) as rejected:
        await MockFailureProvider().initiate_payment(request)
    with pytest.raises(ProviderTimeout) as timeout:
        await MockTimeoutProvider().initiate_payment(request)
    assert rejected.value.retryable is False
    assert timeout.value.retryable is True


def test_registry_is_deterministic_and_exposes_capabilities() -> None:
    registry = ProviderRegistry()
    assert registry.get("mock_success").code == "mock_success"
    assert registry.get("simulated").code == "simulated"
    assert registry.capabilities("mock_success").supports_status_query is True
    assert [provider.code for provider in registry.list()] == [
        "mock_success",
        "mock_pending",
        "mock_failure",
        "mock_timeout",
        "simulated",
    ]
    with pytest.raises(ProviderError) as missing:
        registry.get("missing")
    assert missing.value.retryable is True


async def _payment_fixture(session: AsyncSession) -> tuple[User, Merchant, Branch, Till]:
    permissions = [
        Permission(code=code)
        for code in ("transactions:create", "transactions:read", "transactions:update")
    ]
    role = Role(code=f"provider_test_{uuid.uuid4().hex}", name="Provider test")
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
    session.add_all(
        [
            *permissions,
            role,
            merchant,
            branch,
            till,
            actor,
            PaymentProvider(code=ProviderCode.SIMULATED, display_name="Simulated"),
        ]
    )
    await session.commit()
    return actor, merchant, branch, till


@pytest.mark.asyncio
async def test_payment_service_integrates_provider_result_into_attempt_and_state(
    session: AsyncSession,
) -> None:
    actor, merchant, branch, till = await _payment_fixture(session)
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
            "provider_code": "simulated",
            "idempotency_key": "provider-test-1",
        },
    )

    processed = await service.process_payment(actor, payment.reference)

    assert processed.status is TransactionStatus.SUCCESS
    assert processed.attempts[0].status.value == "success"
    assert processed.attempts[0].provider_reference == f"simulated-{payment.reference}"
    assert processed.attempts[0].provider_request["amount"] == "10.00"
