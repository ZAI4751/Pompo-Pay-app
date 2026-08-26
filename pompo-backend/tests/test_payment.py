"""M006 payment-core unit and service tests."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
from app.api.v1.payments import get_payment_service, router
from app.models import (
    Branch,
    Merchant,
    PaymentAttempt,
    PaymentProvider,
    Permission,
    Role,
    RolePermission,
    Till,
    Transaction,
    User,
)
from app.models.base import Base
from app.models.enums import ProviderCode, TransactionStatus
from app.payments.state_machine import InvalidTransactionTransition, validate_transition
from app.services.payment import (
    PaymentConflictError,
    PaymentForbiddenError,
    PaymentInvalidError,
    PaymentService,
)


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


async def _fixture(session: AsyncSession) -> tuple[User, Merchant, Branch, Till]:
    permission = Permission(code="transactions:create")
    update_permission = Permission(code="transactions:update")
    read_permission = Permission(code="transactions:read")
    role = Role(code=f"payment_{uuid.uuid4().hex}", name="Payment operator")
    role.permissions.append(RolePermission(permission=permission))
    role.permissions.append(RolePermission(permission=update_permission))
    role.permissions.append(RolePermission(permission=read_permission))
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
            permission,
            update_permission,
            read_permission,
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


def _values(merchant: Merchant, branch: Branch, till: Till, key: str = "order-1") -> dict:
    return {
        "merchant_id": merchant.id,
        "branch_id": branch.id,
        "till_id": till.id,
        "amount": Decimal("125.50"),
        "currency": "MWK",
        "payment_method": "mobile_money",
        "provider_code": "simulated",
        "idempotency_key": key,
    }


@pytest.mark.asyncio
async def test_state_machine_rejects_invalid_and_allows_terminal_refund() -> None:
    validate_transition(TransactionStatus.CREATED, TransactionStatus.PENDING)
    validate_transition(TransactionStatus.SUCCESS, TransactionStatus.REFUNDED)
    with pytest.raises(InvalidTransactionTransition):
        validate_transition(TransactionStatus.SUCCESS, TransactionStatus.CREATED)


@pytest.mark.asyncio
async def test_payment_creation_is_idempotent_and_creates_first_attempt(
    session: AsyncSession,
) -> None:
    actor, merchant, branch, till = await _fixture(session)
    service = PaymentService(session)
    values = _values(merchant, branch, till)

    first = await service.create_payment(actor, values)
    second = await service.create_payment(actor, values)

    assert first.id == second.id
    assert first.reference == second.reference
    assert len(first.attempts) == 1


@pytest.mark.asyncio
async def test_idempotency_key_rejects_different_request(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _fixture(session)
    service = PaymentService(session)
    await service.create_payment(actor, _values(merchant, branch, till))
    changed = _values(merchant, branch, till)
    changed["amount"] = Decimal("126.00")
    with pytest.raises(PaymentConflictError):
        await service.create_payment(actor, changed)


@pytest.mark.asyncio
async def test_payment_scope_and_lifecycle_are_enforced(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _fixture(session)
    other = Merchant(
        name="Other", contact_email=f"{uuid.uuid4().hex}@example.com", contact_phone="+265991000001"
    )
    session.add(other)
    await session.commit()
    service = PaymentService(session)
    with pytest.raises(PaymentForbiddenError):
        await service.create_payment(actor, _values(other, branch, till, "other"))
    payment = await service.create_payment(actor, _values(merchant, branch, till, "valid"))
    with pytest.raises(PaymentInvalidError):
        await service.transition_payment(actor, payment.reference, TransactionStatus.SUCCESS)


@pytest.mark.asyncio
async def test_missing_provider_is_deterministic_failure(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _fixture(session)
    service = PaymentService(session)
    values = _values(merchant, branch, till, "missing-provider")
    values["provider_code"] = "not-configured"
    with pytest.raises(PaymentInvalidError, match="provider"):
        await service.create_payment(actor, values)


@pytest.mark.asyncio
async def test_payment_api_requires_authentication() -> None:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[deps.get_auth_service] = lambda: object()
    application.dependency_overrides[get_payment_service] = lambda: object()
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/payments/PMP-MISSING")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_payment_api_serializes_transaction() -> None:
    merchant_id = uuid.uuid4()
    transaction = Transaction(
        id=uuid.uuid4(),
        merchant_id=merchant_id,
        branch_id=uuid.uuid4(),
        till_id=uuid.uuid4(),
        reference="PMP-API",
        idempotency_key="api-key",
        request_fingerprint="a" * 64,
        amount=Decimal("10.00"),
        currency="MWK",
        payment_method="mobile_money",
        status=TransactionStatus.CREATED,
        attempts=[
            PaymentAttempt(
                id=uuid.uuid4(),
                provider_id=uuid.uuid4(),
                attempt_number=1,
                status="initiated",
                initiated_at=datetime.now(UTC),
            )
        ],
    )

    class PaymentStub:
        async def get_payment(self, _actor: User, _reference: str) -> Transaction:
            return transaction

    application = FastAPI()
    application.include_router(router)
    actor = User(id=uuid.uuid4(), email="api@example.com", full_name="API", hashed_password="hash")

    class AuthorizationStub:
        async def require_permission(self, user: User, _permission: str) -> User:
            return user

    application.dependency_overrides[deps.get_current_user] = lambda: actor
    application.dependency_overrides[deps.get_authorization_service] = lambda: AuthorizationStub()
    application.dependency_overrides[get_payment_service] = lambda: PaymentStub()
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/payments/PMP-API")
    assert response.status_code == 200
    assert response.json()["reference"] == "PMP-API"
