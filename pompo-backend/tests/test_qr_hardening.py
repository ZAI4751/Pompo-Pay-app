"""M009 QR hardening — edge cases, concurrency, tamper resistance, exposure."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.qr import get_qr_service, router as qr_router
from app.models import (
    Branch,
    Merchant,
    PaymentProvider,
    Permission,
    QRCode,
    Role,
    RolePermission,
    Till,
    Transaction,
    User,
)
from app.core.config.base import get_settings
from app.models.base import Base
from app.models.enums import ProviderCode, QRStatus, QRType, TransactionStatus
from app.payments.catalog import seed_provider_catalog
from app.qr.payload import QRPayloadService
from app.services.payment import PaymentService
from app.services.qr import QRForbiddenError, QRInvalidError, QRService


@pytest.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite://")
    async with eng.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session


async def _actor(
    session: AsyncSession,
    *,
    permissions: tuple[str, ...],
    merchant: Merchant | None = None,
    branch: Branch | None = None,
) -> tuple[User, Merchant, Branch, Till]:
    permission_models: list[Permission] = []
    for code in permissions:
        existing = await session.scalar(select(Permission).where(Permission.code == code))
        if existing is None:
            existing = Permission(code=code)
            session.add(existing)
        permission_models.append(existing)
    role = Role(code=f"qr_hard_{uuid.uuid4().hex}", name="QR hardening")
    role.permissions.extend(RolePermission(permission=permission) for permission in permission_models)
    if merchant is None:
        merchant = Merchant(
            name="Hard Merchant",
            contact_email=f"{uuid.uuid4().hex}@example.com",
            contact_phone="+265991000000",
        )
    if branch is None:
        branch = Branch(merchant=merchant, name="Hard Branch")
    till = Till(branch=branch, code=f"HARD-{uuid.uuid4().hex[:4]}", name="Hard Counter")
    actor = User(
        merchant=merchant,
        branch=branch,
        role=role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Hard Operator",
        hashed_password="hash",
        is_active=True,
    )
    existing_provider = await session.scalar(select(PaymentProvider).limit(1))
    to_add: list = [role, merchant, branch, till, actor]
    if existing_provider is None:
        to_add.append(
            PaymentProvider(code=ProviderCode.SIMULATED, display_name="Simulated")
        )
    session.add_all(to_add)
    await session.commit()
    return actor, merchant, branch, till


def _dynamic_values(
    merchant: Merchant, branch: Branch, till: Till, *, idempotency_key: str
) -> dict:
    return {
        "merchant_id": merchant.id,
        "branch_id": branch.id,
        "till_id": till.id,
        "amount": Decimal("75.00"),
        "currency": "MWK",
        "payment_method": "mobile_money",
        "provider_code": "simulated",
        "idempotency_key": idempotency_key,
        "expires_in_seconds": 3600,
    }


@pytest.mark.asyncio
async def test_dynamic_qr_create_idempotency_returns_same_qr(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "transactions:create")
    )
    service = QRService(session)
    values = _dynamic_values(merchant, branch, till, idempotency_key="dyn-idem-1")
    first = await service.create_dynamic_qr(actor, values)
    second = await service.create_dynamic_qr(actor, values)
    assert first.id == second.id
    assert first.public_identifier == second.public_identifier
    count = await session.scalar(
        select(func.count()).select_from(QRCode).where(QRCode.transaction_id == first.transaction_id)
    )
    assert count == 1


@pytest.mark.asyncio
async def test_concurrent_dynamic_qr_initiation_same_transaction(db_engine) -> None:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as setup_session:
        actor, merchant, branch, till = await _actor(
            setup_session, permissions=("qr:create", "transactions:create")
        )
        qr_service = QRService(setup_session)
        qr = await qr_service.create_dynamic_qr(
            actor, _dynamic_values(merchant, branch, till, idempotency_key=f"dyn-conc-{uuid.uuid4().hex}")
        )
        payload = qr.payload
        actor_id = actor.id

    async def scan(idempotency_key: str) -> uuid.UUID:
        async with factory() as scan_session:
            user = await scan_session.get(User, actor_id)
            assert user is not None
            service = QRService(scan_session)
            txn = await service.initiate_payment_from_qr(
                user,
                {"payload": payload, "idempotency_key": idempotency_key},
            )
            return txn.id

    txn_a, txn_b = await asyncio.gather(scan("scan-a"), scan("scan-b"))
    assert txn_a == txn_b


@pytest.mark.asyncio
async def test_concurrent_static_qr_same_idempotency_key(db_engine) -> None:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as setup_session:
        actor, merchant, branch, till = await _actor(
            setup_session, permissions=("qr:create", "transactions:create")
        )
        qr = await QRService(setup_session).create_static_qr(
            actor,
            {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
        )
        payload = qr.payload
        actor_id = actor.id
        idempotency_key = f"static-conc-{uuid.uuid4().hex}"

    async def pay() -> uuid.UUID:
        async with factory() as scan_session:
            user = await scan_session.get(User, actor_id)
            assert user is not None
            txn = await QRService(scan_session).initiate_payment_from_qr(
                user,
                {
                    "payload": payload,
                    "idempotency_key": idempotency_key,
                    "amount": Decimal("15.00"),
                    "payment_method": "mobile_money",
                    "provider_code": "simulated",
                },
            )
            return txn.id

    first, second = await asyncio.gather(pay(), pay())
    assert first == second


@pytest.mark.asyncio
async def test_dynamic_qr_rejects_client_amount_override(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "transactions:create")
    )
    service = QRService(session)
    qr = await service.create_dynamic_qr(
        actor, _dynamic_values(merchant, branch, till, idempotency_key="dyn-amt")
    )
    with pytest.raises(QRInvalidError, match="Amount cannot be modified"):
        await service.initiate_payment_from_qr(
            actor,
            {
                "payload": qr.payload,
                "idempotency_key": "override-amt",
                "amount": Decimal("1.00"),
            },
        )


@pytest.mark.asyncio
async def test_dynamic_qr_rejects_tampered_payment_reference(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "transactions:create")
    )
    service = QRService(session)
    qr = await service.create_dynamic_qr(
        actor, _dynamic_values(merchant, branch, till, idempotency_key="dyn-ref")
    )
    payload_service = QRPayloadService(get_settings().secret_key)
    forged = payload_service.encode_dynamic(
        public_identifier=qr.public_identifier,
        amount=qr.amount,
        currency=qr.currency,
        expires_at=qr.expires_at or datetime.now(UTC) + timedelta(hours=1),
        payment_reference="PMP-FORGED",
    )
    with pytest.raises(QRInvalidError, match="tampered|does not match|Invalid QR signature"):
        await service.initiate_payment_from_qr(
            actor, {"payload": forged, "idempotency_key": "ref-tamper"}
        )


@pytest.mark.asyncio
async def test_dynamic_qr_rejects_tampered_currency(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "transactions:create")
    )
    service = QRService(session)
    qr = await service.create_dynamic_qr(
        actor, _dynamic_values(merchant, branch, till, idempotency_key="dyn-cur")
    )
    payload_service = QRPayloadService(get_settings().secret_key)
    forged = payload_service.encode_dynamic(
        public_identifier=qr.public_identifier,
        amount=qr.amount,
        currency="USD",
        expires_at=qr.expires_at or datetime.now(UTC) + timedelta(hours=1),
        payment_reference=qr.payment_reference,
    )
    with pytest.raises(QRInvalidError, match="tampered|currency|does not match"):
        await service.initiate_payment_from_qr(
            actor, {"payload": forged, "idempotency_key": "cur-tamper"}
        )


@pytest.mark.asyncio
async def test_static_qr_rejects_cross_merchant_payload_swap(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "transactions:create")
    )
    service = QRService(session)
    qr_a = await service.create_static_qr(
        actor,
        {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
    )
    payload_service = QRPayloadService(get_settings().secret_key)
    forged = payload_service.encode_static(public_identifier=qr_a.public_identifier)
    # Re-encode binds signature to public_id only; swapping merchant context requires
    # a different public_identifier, which the server resolves independently.
    other_id = "QROTHER1234567"
    while other_id == qr_a.public_identifier:
        other_id = f"QR{uuid.uuid4().hex[:12].upper()}"
    swapped = forged.replace(qr_a.public_identifier, other_id, 1)
    with pytest.raises(QRInvalidError, match="Invalid QR signature|does not match|not found"):
        await service.initiate_payment_from_qr(
            actor,
            {
                "payload": swapped,
                "idempotency_key": "swap-1",
                "amount": Decimal("5.00"),
            },
        )


@pytest.mark.asyncio
async def test_expired_dynamic_qr_rejects_payment(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "transactions:create")
    )
    service = QRService(session)
    qr = await service.create_dynamic_qr(
        actor,
        {
            **_dynamic_values(merchant, branch, till, idempotency_key="dyn-exp"),
            "expires_in_seconds": 60,
        },
    )
    qr.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await session.commit()
    with pytest.raises(QRInvalidError, match="expired"):
        await service.initiate_payment_from_qr(
            actor, {"payload": qr.payload, "idempotency_key": "after-exp"}
        )


@pytest.mark.asyncio
async def test_revoked_dynamic_qr_rejects_payment(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "qr:read", "qr:revoke", "transactions:create")
    )
    service = QRService(session)
    qr = await service.create_dynamic_qr(
        actor, _dynamic_values(merchant, branch, till, idempotency_key="dyn-rev")
    )
    await service.revoke_qr(actor, qr.public_identifier)
    with pytest.raises(QRInvalidError):
        await service.initiate_payment_from_qr(
            actor, {"payload": qr.payload, "idempotency_key": "after-revoke"}
        )


@pytest.mark.asyncio
async def test_consumed_dynamic_qr_after_success(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session,
        permissions=(
            "qr:create",
            "transactions:create",
            "transactions:update",
            "transactions:read",
        ),
    )
    await seed_provider_catalog(session)
    await session.commit()
    qr_service = QRService(session)
    payment_service = PaymentService(session)
    qr = await qr_service.create_dynamic_qr(
        actor, _dynamic_values(merchant, branch, till, idempotency_key="dyn-consume")
    )
    txn = await qr_service.initiate_payment_from_qr(
        actor, {"payload": qr.payload, "idempotency_key": "consume-scan"}
    )
    await payment_service.process_payment(actor, txn.reference)
    await session.refresh(qr)
    assert qr.status is QRStatus.CONSUMED
    assert qr.is_used is True
    with pytest.raises(QRInvalidError, match="no longer available|consumed|expired|revoked"):
        await qr_service.initiate_payment_from_qr(
            actor, {"payload": qr.payload, "idempotency_key": "reuse-scan"}
        )


@pytest.mark.asyncio
async def test_failed_dynamic_qr_marks_consumed(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session,
        permissions=(
            "qr:create",
            "transactions:create",
            "transactions:update",
            "transactions:read",
            "transactions:cancel",
        ),
    )
    qr_service = QRService(session)
    payment_service = PaymentService(session)
    qr = await qr_service.create_dynamic_qr(
        actor, _dynamic_values(merchant, branch, till, idempotency_key="dyn-fail")
    )
    txn = await qr_service.initiate_payment_from_qr(
        actor, {"payload": qr.payload, "idempotency_key": "fail-scan"}
    )
    await payment_service.cancel_payment(actor, txn.reference)
    await session.refresh(qr)
    assert qr.status is QRStatus.CONSUMED
    with pytest.raises(QRInvalidError):
        await qr_service.initiate_payment_from_qr(
            actor, {"payload": qr.payload, "idempotency_key": "fail-reuse"}
        )


@pytest.mark.asyncio
async def test_malformed_payload_rejected(session: AsyncSession) -> None:
    actor, _, _, _ = await _actor(session, permissions=("transactions:create",))
    with pytest.raises(QRInvalidError, match="Malformed"):
        await QRService(session).initiate_payment_from_qr(
            actor, {"payload": "NOT-POMPO", "idempotency_key": "bad"}
        )


@pytest.mark.asyncio
async def test_signature_mismatch_rejected(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "transactions:create")
    )
    service = QRService(session)
    qr = await service.create_static_qr(
        actor,
        {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
    )
    bad_sig = qr.payload[:-1] + ("A" if qr.payload[-1] != "A" else "B")
    with pytest.raises(QRInvalidError, match="Invalid QR signature|does not match"):
        await service.initiate_payment_from_qr(
            actor,
            {
                "payload": bad_sig,
                "idempotency_key": "sig-bad",
                "amount": Decimal("10.00"),
            },
        )


@pytest.mark.asyncio
async def test_public_inspect_exposes_no_internal_ids(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(
        session, permissions=("qr:create", "transactions:create")
    )
    service = QRService(session)
    qr = await service.create_dynamic_qr(
        actor, _dynamic_values(merchant, branch, till, idempotency_key="dyn-pub")
    )

    application = FastAPI()
    application.include_router(qr_router, prefix="/api/v1")
    application.dependency_overrides[get_qr_service] = lambda: service

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/qr/{qr.public_identifier}")
        assert resp.status_code == 200
        body = resp.json()
        forbidden_keys = {
            "merchant_id",
            "branch_id",
            "till_id",
            "encoded_payload",
            "payload",
            "payload_metadata",
            "transaction_id",
            "id",
            "secret",
            "signature",
        }
        assert forbidden_keys.isdisjoint(body.keys())
        assert "merchant_name" in body


@pytest.mark.asyncio
async def test_unauthorized_admin_qr_read(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(session, permissions=("qr:create",))
    other_actor, _, _, _ = await _actor(
        session,
        permissions=("qr:read",),
        merchant=Merchant(
            name="Other Hard",
            contact_email=f"{uuid.uuid4().hex}@example.com",
            contact_phone="+265991000002",
        ),
    )
    service = QRService(session)
    qr = await service.create_static_qr(
        actor,
        {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
    )
    with pytest.raises(QRForbiddenError):
        await service.get_qr(other_actor, qr.public_identifier)


@pytest.mark.asyncio
async def test_unauthorized_revoke(session: AsyncSession) -> None:
    actor, merchant, branch, till = await _actor(session, permissions=("qr:create",))
    revoker, _, _, _ = await _actor(
        session,
        permissions=("qr:revoke",),
        merchant=Merchant(
            name="Revoke Other",
            contact_email=f"{uuid.uuid4().hex}@example.com",
            contact_phone="+265991000003",
        ),
    )
    service = QRService(session)
    qr = await service.create_static_qr(
        actor,
        {"merchant_id": merchant.id, "branch_id": branch.id, "till_id": till.id},
    )
    with pytest.raises(QRForbiddenError):
        await service.revoke_qr(revoker, qr.public_identifier)


def test_payload_deterministic_signing() -> None:
    key = "test-secret-key-minimum-32-characters-long"
    a = QRPayloadService(key)
    b = QRPayloadService(key)
    encoded_a = a.encode_static(public_identifier="QRTEST12345678")
    encoded_b = b.encode_static(public_identifier="QRTEST12345678")
    assert encoded_a == encoded_b
    other = QRPayloadService("different-secret-key-minimum-32-chars")
    assert other.encode_static(public_identifier="QRTEST12345678") != encoded_a
