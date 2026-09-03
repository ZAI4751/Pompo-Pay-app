"""Tests for POMPO Universal QR and Zero-Install Web Checkout backend contracts."""

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
from app.api.v1.instruments import get_instrument_service, router as instruments_router
from app.api.v1.payments import get_payment_service, router as payments_router
from app.api.v1.qr import get_qr_service, router as qr_router
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
from app.models.enums import QRStatus, QRType
from app.payments.catalog import seed_provider_catalog
from app.qr.payload import extract_public_identifier
from app.services.instrument import PaymentInstrumentService
from app.services.payment import PaymentService
from app.services.qr import QRInvalidError, QRNotFoundError, QRService


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


async def _get_permission(session: AsyncSession, code: str) -> Permission:
    existing = await session.scalar(select(Permission).where(Permission.code == code))
    if existing is not None:
        return existing
    created = Permission(code=code)
    session.add(created)
    await session.flush()
    return created


async def _actor(
    session: AsyncSession,
    *,
    permissions: tuple[str, ...],
) -> tuple[User, Merchant, Branch, Till]:
    permission_models = [await _get_permission(session, code) for code in permissions]
    role = Role(code=f"qr_role_{uuid.uuid4().hex}", name="QR operator")
    role.permissions.extend(RolePermission(permission=p) for p in permission_models)
    merchant = Merchant(
        name="Lilongwe Fresh Mart",
        contact_email=f"{uuid.uuid4().hex}@freshmart.mw",
        contact_phone="+265991112233",
    )
    branch = Branch(
        merchant=merchant,
        name="City Centre",
    )
    till = Till(
        branch=branch,
        name="Till 01",
        code=f"T01-{uuid.uuid4().hex[:4]}",
    )
    actor = User(
        email=f"{uuid.uuid4().hex}@freshmart.mw",
        hashed_password="hashed_placeholder",
        full_name="Merchant Cashier",
        role=role,
        merchant=merchant,
        branch=branch,
        is_active=True,
    )
    session.add_all([merchant, branch, till, role, actor])
    await session.commit()
    await session.refresh(actor, attribute_names=["merchant", "branch", "role"])
    return actor, merchant, branch, till


async def _customer(
    session: AsyncSession,
) -> User:
    permissions = [
        await _get_permission(session, "transactions:create"),
        await _get_permission(session, "transactions:read"),
    ]
    role = Role(code=f"customer_{uuid.uuid4().hex[:6]}", name="Customer")
    role.permissions.extend(RolePermission(permission=p) for p in permissions)
    user = User(
        email=f"customer_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashed_placeholder",
        full_name="Alice Phiri",
        phone="+265888123456",
        role=role,
        is_active=True,
    )
    session.add_all([role, user])
    await session.commit()
    await session.refresh(user, attribute_names=["role"])
    return user


def test_extract_public_identifier_utility() -> None:
    # Bare public ID
    assert extract_public_identifier("POMPO-ABC12345") == "POMPO-ABC12345"
    assert extract_public_identifier("   POMPO-XYZ98765  ") == "POMPO-XYZ98765"

    # Universal HTTPS URL
    assert extract_public_identifier("https://pay.pompo.mw/p/POMPO-ABC12345") == "POMPO-ABC12345"
    assert extract_public_identifier("https://pay.pompo.mw/p/POMPO-ABC12345/") == "POMPO-ABC12345"
    assert extract_public_identifier("https://pay.pompo.mw/p/POMPO-ABC12345?amount=10") == "POMPO-ABC12345"
    assert extract_public_identifier("http://localhost:3000/p/POMPO-ABC12345") == "POMPO-ABC12345"
    assert extract_public_identifier("/p/POMPO-ABC12345") == "POMPO-ABC12345"

    # Internal signed payload
    assert (
        extract_public_identifier("POMPO:1:static:POMPO-ABC12345:1234567890123456789012")
        == "POMPO-ABC12345"
    )

    # Invalid / empty
    assert extract_public_identifier("") is None
    assert extract_public_identifier("   ") is None
    assert extract_public_identifier("https://example.com/other/path") is None
    assert extract_public_identifier("not_valid_code") is None


