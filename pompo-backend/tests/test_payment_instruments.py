"""Payment instruments — saved methods, not a wallet."""

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
from app.api.v1.instruments import get_instrument_service, router as instruments_router
from app.api.v1.payments import (
    get_payment_service,
    get_qr_service as get_payment_qr_service,
    router as payments_router,
)
from app.api.v1.qr import get_qr_service, router as qr_router
from app.models import AuditLog, Branch, Merchant, PaymentInstrument, Permission, Role, RolePermission, Till, User
from app.models.base import Base
from app.models.enums import PaymentInstrumentStatus, ProviderCode
from app.payments.catalog import seed_provider_catalog
from app.payments.instrument_tokens import digest_token, reject_secret_fields
from app.services.instrument import PaymentInstrumentService
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


async def _seed(session: AsyncSession) -> tuple[Merchant, Branch, Till]:
    merchant = Merchant(
        name="Chez Ntemba",
        contact_email=f"{uuid.uuid4().hex}@example.com",
        contact_phone="+265991000000",
    )
    branch = Branch(merchant=merchant, name="Lilongwe")
    till = Till(branch=branch, code="T1", name="Door")
    session.add_all([merchant, branch, till])
    await seed_provider_catalog(session)
    await session.commit()
    return merchant, branch, till


def _app(session: AsyncSession, actor: User) -> FastAPI:
    application = FastAPI()
    application.include_router(instruments_router, prefix="/api/v1")
    application.include_router(payments_router, prefix="/api/v1")
    application.include_router(qr_router, prefix="/api/v1")

    class AuthorizationStub:
        async def require_permission(self, user: User, _permission: str) -> User:
            return user

        async def has_permission(self, user: User, _permission: str) -> bool:
            return True

    application.dependency_overrides[deps.get_current_user] = lambda: actor
    application.dependency_overrides[deps.get_authorization_service] = lambda: AuthorizationStub()
    application.dependency_overrides[get_instrument_service] = lambda: PaymentInstrumentService(session)
    application.dependency_overrides[get_payment_service] = lambda: PaymentService(session)
    application.dependency_overrides[get_qr_service] = lambda: QRService(session)
    application.dependency_overrides[get_payment_qr_service] = lambda: QRService(session)
    return application


