"""M009 QR payment tests — payload, service, API, and security."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
from app.api.v1.payments import get_payment_service, router as payments_router
from app.api.v1.qr import get_qr_service, router as qr_router
from app.models import (
    Branch,
    Merchant,
    PaymentProvider,
    Permission,
    Role,
    RolePermission,
    Till,
    Transaction,
    User,
)
from app.models.base import Base
from app.models.enums import ProviderCode, QRStatus, QRType, TransactionStatus
from app.payments.catalog import seed_provider_catalog
from app.qr.payload import QRPayloadError, QRPayloadService
from app.services.payment import PaymentService
from app.services.qr import QRForbiddenError, QRInvalidError, QRService


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


async def _actor(
    session: AsyncSession,
    *,
    permissions: tuple[str, ...],
    merchant: Merchant | None = None,
    branch: Branch | None = None,
) -> tuple[User, Merchant, Branch, Till]:
    permission_models = [Permission(code=code) for code in permissions]
    role = Role(code=f"qr_role_{uuid.uuid4().hex}", name="QR operator")
    role.permissions.extend(RolePermission(permission=permission) for permission in permission_models)
    if merchant is None:
        merchant = Merchant(
            name="QR Merchant",
            contact_email=f"{uuid.uuid4().hex}@example.com",
            contact_phone="+265991000000",
        )
    if branch is None:
        branch = Branch(merchant=merchant, name="Main Branch")
    till = Till(branch=branch, code="QR-1", name="QR Counter")
    actor = User(
        merchant=merchant,
        branch=branch,
        role=role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="QR Operator",
        hashed_password="hash",
        is_active=True,
    )
    provider = PaymentProvider(code=ProviderCode.SIMULATED, display_name="Simulated")
    session.add_all([*permission_models, role, merchant, branch, till, actor, provider])
    await session.commit()
    return actor, merchant, branch, till


class TestQRPayload:
    def test_static_encode_parse_roundtrip(self) -> None:
        service = QRPayloadService("test-secret-key-minimum-32-characters-long")
        encoded = service.encode_static(public_identifier="QRABC123456789")
        parsed = service.parse(encoded)
        assert parsed.qr_type is QRType.STATIC
        assert parsed.public_identifier == "QRABC123456789"
        assert parsed.version == 1

    def test_dynamic_encode_parse_roundtrip(self) -> None:
        service = QRPayloadService("test-secret-key-minimum-32-characters-long")
        expires = datetime.now(UTC) + timedelta(minutes=15)
        encoded = service.encode_dynamic(
            public_identifier="QRDYN123456789",
            amount=Decimal("150.75"),
            currency="MWK",
            expires_at=expires,
            payment_reference="PMP-REF123",
        )
        parsed = service.parse(encoded)
        assert parsed.qr_type is QRType.DYNAMIC
        assert parsed.amount == Decimal("150.75")
        assert parsed.currency == "MWK"
        assert parsed.payment_reference == "PMP-REF123"

    def test_rejects_invalid_signature(self) -> None:
        service = QRPayloadService("test-secret-key-minimum-32-characters-long")
        encoded = service.encode_static(public_identifier="QRABC123456789")
        tampered = encoded[:-1] + ("A" if encoded[-1] != "A" else "B")
        with pytest.raises(QRPayloadError, match="Invalid QR signature"):
            service.parse(tampered)

    def test_rejects_malformed_payload(self) -> None:
        service = QRPayloadService("test-secret-key-minimum-32-characters-long")
        with pytest.raises(QRPayloadError, match="Malformed"):
            service.parse("not-a-pompo-payload")

    def test_rejects_unsupported_version(self) -> None:
        service = QRPayloadService("test-secret-key-minimum-32-characters-long")
        encoded = service.encode_static(public_identifier="QRABC123456789")
        upgraded = encoded.replace(":1:static:", ":99:static:", 1)
        with pytest.raises(QRPayloadError, match="Unsupported QR version"):
            service.parse(upgraded)


@pytest.mark.asyncio
async def test_static_qr_creation_and_revoke(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "qr:read", "qr:revoke", "transactions:create")
    )
    service = QRService(session)
    qr = await service.create_static_qr(
        actor,
        {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
    )
    assert qr.qr_type is QRType.STATIC
    assert qr.status is QRStatus.ACTIVE
    assert qr.payload.startswith("POMPO:1:static:")

    revoked = await service.revoke_qr(actor, qr.public_identifier)
    assert revoked.status is QRStatus.REVOKED
    assert revoked.revoked_at is not None


@pytest.mark.asyncio
async def test_dynamic_qr_links_payment_and_expires(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session,
        permissions=("qr:create", "qr:read", "transactions:create", "transactions:update"),
    )
    service = QRService(session)
    qr = await service.create_dynamic_qr(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("99.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated",
            "idempotency_key": "dyn-qr-1",
            "expires_in_seconds": 60,
        },
    )
    assert qr.qr_type is QRType.DYNAMIC
    assert qr.transaction_id is not None
    assert qr.payment_reference is not None
    assert qr.amount == Decimal("99.00")

    transaction = await session.get(Transaction, qr.transaction_id)
    assert transaction is not None
    assert transaction.status is TransactionStatus.QR_GENERATED


@pytest.mark.asyncio
async def test_static_qr_payment_uses_payment_service(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "transactions:create", "transactions:read")
    )
    qr_service = QRService(session)
    qr = await qr_service.create_static_qr(
        actor,
        {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
    )
    payment = await qr_service.initiate_payment_from_qr(
        actor,
        {
            "payload": qr.payload,
            "idempotency_key": "static-pay-1",
            "amount": Decimal("50.00"),
            "payment_method": "mobile_money",
            "provider_code": "simulated",
        },
    )
    assert payment.amount == Decimal("50.00")
    assert payment.merchant_id == merchant.id
    replay = await qr_service.initiate_payment_from_qr(
        actor,
        {
            "payload": qr.payload,
            "idempotency_key": "static-pay-1",
            "amount": Decimal("50.00"),
            "payment_method": "mobile_money",
            "provider_code": "simulated",
        },
    )
    assert replay.id == payment.id


@pytest.mark.asyncio
async def test_dynamic_qr_rejects_tampered_payload(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "transactions:create")
    )
    qr_service = QRService(session)
    qr = await qr_service.create_dynamic_qr(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("80.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated",
            "idempotency_key": "dyn-tamper",
        },
    )
    tampered = qr.payload.replace("8000", "100", 1)
    with pytest.raises(QRInvalidError, match="Invalid QR signature|does not match"):
        await qr_service.initiate_payment_from_qr(
            actor,
            {"payload": tampered, "idempotency_key": "scan-1"},
        )


@pytest.mark.asyncio
async def test_revoked_static_qr_rejects_payment(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "qr:read", "qr:revoke", "transactions:create")
    )
    qr_service = QRService(session)
    qr = await qr_service.create_static_qr(
        actor,
        {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
    )
    await qr_service.revoke_qr(actor, qr.public_identifier)
    with pytest.raises(QRInvalidError):
        await qr_service.initiate_payment_from_qr(
            actor,
            {
                "payload": qr.payload,
                "idempotency_key": "after-revoke",
                "amount": Decimal("10.00"),
            },
        )


@pytest.mark.asyncio
async def test_tenant_isolation_on_qr_read(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "qr:read")
    )
    other_merchant = Merchant(
        name="Other",
        contact_email=f"{uuid.uuid4().hex}@example.com",
        contact_phone="+265991000001",
    )
    session.add(other_merchant)
    await session.commit()

    other_actor = User(
        merchant=other_merchant,
        role=actor.role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Other",
        hashed_password="hash",
        is_active=True,
    )
    session.add(other_actor)
    await session.commit()

    qr_service = QRService(session)
    qr = await qr_service.create_static_qr(
        actor,
        {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
    )
    with pytest.raises(QRForbiddenError):
        await qr_service.get_qr(other_actor, qr.public_identifier)


@pytest.mark.asyncio
async def test_different_idempotency_keys_create_distinct_static_payments(
    session: AsyncSession,
) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "transactions:create")
    )
    qr_service = QRService(session)
    qr = await qr_service.create_static_qr(
        actor,
        {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
    )
    base = {
        "payload": qr.payload,
        "amount": Decimal("20.00"),
        "payment_method": "mobile_money",
        "provider_code": "simulated",
    }
    first = await qr_service.initiate_payment_from_qr(
        actor, {**base, "idempotency_key": "key-a"}
    )
    second = await qr_service.initiate_payment_from_qr(
        actor, {**base, "idempotency_key": "key-b"}
    )
    assert first.id != second.id


@pytest.mark.asyncio
async def test_qr_api_routes(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session,
        permissions=(
            "qr:create",
            "qr:read",
            "qr:revoke",
            "transactions:create",
            "transactions:update",
        ),
    )
    await seed_provider_catalog(session)
    await session.commit()

    application = FastAPI()
    application.include_router(qr_router, prefix="/api/v1")
    application.include_router(payments_router, prefix="/api/v1")

    class AuthorizationStub:
        async def require_permission(self, user: User, _permission: str) -> User:
            return user

        async def has_permission(self, user: User, _permission: str) -> bool:
            return True

    application.dependency_overrides[deps.get_current_user] = lambda: actor
    application.dependency_overrides[deps.get_authorization_service] = lambda: AuthorizationStub()
    application.dependency_overrides[get_qr_service] = lambda: QRService(session)
    application.dependency_overrides[get_payment_service] = lambda: PaymentService(session)

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        static_resp = await client.post(
            "/api/v1/qr/static",
            json={
                "merchant_id": str(merchant.id),
                "branch_id": str(branch.id),
                "till_id": str(till.id),
            },
        )
        assert static_resp.status_code == 201
        static_body = static_resp.json()
        assert static_body["qr_type"] == "static"
        assert static_body["encoded_payload"].startswith("POMPO:")

        dynamic_resp = await client.post(
            "/api/v1/qr/dynamic",
            json={
                "merchant_id": str(merchant.id),
                "branch_id": str(branch.id),
                "till_id": str(till.id),
                "amount": "45.00",
                "currency": "MWK",
                "payment_method": "mobile_money",
                "provider_code": "simulated",
                "idempotency_key": "api-dyn-1",
            },
        )
        assert dynamic_resp.status_code == 201
        assert dynamic_resp.json()["amount"] == "45.00"

        inspect_resp = await client.get(f"/api/v1/qr/{static_body['public_identifier']}")
        assert inspect_resp.status_code == 200
        assert "merchant_name" in inspect_resp.json()

        revoke_resp = await client.post(
            f"/api/v1/qr/{static_body['public_identifier']}/revoke"
        )
        assert revoke_resp.status_code == 200
        assert revoke_resp.json()["status"] == "revoked"