@pytest.mark.asyncio
async def test_universal_qr_creation_and_inspection(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "qr:read", "transactions:create")
    )
    service = QRService(session)

    # 1. Static QR creation
    static_qr = await service.create_static_qr(
        actor,
        {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
    )
    assert static_qr.public_identifier
    assert static_qr.payload.startswith("POMPO:1:static:")

    # 2. Inspect static QR via service with URL
    inspected_direct = await service.inspect_qr(static_qr.public_identifier)
    assert inspected_direct.merchant.name == "Lilongwe Fresh Mart"

    inspected_via_url = await service.inspect_qr(
        f"https://pay.pompo.mw/p/{static_qr.public_identifier}"
    )
    assert inspected_via_url.id == static_qr.id

    # 3. Dynamic QR creation
    dynamic_qr = await service.create_dynamic_qr(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("15000.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated",
            "idempotency_key": f"dyn-test-{uuid.uuid4().hex}",
            "expires_in_seconds": 900,
        },
    )
    assert dynamic_qr.amount == Decimal("15000.00")

    inspected_dyn = await service.inspect_qr(
        f"https://pay.pompo.mw/p/{dynamic_qr.public_identifier}"
    )
    assert inspected_dyn.amount == Decimal("15000.00")
    assert inspected_dyn.currency == "MWK"


@pytest.mark.asyncio
async def test_universal_qr_api_endpoints(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "qr:read", "qr:revoke", "transactions:create")
    )
    customer = await _customer(session)
    service = QRService(session)
    instrument_service = PaymentInstrumentService(session)
    payment_service = PaymentService(session)

    app = FastAPI()
    app.include_router(qr_router, prefix="/api/v1")
    app.include_router(payments_router, prefix="/api/v1")
    app.include_router(instruments_router, prefix="/api/v1")

    async def override_session():
        yield session

    app.dependency_overrides[deps.get_db_session] = override_session
    app.dependency_overrides[get_qr_service] = lambda: service
    app.dependency_overrides[get_instrument_service] = lambda: instrument_service
    app.dependency_overrides[get_payment_service] = lambda: payment_service

    # Create static & dynamic QRs
    static_qr = await service.create_static_qr(
        actor,
        {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
    )
    dynamic_qr = await service.create_dynamic_qr(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("7500.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated",
            "idempotency_key": f"dyn-api-{uuid.uuid4().hex}",
            "expires_in_seconds": 600,
        },
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Public catalog inspection without token
        cat_resp = await client.get("/api/v1/payment-methods/catalog")
        assert cat_resp.status_code == 200
        assert len(cat_resp.json()) > 0

        # Public inspection of static QR
        static_resp = await client.get(f"/api/v1/qr/{static_qr.public_identifier}")
        assert static_resp.status_code == 200
        static_data = static_resp.json()
        assert static_data["merchant_name"] == "Lilongwe Fresh Mart"
        assert static_data["qr_type"] == "static"
        assert static_data["amount"] is None
        assert static_data["payment_url"] == f"https://pay.pompo.mw/p/{static_qr.public_identifier}"

        # Public inspection of dynamic QR
        dyn_resp = await client.get(f"/api/v1/qr/{dynamic_qr.public_identifier}")
        assert dyn_resp.status_code == 200
        dyn_data = dyn_resp.json()
        assert dyn_data["merchant_name"] == "Lilongwe Fresh Mart"
        assert dyn_data["qr_type"] == "dynamic"
        assert dyn_data["amount"] == "7500.00"
        assert dyn_data["currency"] == "MWK"
        assert dyn_data["payment_url"] == f"https://pay.pompo.mw/p/{dynamic_qr.public_identifier}"

        # Public inspection of unknown QR -> 404
        unknown_resp = await client.get("/api/v1/qr/POMPO-NOTFOUND99")
        assert unknown_resp.status_code == 404

        # Inspection with allow_inactive on revoked QR
        await service.revoke_qr(actor, static_qr.public_identifier)

        # Standard inspect raises 422
        active_only = await client.get(f"/api/v1/qr/{static_qr.public_identifier}")
        assert active_only.status_code == 422

        # Allow inactive inspect returns 200 with status=revoked
        inactive_resp = await client.get(
            f"/api/v1/qr/{static_qr.public_identifier}?allow_inactive=true"
        )
        assert inactive_resp.status_code == 200
        assert inactive_resp.json()["status"] == "revoked"
        assert inactive_resp.json()["merchant_name"] == "Lilongwe Fresh Mart"


@pytest.mark.asyncio
async def test_payment_from_universal_qr_url(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    actor, merchant, branch, till = await _actor(
        session,
        permissions=(
            "qr:create",
            "qr:read",
            "qr:revoke",
            "transactions:create",
            "transactions:read",
            "transactions:update",
        ),
    )
    customer = await _customer(session)
    qr_service = QRService(session)
    payment_service = PaymentService(session)

    # 1. Dynamic QR: Pay using canonical HTTPS URL as payload
    dyn_qr = await qr_service.create_dynamic_qr(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("12500.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated",
            "idempotency_key": f"dyn-pay-{uuid.uuid4().hex}",
            "expires_in_seconds": 600,
        },
    )

    universal_url = f"https://pay.pompo.mw/p/{dyn_qr.public_identifier}"

    # Payment initiated with universal URL as payload
    txn = await qr_service.initiate_payment_from_qr(
        customer,
        {
            "payload": universal_url,
            "idempotency_key": f"pay-dyn-url-{uuid.uuid4().hex}",
        },
    )
    assert txn.amount == Decimal("12500.00")
    assert txn.currency == "MWK"
    assert txn.reference.startswith("PMP-")

    # 2. Server-authoritative amount: Reject customer override on dynamic QR
    with pytest.raises(QRInvalidError, match="cannot be modified for dynamic QR"):
        await qr_service.initiate_payment_from_qr(
            customer,
            {
                "public_identifier": dyn_qr.public_identifier,
                "amount": Decimal("5000.00"),  # Client attempting to pay less
                "idempotency_key": f"tamper-amount-{uuid.uuid4().hex}",
            },
        )

    # 3. Static QR: Pay using public_identifier with custom amount
    static_qr = await qr_service.create_static_qr(
        actor,
        {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
    )

    static_txn = await qr_service.initiate_payment_from_qr(
        customer,
        {
            "public_identifier": static_qr.public_identifier,
            "amount": Decimal("4200.00"),
            "idempotency_key": f"pay-static-{uuid.uuid4().hex}",
        },
    )
    assert static_txn.amount == Decimal("4200.00")
    assert static_txn.currency == "MWK"

    # Static payment requires amount
    with pytest.raises(QRInvalidError, match="Amount is required"):
        await qr_service.initiate_payment_from_qr(
            customer,
            {
                "public_identifier": static_qr.public_identifier,
                "idempotency_key": f"static-no-amt-{uuid.uuid4().hex}",
            },
        )

    # 4. Expired QR rejects payment
    expired_qr = await qr_service.create_dynamic_qr(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("1000.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated",
            "idempotency_key": f"dyn-exp-{uuid.uuid4().hex}",
            "expires_in_seconds": 60,
        },
    )
    expired_qr.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await session.commit()
    with pytest.raises(QRInvalidError, match="expired"):
        await qr_service.initiate_payment_from_qr(
            customer,
            {
                "payload": f"https://pay.pompo.mw/p/{expired_qr.public_identifier}",
                "idempotency_key": f"after-exp-{uuid.uuid4().hex}",
            },
        )

    # 5. Revoked QR rejects payment
    revoked_qr = await qr_service.create_dynamic_qr(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("2000.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated",
            "idempotency_key": f"dyn-rev-{uuid.uuid4().hex}",
            "expires_in_seconds": 600,
        },
    )
    await qr_service.revoke_qr(actor, revoked_qr.public_identifier)
    with pytest.raises(QRInvalidError, match="revoked"):
        await qr_service.initiate_payment_from_qr(
            customer,
            {
                "payload": f"https://pay.pompo.mw/p/{revoked_qr.public_identifier}",
                "idempotency_key": f"after-rev-{uuid.uuid4().hex}",
            },
        )

    # 6. Consumed dynamic QR rejects duplicate payment
    consume_qr = await qr_service.create_dynamic_qr(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("3000.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated",
            "idempotency_key": f"dyn-consume-{uuid.uuid4().hex}",
            "expires_in_seconds": 600,
        },
    )
    consume_txn = await qr_service.initiate_payment_from_qr(
        customer,
        {
            "public_identifier": consume_qr.public_identifier,
            "idempotency_key": f"consume-1-{uuid.uuid4().hex}",
        },
    )
    await payment_service.process_payment(actor, consume_txn.reference)
    await session.refresh(consume_qr)
    assert consume_qr.status is QRStatus.CONSUMED

    with pytest.raises(QRInvalidError, match="consumed|expired|revoked|no longer available"):
        await qr_service.initiate_payment_from_qr(
            customer,
            {
                "public_identifier": consume_qr.public_identifier,
                "idempotency_key": f"consume-2-{uuid.uuid4().hex}",
            },
        )

    # 7. End-to-end Merchant & Admin visibility
    # Merchant can list and see the transaction
    merchant_txns = await payment_service.list_merchant_payments(actor)
    assert any(p.reference == txn.reference for p in merchant_txns)
    assert any(p.reference == static_txn.reference for p in merchant_txns)

    # Transaction details contain correct merchant and amount
    detail = await payment_service.get_payment(actor, txn.reference)
    assert detail.amount == Decimal("12500.00")
    assert detail.merchant_id == merchant.id
    assert detail.till_id == till.id