async def _enroll_airtel(client: AsyncClient, *, msisdn: str = "0881234321") -> dict:
    response = await client.post(
        "/api/v1/payment-methods",
        json={
            "provider_code": "simulated",
            "instrument_type": "mobile_money",
            "msisdn": msisdn,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_reject_secret_fields() -> None:
    with pytest.raises(ValueError, match="Provider secrets"):
        reject_secret_fields({"pin": "0000", "msisdn": "0881234321"})
    digest = digest_token("secret", "simtok_abc")
    assert digest != "simtok_abc"
    assert len(digest) == 64


@pytest.mark.asyncio
async def test_enroll_list_default_revoke_and_no_secret_leak(session: AsyncSession) -> None:
    await _seed(session)
    customer = await _user(session, permissions=("transactions:create",), role_code="customer")
    application = _app(session, customer)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        catalog = await client.get("/api/v1/payment-methods/catalog")
        assert catalog.status_code == 200
        airtel_live = next(item for item in catalog.json() if item["provider_code"] == "airtel_money")
        assert airtel_live["available"] is False
        tnm_catalog = next(item for item in catalog.json() if item["provider_code"] == "tnm_mpamba")
        assert tnm_catalog["available"] is False
        assert tnm_catalog["authorization_state"] == "unsupported"
        assert "live HTTP contract is not in POMPO" in tnm_catalog["reason"]

        forbidden = await client.post(
            "/api/v1/payment-methods",
            json={"provider_code": "simulated", "instrument_type": "mobile_money", "msisdn": "08811", "pin": "1234"},
        )
        assert forbidden.status_code == 422

        unavailable = await client.post(
            "/api/v1/payment-methods",
            json={"provider_code": "airtel_money", "instrument_type": "mobile_money", "msisdn": "0881234321"},
        )
        assert unavailable.status_code == 422

        tnm_enroll = await client.post(
            "/api/v1/payment-methods",
            json={"provider_code": "tnm_mpamba", "instrument_type": "mobile_money", "msisdn": "0881234321"},
        )
        assert tnm_enroll.status_code == 422
        assert "Saved Mpamba" in tnm_enroll.json()["detail"] or "not available" in tnm_enroll.json()["detail"].lower()

        method = await _enroll_airtel(client)
        assert method["is_sandbox"] is True
        assert method["display_name"] == "Test Airtel Money"
        assert "••" in method["masked_identifier"]
        assert method["is_default"] is True
        assert "token_reference" not in method
        assert "pin" not in method

        visa = await client.post(
            "/api/v1/payment-methods",
            json={"provider_code": "simulated", "instrument_type": "visa", "card_last4": "4242"},
        )
        assert visa.status_code == 201, visa.text
        assert visa.json()["masked_identifier"] == "•••• 4242"
        assert visa.json()["display_name"] == "Sandbox Visa"

        listed = await client.get("/api/v1/payment-methods")
        assert listed.status_code == 200
        assert len(listed.json()) == 2

        defaulted = await client.post(f"/api/v1/payment-methods/{visa.json()['id']}/default")
        assert defaulted.status_code == 200
        assert defaulted.json()["is_default"] is True
        refreshed = await client.get(f"/api/v1/payment-methods/{method['id']}")
        assert refreshed.json()["is_default"] is False

        revoked = await client.delete(f"/api/v1/payment-methods/{method['id']}")
        assert revoked.status_code == 200
        assert revoked.json()["status"] == "revoked"
        remaining = await client.get("/api/v1/payment-methods")
        ids = {row["id"] for row in remaining.json()}
        assert method["id"] not in ids

    stored = await session.scalar(
        select(PaymentInstrument).where(PaymentInstrument.public_identifier == method["id"])
    )
    assert stored is not None
    assert stored.token_reference != ""
    assert not stored.token_reference.startswith("simtok_")
    assert stored.status is PaymentInstrumentStatus.REVOKED

    audits = list((await session.scalars(select(AuditLog))).all())
    blob = str([row.after_state for row in audits])
    assert "pin" not in blob.lower()
    assert "simtok_" not in blob


@pytest.mark.asyncio
async def test_cross_customer_instrument_is_not_found(session: AsyncSession) -> None:
    await _seed(session)
    owner = await _user(session, permissions=("transactions:create",), role_code="owner")
    other = await _user(session, permissions=("transactions:create",), role_code="other")
    owner_app = _app(session, owner)
    async with AsyncClient(transport=ASGITransport(app=owner_app), base_url="http://test") as client:
        method = await _enroll_airtel(client, msisdn="0991882218")
    other_app = _app(session, other)
    async with AsyncClient(transport=ASGITransport(app=other_app), base_url="http://test") as client:
        missing = await client.get(f"/api/v1/payment-methods/{method['id']}")
        assert missing.status_code == 404
        assert missing.json()["detail"] == "Payment method not found"


@pytest.mark.asyncio
async def test_qr_checkout_derives_provider_and_rejects_revoked(
    session: AsyncSession,
) -> None:
    merchant, branch, till = await _seed(session)
    staff = await _user(
        session,
        permissions=("qr:create", "transactions:create", "transactions:update"),
        merchant=merchant,
        branch=branch,
        role_code="cashier",
    )
    customer = await _user(
        session,
        permissions=("transactions:create", "transactions:update", "transactions:read"),
        role_code="customer",
    )
    staff_app = _app(session, staff)
    async with AsyncClient(transport=ASGITransport(app=staff_app), base_url="http://test") as client:
        qr = await client.post(
            "/api/v1/qr/static",
            json={
                "merchant_id": str(merchant.id),
                "branch_id": str(branch.id),
                "till_id": str(till.id),
            },
        )
        assert qr.status_code == 201, qr.text
        payload = qr.json()["encoded_payload"]
        public_id = qr.json()["public_identifier"]

    customer_app = _app(session, customer)
    async with AsyncClient(transport=ASGITransport(app=customer_app), base_url="http://test") as client:
        method = await _enroll_airtel(client)
        mismatch = await client.post(
            "/api/v1/payments/from-qr",
            json={
                "payload": payload,
                "idempotency_key": "pay-mismatch",
                "amount": "18500.00",
                "provider_code": "airtel_money",
                "payment_instrument_id": method["id"],
            },
        )
        assert mismatch.status_code == 422

        paid = await client.post(
            "/api/v1/payments/from-qr",
            json={
                "payload": payload,
                "idempotency_key": "pay-ok",
                "amount": "18500.00",
                "payment_instrument_id": method["id"],
            },
        )
        assert paid.status_code == 201, paid.text
        body = paid.json()
        assert body["payment_instrument_id"] == method["id"]
        assert body["payment_method"] == "mobile_money"
        assert "token_reference" not in body

        processed = await client.post(f"/api/v1/payments/{body['reference']}/process")
        assert processed.status_code == 200, processed.text
        assert processed.json()["status"] == "success"

        replay = await client.post(
            "/api/v1/payments/from-qr",
            json={
                "payload": payload,
                "idempotency_key": "pay-ok",
                "amount": "18500.00",
                "payment_instrument_id": method["id"],
            },
        )
        assert replay.status_code == 201
        assert replay.json()["reference"] == body["reference"]

        wait = await client.get(f"/api/v1/payment-methods/{method['id']}")
        assert wait.json()["last_used_at"] is not None

        await client.delete(f"/api/v1/payment-methods/{method['id']}")
        rejected = await client.post(
            "/api/v1/payments/from-qr",
            json={
                "public_identifier": public_id,
                "idempotency_key": "pay-revoked",
                "amount": "10.00",
                "payment_instrument_id": method["id"],
            },
        )
        assert rejected.status_code == 422

        visa = await client.post(
            "/api/v1/payment-methods",
            json={"provider_code": "simulated", "instrument_type": "visa", "card_last4": "4242"},
        )
        assert visa.status_code == 201
        manual = await client.post(
            "/api/v1/payments/from-qr",
            json={
                "public_identifier": public_id,
                "idempotency_key": "pay-manual",
                "amount": "50.00",
                "payment_instrument_id": visa.json()["id"],
            },
        )
        assert manual.status_code == 201, manual.text
        assert manual.json()["payment_method"] == "card"
        assert manual.json()["payment_instrument_id"] == visa.json()["id"]


@pytest.mark.asyncio
async def test_dynamic_qr_binds_instrument(session: AsyncSession) -> None:
    merchant, branch, till = await _seed(session)
    staff = await _user(
        session,
        permissions=("qr:create", "transactions:create", "transactions:update"),
        merchant=merchant,
        branch=branch,
        role_code="cashier",
    )
    customer = await _user(
        session,
        permissions=("transactions:create", "transactions:update", "transactions:read"),
        role_code="customer",
    )
    staff_app = _app(session, staff)
    async with AsyncClient(transport=ASGITransport(app=staff_app), base_url="http://test") as client:
        qr = await client.post(
            "/api/v1/qr/dynamic",
            json={
                "merchant_id": str(merchant.id),
                "branch_id": str(branch.id),
                "till_id": str(till.id),
                "amount": "100.00",
                "idempotency_key": "dyn-qr-1",
            },
        )
        assert qr.status_code == 201, qr.text
        payload = qr.json()["encoded_payload"]
    customer_app = _app(session, customer)
    async with AsyncClient(transport=ASGITransport(app=customer_app), base_url="http://test") as client:
        method = await _enroll_airtel(client, msisdn="0885554433")
        paid = await client.post(
            "/api/v1/payments/from-qr",
            json={
                "payload": payload,
                "idempotency_key": "dyn-pay-1",
                "payment_instrument_id": method["id"],
            },
        )
        assert paid.status_code == 201, paid.text
        assert paid.json()["payment_instrument_id"] == method["id"]
        processed = await client.post(f"/api/v1/payments/{paid.json()['reference']}/process")
        assert processed.status_code == 200, processed.text
        assert processed.json()["status"] == "success"


@pytest.mark.asyncio
async def test_admin_list_is_masked(session: AsyncSession) -> None:
    await _seed(session)
    admin = await _user(session, permissions=("users:read",), role_code="platform_admin")
    customer = await _user(session, permissions=("transactions:create",), role_code="customer")
    customer_app = _app(session, customer)
    async with AsyncClient(transport=ASGITransport(app=customer_app), base_url="http://test") as client:
        await _enroll_airtel(client, msisdn="0887778899")
    admin_app = _app(session, admin)
    async with AsyncClient(transport=ASGITransport(app=admin_app), base_url="http://test") as client:
        rows = await client.get("/api/v1/payment-methods/admin")
        assert rows.status_code == 200
        assert rows.json()
        row = rows.json()[0]
        assert "token_reference" not in row
        assert "••" in row["masked_identifier"]
        assert row["customer_email"] == customer.email


def test_openapi_includes_payment_method_paths() -> None:
    application = FastAPI()
    application.include_router(instruments_router, prefix="/api/v1")
    application.include_router(payments_router, prefix="/api/v1")
    paths = application.openapi()["paths"]
    assert "/api/v1/payment-methods" in paths
    assert "/api/v1/payment-methods/catalog" in paths
    assert "/api/v1/payment-methods/admin" in paths
    assert "/api/v1/payment-methods/{public_id}" in paths
    assert "/api/v1/payment-methods/{public_id}/default" in paths
    assert "/api/v1/payment-methods/{public_id}/verify" in paths
    post_from_qr = paths["/api/v1/payments/from-qr"]["post"]
    schema_ref = post_from_qr["requestBody"]["content"]["application/json"]["schema"]
    assert schema_ref
