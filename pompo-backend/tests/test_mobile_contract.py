"""M012 mobile API contract — customer pay-from-QR and activity lists."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
from app.api.v1.payments import (
    get_payment_service,
    get_qr_service as get_payment_qr_service,
    router as payments_router,
)
from app.api.v1.qr import get_qr_service, router as qr_router
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
from app.payments.catalog import seed_provider_catalog
from app.services.payment import PaymentService
from app.services.qr import QRService


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
) -> User:
    permission_models = [await _permission(session, code) for code in permissions]
    role = Role(code=f"{role_code}_{uuid.uuid4().hex}", name=role_code)
    actor = User(
        merchant=merchant,
        branch=branch,
        role=role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name=role_code,
        hashed_password="hash",
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


def _app(session: AsyncSession, actor: User) -> FastAPI:
    application = FastAPI()
    application.include_router(qr_router, prefix="/api/v1")
    application.include_router(payments_router, prefix="/api/v1")

    class AuthorizationStub:
        async def require_permission(self, user: User, _permission: str) -> User:
            return user

        async def has_permission(self, user: User, _permission: str) -> bool:
            return True

        async def get_user_role(self, user: User):
            return user.role

    qr_service = QRService(session)
    payment_service = PaymentService(session)
    stub = AuthorizationStub()
    qr_service._authorization = stub
    payment_service._authorization = stub

    application.dependency_overrides[deps.get_current_user] = lambda: actor
    application.dependency_overrides[deps.get_authorization_service] = lambda: stub
    application.dependency_overrides[get_qr_service] = lambda: qr_service
    application.dependency_overrides[get_payment_qr_service] = lambda: qr_service
    application.dependency_overrides[get_payment_service] = lambda: payment_service
    return application


@pytest.mark.asyncio
async def test_customer_cannot_create_direct_pos_payment(session: AsyncSession) -> None:
    merchant, branch, till = await _merchant_graph(session)
    customer = await _user(
        session,
        permissions=("transactions:create", "transactions:read"),
        role_code="customer",
    )
    await seed_provider_catalog(session)
    await session.commit()

    application = _app(session, customer)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/payments",
            json={
                "merchant_id": str(merchant.id),
                "branch_id": str(branch.id),
                "till_id": str(till.id),
                "amount": "25.00",
                "currency": "MWK",
                "payment_method": "mobile_money",
                "provider_code": "simulated",
                "idempotency_key": "pos-blocked",
            },
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_customer_cannot_list_merchant_payments(session: AsyncSession) -> None:
    await _merchant_graph(session)
    customer = await _user(session, permissions=("transactions:read",), role_code="customer")
    application = _app(session, customer)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/payments")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_sandbox_dynamic_qr_customer_pay_and_activity(session: AsyncSession) -> None:
    merchant, branch, till = await _merchant_graph(session)
    owner = await _user(
        session,
        permissions=(
            "qr:create",
            "qr:read",
            "transactions:create",
            "transactions:read",
            "transactions:update",
        ),
        merchant=merchant,
        branch=branch,
        role_code="merchant_owner",
    )
    customer = await _user(
        session,
        permissions=(
            "transactions:create",
            "transactions:read",
            "transactions:update",
        ),
        role_code="customer",
    )
    stranger = await _user(
        session,
        permissions=("transactions:read",),
        role_code="customer",
    )
    await seed_provider_catalog(session)
    await session.commit()

    owner_app = _app(session, owner)
    customer_app = _app(session, customer)
    stranger_app = _app(session, stranger)

    async with AsyncClient(
        transport=ASGITransport(app=owner_app), base_url="http://test"
    ) as merchant_client:
        qr_resp = await merchant_client.post(
            "/api/v1/qr/dynamic",
            json={
                "merchant_id": str(merchant.id),
                "branch_id": str(branch.id),
                "till_id": str(till.id),
                "amount": "150.00",
                "currency": "MWK",
                "payment_method": "mobile_money",
                "provider_code": "simulated",
                "idempotency_key": "mobile-dyn-1",
            },
        )
        assert qr_resp.status_code == 201, qr_resp.text
        qr_body = qr_resp.json()
        payload = qr_body["encoded_payload"]
        public_id = qr_body["public_identifier"]

        listed = await merchant_client.get("/api/v1/qr")
        assert listed.status_code == 200
        assert any(item["public_identifier"] == public_id for item in listed.json())

    async with AsyncClient(
        transport=ASGITransport(app=customer_app), base_url="http://test"
    ) as pay_client:
        inspect = await pay_client.get(f"/api/v1/qr/{public_id}")
        assert inspect.status_code == 200
        preview = inspect.json()
        assert preview["merchant_name"] == "Chikondi Shop"
        assert preview["amount"] == "150.00"
        assert preview["qr_type"] == "dynamic"

        initiated = await pay_client.post(
            "/api/v1/payments/from-qr",
            json={
                "payload": payload,
                "idempotency_key": "customer-pay-1",
            },
        )
        assert initiated.status_code == 201, initiated.text
        payment = initiated.json()
        assert payment["amount"] == "150.00"
        assert payment["status"] == TransactionStatus.PENDING.value
        reference = payment["reference"]

        override = await pay_client.post(
            "/api/v1/payments/from-qr",
            json={
                "payload": payload,
                "idempotency_key": "customer-pay-override",
                "amount": "999.00",
            },
        )
        assert override.status_code == 422

        replay = await pay_client.post(
            "/api/v1/payments/from-qr",
            json={"payload": payload, "idempotency_key": "customer-pay-1"},
        )
        assert replay.status_code == 201
        assert replay.json()["reference"] == reference

        processed = await pay_client.post(f"/api/v1/payments/{reference}/process")
        assert processed.status_code == 200, processed.text
        assert processed.json()["status"] == TransactionStatus.SUCCESS.value

        mine = await pay_client.get("/api/v1/payments/mine")
        assert mine.status_code == 200
        mine_refs = {row["reference"] for row in mine.json()}
        assert reference in mine_refs
        detail = next(row for row in mine.json() if row["reference"] == reference)
        assert detail["merchant_name"] == "Chikondi Shop"

        named = await pay_client.get(f"/api/v1/payments/{reference}")
        assert named.status_code == 200
        assert named.json()["merchant_name"] == "Chikondi Shop"

    async with AsyncClient(
        transport=ASGITransport(app=stranger_app), base_url="http://test"
    ) as other_client:
        denied = await other_client.get(f"/api/v1/payments/{reference}")
        assert denied.status_code == 403

    async with AsyncClient(
        transport=ASGITransport(app=owner_app), base_url="http://test"
    ) as merchant_client:
        activity = await merchant_client.get("/api/v1/payments")
        assert activity.status_code == 200
        assert any(row["reference"] == reference for row in activity.json())


@pytest.mark.asyncio
async def test_static_qr_customer_enters_amount(session: AsyncSession) -> None:
    merchant, branch, till = await _merchant_graph(session)
    owner = await _user(
        session,
        permissions=("qr:create", "transactions:create", "transactions:read", "transactions:update"),
        merchant=merchant,
        branch=branch,
    )
    customer = await _user(
        session,
        permissions=("transactions:create", "transactions:read", "transactions:update"),
    )
    await seed_provider_catalog(session)
    await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=_app(session, owner)), base_url="http://test"
    ) as merchant_client:
        qr_resp = await merchant_client.post(
            "/api/v1/qr/static",
            json={
                "merchant_id": str(merchant.id),
                "branch_id": str(branch.id),
                "till_id": str(till.id),
            },
        )
        assert qr_resp.status_code == 201
        payload = qr_resp.json()["encoded_payload"]

    async with AsyncClient(
        transport=ASGITransport(app=_app(session, customer)), base_url="http://test"
    ) as pay_client:
        initiated = await pay_client.post(
            "/api/v1/payments/from-qr",
            json={
                "payload": payload,
                "idempotency_key": "static-customer-1",
                "amount": "40.00",
                "payment_method": "mobile_money",
                "provider_code": "simulated",
            },
        )
        assert initiated.status_code == 201, initiated.text
        assert initiated.json()["amount"] == "40.00"
        processed = await pay_client.post(
            f"/api/v1/payments/{initiated.json()['reference']}/process"
        )
        assert processed.json()["status"] == TransactionStatus.SUCCESS.value
        assert Decimal(processed.json()["amount"]) == Decimal("40.00")
