"""M015 customer product — registration, repeat pay, requests, splits, favorites, receipts."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
from app.api.v1.customers import get_customer_service, router as customers_router
from app.api.v1.notifications import get_notification_service, router as notifications_router
from app.api.v1.payment_requests import (
    get_payment_request_service,
    router as payment_requests_router,
)
from app.api.v1.payments import (
    get_payment_service,
    get_qr_service as get_payment_qr_service,
    router as payments_router,
)
from app.api.v1.qr import get_qr_service, router as qr_router
from app.api.v1.support import get_support_service, router as support_router
from app.core.security.jwt import JWTConfig
from app.core.security.password import PasswordHasher
from app.models import (
    Branch,
    Merchant,
    PaymentProvider,
    Permission,
    Receipt,
    Role,
    RolePermission,
    Till,
    Transaction,
    User,
)
from app.models.base import Base
from app.models.customer import MerchantFavorite, PaymentRequest
from app.models.enums import PaymentRequestStatus, ProviderCode, TransactionStatus
from app.payments.catalog import seed_provider_catalog
from app.services.customer import CustomerService
from app.services.notification import NotificationService
from app.services.payment import PaymentService
from app.services.payment_request import PaymentRequestService
from app.services.qr import QRService
from app.services.support import SupportService


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


async def _permission(session: AsyncSession, code: str) -> Permission:
    existing = await session.scalar(select(Permission).where(Permission.code == code))
    if existing is not None:
        return existing
    permission = Permission(code=code)
    session.add(permission)
    await session.flush()
    return permission


async def _user(
    session: AsyncSession,
    *,
    permissions: tuple[str, ...],
    merchant: Merchant | None = None,
    branch: Branch | None = None,
    role_code: str = "actor",
    email: str | None = None,
) -> User:
    permission_models = [await _permission(session, code) for code in permissions]
    role = Role(code=f"{role_code}_{uuid.uuid4().hex}", name=role_code)
    actor = User(
        merchant=merchant,
        branch=branch,
        role=role,
        email=email or f"{uuid.uuid4().hex}@example.com",
        full_name=role_code,
        hashed_password=PasswordHasher().hash("correct-horse-battery-staple"),
        is_active=True,
    )
    session.add_all([role, actor])
    await session.flush()
    session.add_all(
        [
            RolePermission(role_id=role.id, permission_id=permission.id)
            for permission in permission_models
        ]
    )
    await session.commit()
    return actor


async def _merchant_graph(session: AsyncSession) -> tuple[Merchant, Branch, Till]:
    merchant = Merchant(
        name="Chikondi Shop",
        contact_email=f"{uuid.uuid4().hex}@example.com",
        contact_phone="+265991000000",
    )
    branch = Branch(merchant=merchant, name="Lilongwe")
    till = Till(branch=branch, code="TILL-1", name="Counter 1")
    session.add_all(
        [merchant, branch, till, PaymentProvider(code=ProviderCode.SIMULATED, display_name="Simulated")]
    )
    await session.commit()
    return merchant, branch, till


async def _seed_customer_role(session: AsyncSession) -> Role:
    role = Role(
        code="customer",
        name="Customer",
        description="Customer",
        is_system_role=True,
        is_active=True,
    )
    session.add(role)
    await session.flush()
    for code in ("transactions:read", "transactions:create", "transactions:update", "transactions:cancel"):
        permission = await _permission(session, code)
        session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    await session.commit()
    return role


def _jwt() -> JWTConfig:
    from app.core.config.base import get_settings

    return JWTConfig(get_settings())


def _app(session: AsyncSession, actor: User) -> FastAPI:
    application = FastAPI()
    application.include_router(qr_router, prefix="/api/v1")
    application.include_router(payments_router, prefix="/api/v1")
    application.include_router(customers_router, prefix="/api/v1")
    application.include_router(payment_requests_router, prefix="/api/v1")
    application.include_router(notifications_router, prefix="/api/v1")
    application.include_router(support_router, prefix="/api/v1")

    class AuthorizationStub:
        async def require_permission(self, user: User, _permission: str) -> User:
            return user

        async def has_permission(self, user: User, _permission: str) -> bool:
            return True

        async def get_user_role(self, user: User):
            return user.role

    qr_service = QRService(session)
    payment_service = PaymentService(session)
    customer_service = CustomerService(session, jwt_config=_jwt(), password_hasher=PasswordHasher())
    request_service = PaymentRequestService(session)
    notification_service = NotificationService(session)
    support_service = SupportService(session)
    stub = AuthorizationStub()
    qr_service._authorization = stub
    payment_service._authorization = stub
    request_service._payments._authorization = stub

    application.dependency_overrides[deps.get_current_user] = lambda: actor
    application.dependency_overrides[deps.get_authorization_service] = lambda: stub
    application.dependency_overrides[get_qr_service] = lambda: qr_service
    application.dependency_overrides[get_payment_qr_service] = lambda: qr_service
    application.dependency_overrides[get_payment_service] = lambda: payment_service
    application.dependency_overrides[get_customer_service] = lambda: customer_service
    application.dependency_overrides[get_payment_request_service] = lambda: request_service
    application.dependency_overrides[get_notification_service] = lambda: notification_service
    application.dependency_overrides[get_support_service] = lambda: support_service
    return application


async def _pay_success(
    session: AsyncSession, actor: User, merchant: Merchant, branch: Branch, till: Till
) -> Transaction:
    await seed_provider_catalog(session)
    await session.commit()
    service = PaymentService(session)

    class AuthorizationStub:
        async def has_permission(self, user: User, _permission: str) -> bool:
            return True

        async def get_user_role(self, user: User):
            return user.role

    service._authorization = AuthorizationStub()
    payment = await service.create_payment(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("1500.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "idempotency_key": f"pay-{uuid.uuid4().hex}",
        },
        require_merchant_scope=False,
    )
    processed = await service.process_payment(actor, payment.reference)
    return processed


@pytest.mark.asyncio
async def test_customer_registration_valid_and_duplicate(session: AsyncSession) -> None:
    await _seed_customer_role(session)
    service = CustomerService(session, jwt_config=_jwt(), password_hasher=PasswordHasher())
    tokens, user = await service.register(
        {
            "email": "ada@example.com",
            "password": "strong-pass-1",
            "full_name": "Ada Customer",
            "phone": "+265999111222",
        }
    )
    assert user.email == "ada@example.com"
    assert tokens.access_token
    assert user.role.code == "customer"
    with pytest.raises(Exception):
        await service.register(
            {
                "email": "ada@example.com",
                "password": "strong-pass-1",
                "full_name": "Ada Two",
            }
        )


@pytest.mark.asyncio
async def test_repeat_payment_creates_new_transaction(session: AsyncSession) -> None:
    merchant, branch, till = await _merchant_graph(session)
    customer = await _user(
        session,
        permissions=("transactions:create", "transactions:read", "transactions:update"),
        role_code="customer",
    )
    original = await _pay_success(session, customer, merchant, branch, till)
    assert original.status is TransactionStatus.SUCCESS
    old_id = original.id
    old_reference = original.reference
    service = PaymentService(session)

    class AuthorizationStub:
        async def has_permission(self, user: User, _permission: str) -> bool:
            return True

        async def get_user_role(self, user: User):
            return user.role

    service._authorization = AuthorizationStub()
    repeated = await service.repeat_payment(
        customer, old_reference, {"idempotency_key": f"repeat-{uuid.uuid4().hex}"}
    )
    assert repeated.reference != old_reference
    assert repeated.id != old_id
    reloaded = await session.get(Transaction, old_id)
    assert reloaded is not None
    assert reloaded.reference == old_reference
    assert reloaded.status is TransactionStatus.SUCCESS
    processed = await service.process_payment(customer, repeated.reference)
    assert processed.status is TransactionStatus.SUCCESS
    receipt = await session.scalar(select(Receipt).where(Receipt.transaction_id == processed.id))
    assert receipt is not None


@pytest.mark.asyncio
async def test_repeat_payment_blocked_when_merchant_inactive(session: AsyncSession) -> None:
    merchant, branch, till = await _merchant_graph(session)
    customer = await _user(
        session,
        permissions=("transactions:create", "transactions:read", "transactions:update"),
        role_code="customer",
    )
    original = await _pay_success(session, customer, merchant, branch, till)
    merchant.is_active = False
    await session.commit()
    service = PaymentService(session)

    class AuthorizationStub:
        async def has_permission(self, user: User, _permission: str) -> bool:
            return True

        async def get_user_role(self, user: User):
            return user.role

    service._authorization = AuthorizationStub()
    with pytest.raises(Exception):
        await service.repeat_payment(
            customer, original.reference, {"idempotency_key": f"repeat-{uuid.uuid4().hex}"}
        )


@pytest.mark.asyncio
async def test_payment_request_create_pay_fulfill_and_isolation(session: AsyncSession) -> None:
    merchant, branch, till = await _merchant_graph(session)
    await seed_provider_catalog(session)
    await session.commit()
    requester = await _user(
        session,
        permissions=("transactions:create", "transactions:read", "transactions:update"),
        role_code="customer",
    )
    payer = await _user(
        session,
        permissions=("transactions:create", "transactions:read", "transactions:update"),
        role_code="customer",
    )
    stranger = await _user(
        session,
        permissions=("transactions:create", "transactions:read", "transactions:update"),
        role_code="customer",
    )
    source = await _pay_success(session, requester, merchant, branch, till)
    req_service = PaymentRequestService(session)
    created = await req_service.create(
        requester,
        {
            "amount": Decimal("500.00"),
            "currency": "MWK",
            "description": "Share of lunch",
            "source_payment_reference": source.reference,
            "idempotency_key": f"req-{uuid.uuid4().hex}",
        },
    )
    assert created.status is PaymentRequestStatus.PENDING
    same = await req_service.create(
        requester,
        {
            "amount": Decimal("500.00"),
            "currency": "MWK",
            "source_payment_reference": source.reference,
            "idempotency_key": created.idempotency_key,
        },
    )
    assert same.id == created.id

    application = _app(session, stranger)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.get(f"/api/v1/payment-requests/{created.public_identifier}")
        assert denied.status_code == 403
        public = await client.get(f"/api/v1/payment-requests/public/{created.public_identifier}")
        assert public.status_code == 200

    pay_app = _app(session, payer)
    transport = ASGITransport(app=pay_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pay = await client.post(
            f"/api/v1/payment-requests/{created.public_identifier}/pay",
            json={"idempotency_key": f"payreq-{uuid.uuid4().hex}"},
        )
        assert pay.status_code == 201, pay.text
        reference = pay.json()["reference"]
        processed = await client.post(f"/api/v1/payments/{reference}/process")
        assert processed.status_code == 200
        assert processed.json()["status"] == "success"

    await session.refresh(created)
    loaded = await req_service.inspect_public(created.public_identifier)
    assert loaded.status is PaymentRequestStatus.PAID
    assert loaded.payment_reference == reference


@pytest.mark.asyncio
async def test_payment_request_second_pay_reuses_in_flight_payment(session: AsyncSession) -> None:
    merchant, branch, till = await _merchant_graph(session)
    await seed_provider_catalog(session)
    await session.commit()
    requester = await _user(
        session,
        permissions=("transactions:create", "transactions:read", "transactions:update"),
        role_code="customer",
    )
    payer = await _user(
        session,
        permissions=("transactions:create", "transactions:read", "transactions:update"),
        role_code="customer",
    )
    source = await _pay_success(session, requester, merchant, branch, till)
    service = PaymentRequestService(session)

    class AuthorizationStub:
        async def has_permission(self, user: User, _permission: str) -> bool:
            return True

        async def get_user_role(self, user: User):
            return user.role

    service._payments._authorization = AuthorizationStub()
    created = await service.create(
        requester,
        {
            "amount": Decimal("500.00"),
            "currency": "MWK",
            "source_payment_reference": source.reference,
            "idempotency_key": f"req-{uuid.uuid4().hex}",
        },
    )
    first = await service.pay(payer, created.public_identifier, {"idempotency_key": f"pay-{uuid.uuid4().hex}"})
    second = await service.pay(payer, created.public_identifier, {"idempotency_key": f"pay-{uuid.uuid4().hex}"})
    assert first.id == second.id
    assert first.reference == second.reference


@pytest.mark.asyncio
async def test_payment_request_cancel_and_expire(session: AsyncSession) -> None:
    merchant, branch, till = await _merchant_graph(session)
    requester = await _user(
        session,
        permissions=("transactions:create", "transactions:read", "transactions:update"),
        role_code="customer",
    )
    source = await _pay_success(session, requester, merchant, branch, till)
    service = PaymentRequestService(session)
    created = await service.create(
        requester,
        {
            "amount": Decimal("200.00"),
            "currency": "MWK",
            "source_payment_reference": source.reference,
            "idempotency_key": f"req-{uuid.uuid4().hex}",
        },
    )
    cancelled = await service.cancel(requester, created.public_identifier)
    assert cancelled.status is PaymentRequestStatus.CANCELLED

    expiring = await service.create(
        requester,
        {
            "amount": Decimal("200.00"),
            "currency": "MWK",
            "source_payment_reference": source.reference,
            "expires_in_seconds": 60,
            "idempotency_key": f"req-{uuid.uuid4().hex}",
        },
    )
    expiring.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await session.commit()
    loaded = await service.inspect_public(expiring.public_identifier)
    assert loaded.status is PaymentRequestStatus.EXPIRED


@pytest.mark.asyncio
async def test_bill_split_amounts_and_expired_split(session: AsyncSession) -> None:
    merchant, branch, till = await _merchant_graph(session)
    creator = await _user(
        session,
        permissions=("transactions:create", "transactions:read", "transactions:update"),
        role_code="customer",
    )
    source = await _pay_success(session, creator, merchant, branch, till)
    service = PaymentRequestService(session)
    with pytest.raises(Exception):
        await service.create_split(
            creator,
            {
                "total_amount": Decimal("30000.00"),
                "currency": "MWK",
                "source_payment_reference": source.reference,
                "idempotency_key": f"split-{uuid.uuid4().hex}",
                "participants": [
                    {"amount": Decimal("10000.00")},
                    {"amount": Decimal("10000.00")},
                ],
            },
        )
    split = await service.create_split(
        creator,
        {
            "total_amount": Decimal("30000.00"),
            "currency": "MWK",
            "source_payment_reference": source.reference,
            "idempotency_key": f"split-{uuid.uuid4().hex}",
            "participants": [
                {"amount": Decimal("10000.00"), "label": "A"},
                {"amount": Decimal("10000.00"), "label": "B"},
                {"amount": Decimal("10000.00"), "label": "C"},
            ],
        },
    )
    assert len(split.requests) == 3
    assert {row.amount for row in split.requests} == {Decimal("10000.00")}
    for row in split.requests:
        row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await session.commit()
    for row in split.requests:
        loaded = await service.inspect_public(row.public_identifier)
        assert loaded.status is PaymentRequestStatus.EXPIRED


@pytest.mark.asyncio
async def test_favorites_receipts_notifications_search_support(session: AsyncSession) -> None:
    merchant, branch, till = await _merchant_graph(session)
    customer = await _user(
        session,
        permissions=("transactions:create", "transactions:read", "transactions:update"),
        role_code="customer",
    )
    other = await _user(
        session,
        permissions=("transactions:create", "transactions:read"),
        role_code="customer",
    )
    payment = await _pay_success(session, customer, merchant, branch, till)
    customer_service = CustomerService(session, jwt_config=_jwt(), password_hasher=PasswordHasher())
    first = await customer_service.add_favorite(customer, merchant.id)
    second = await customer_service.add_favorite(customer, merchant.id)
    assert first.id == second.id
    others = await customer_service.list_merchants(other)
    assert others == []
    merchants = await customer_service.list_merchants(customer)
    assert merchants[0]["merchant_id"] == merchant.id
    await customer_service.remove_favorite(customer, merchant.id)
    remaining = await session.scalar(
        select(MerchantFavorite).where(MerchantFavorite.user_id == customer.id)
    )
    assert remaining is None

    pay_service = PaymentService(session)

    class AuthorizationStub:
        async def has_permission(self, user: User, _permission: str) -> bool:
            return True

        async def get_user_role(self, user: User):
            return user.role

    pay_service._authorization = AuthorizationStub()
    receipt = await pay_service.get_receipt(customer, payment.reference)
    assert receipt["title"] == "PAYMENT RECEIPT"
    assert receipt["reference"] == payment.reference
    with pytest.raises(Exception):
        await pay_service.get_receipt(other, payment.reference)

    filtered = await pay_service.list_my_payments(customer, status="success", query_text="Chikondi")
    assert any(row.reference == payment.reference for row in filtered)
    empty = await pay_service.list_my_payments(other, status="success")
    assert empty == []

    notes, unread = await NotificationService(session).list_for_user(customer)
    assert unread >= 1
    assert any(item.payment_reference == payment.reference for item in notes)
    other_notes, other_unread = await NotificationService(session).list_for_user(other)
    assert other_notes == []
    assert other_unread == 0
    if notes:
        with pytest.raises(Exception):
            await NotificationService(session).mark_read(other, notes[0].id)

    support = SupportService(session)
    ticket = await support.create(
        customer,
        {
            "category": "payment_problem",
            "subject": "Payment question",
            "message": "Need help with this payment",
            "payment_reference": payment.reference,
        },
    )
    assert ticket.payment_reference == payment.reference
    with pytest.raises(Exception):
        await support.get_visible(other, ticket.public_identifier)

    insights = await customer_service.insights(customer)
    assert insights["payment_count"] >= 1
    assert insights["most_used_merchants"][0]["merchant_name"] == "Chikondi Shop"


@pytest.mark.asyncio
async def test_openapi_includes_m015_paths(session: AsyncSession) -> None:
    customer = await _user(session, permissions=("transactions:read",), role_code="customer")
    application = _app(session, customer)
    paths = application.openapi()["paths"]
    assert "/api/v1/customers/register" in paths
    assert "/api/v1/payments/{reference}/repeat" in paths
    assert "/api/v1/payment-requests" in paths
    assert "/api/v1/notifications" in paths
    assert "/api/v1/support-requests" in paths
