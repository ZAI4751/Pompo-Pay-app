"""Provider failure taxonomy, retry classification, and attempt integration."""

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
from app.payments.adapters import MockTimeoutProvider
from app.payments.providers import (
    ProviderAuthenticationError,
    ProviderDuplicate,
    ProviderErrorCode,
    ProviderInvalidRequest,
    ProviderRateLimited,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
    RetryClass,
    retry_class_for,
)
from app.payments.registry import ProviderRegistry
from app.payments.retry import MAX_PROVIDER_ATTEMPTS, should_open_new_attempt, should_retry_error
from app.payments.stubs import AirtelMoneyAdapter
from app.services.payment import PaymentInvalidError, PaymentService


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


def test_failure_codes_are_classified_as_retryable_or_not() -> None:
    assert retry_class_for(ProviderErrorCode.TIMEOUT) is RetryClass.RETRYABLE
    assert retry_class_for(ProviderErrorCode.UNAVAILABLE) is RetryClass.RETRYABLE
    assert retry_class_for(ProviderErrorCode.RATE_LIMITED) is RetryClass.RETRYABLE
    assert retry_class_for(ProviderErrorCode.AUTHENTICATION) is RetryClass.NON_RETRYABLE
    assert retry_class_for(ProviderErrorCode.INVALID_REQUEST) is RetryClass.NON_RETRYABLE
    assert retry_class_for(ProviderErrorCode.REJECTED) is RetryClass.NON_RETRYABLE
    assert retry_class_for(ProviderErrorCode.DUPLICATE) is RetryClass.NON_RETRYABLE
    assert retry_class_for(ProviderErrorCode.UNKNOWN) is RetryClass.NON_RETRYABLE
    assert ProviderTimeout().retryable is True
    assert ProviderUnavailable().retryable is True
    assert ProviderRateLimited().retryable is True
    assert ProviderAuthenticationError().retryable is False
    assert ProviderInvalidRequest().retryable is False
    assert ProviderRejected().retryable is False
    assert ProviderDuplicate().retryable is False


def test_retry_policy_is_bounded() -> None:
    timeout = ProviderTimeout()
    assert should_retry_error(timeout, 1) is True
    assert should_retry_error(timeout, MAX_PROVIDER_ATTEMPTS) is False
    assert should_open_new_attempt(attempt_number=2, retryable=False) is False
    assert should_retry_error(ProviderRejected(), 1) is False


@pytest.mark.asyncio
async def test_stub_adapter_does_not_invent_a_live_http_call() -> None:
    from app.payments.providers import ProviderPaymentRequest, ProviderUnavailable

    request = ProviderPaymentRequest("PMP-1", Decimal("10.00"), "MWK", "merchant")
    with pytest.raises(ProviderUnavailable, match="not implemented"):
        await AirtelMoneyAdapter().initiate_payment(request)
    health = await AirtelMoneyAdapter().health_check()
    assert health.configured is False
    assert health.contract_ready is False
    assert health.supports_health_check is False


async def _actor_graph(session: AsyncSession, provider_code: ProviderCode) -> tuple[User, Merchant, Branch, Till]:
    permissions = [
        Permission(code=code)
        for code in ("transactions:create", "transactions:read", "transactions:update")
    ]
    role = Role(code=f"retry_{uuid.uuid4().hex}", name="Retry")
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
            PaymentProvider(code=provider_code, display_name=provider_code.value, is_active=True),
        ]
    )
    await session.commit()
    return actor, merchant, branch, till


@pytest.mark.asyncio
async def test_timeout_records_retryable_attempt_and_does_not_duplicate(
    session: AsyncSession,
) -> None:
    actor, merchant, branch, till = await _actor_graph(session, ProviderCode.SIMULATED_TIMEOUT)
    service = PaymentService(session, registry=ProviderRegistry((MockTimeoutProvider(),)))
    payment = await service.create_payment(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("10.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated_timeout",
            "idempotency_key": "timeout-1",
        },
    )
    first = await service.process_payment(actor, payment.reference)
    assert first.status is TransactionStatus.PROCESSING
    assert first.attempts[0].retryable is True
    assert first.attempts[0].failure_code == "timeout"
    assert first.attempts[0].provider_request["idempotency_key"] == payment.reference

    second = await service.process_payment(actor, payment.reference)
    assert len(second.attempts) == 2
    assert second.attempts[1].provider_request["idempotency_key"] == payment.reference
    assert second.status is TransactionStatus.PROCESSING

    third = await service.process_payment(actor, payment.reference)
    assert len(third.attempts) == 3
    assert third.status is TransactionStatus.TIMEOUT
    with pytest.raises(PaymentInvalidError, match="Retry is not permitted"):
        await service.process_payment(actor, payment.reference)
