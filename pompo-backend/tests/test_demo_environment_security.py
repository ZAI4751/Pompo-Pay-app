"""Security and simulation tests for POMPO demonstration environment (Part B).

Validates:
1. Customer JWT cannot create merchant QR (static or dynamic)
2. Customer JWT cannot access merchant transactions
3. Customer JWT cannot access merchant settlements
4. Customer JWT cannot use arbitrary merchant/branch/till IDs
5. Merchant JWT can only access authorized merchant/branch/till
6. Public QR cannot mutate QR/merchant/amount state
7. Dynamic QR amount is server-authoritative
8. Platform Admin without merchant_id cannot access Merchant Mode
9. Deterministic simulated provider outcomes:
   - SUCCESS (simulated)
   - FAILED (simulated_failure)
   - PENDING (simulated_pending)
   - TIMEOUT (simulated_timeout)
   - IDEMPOTENT DUPLICATE replay
"""

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
from app.api.v1.auth import router as auth_router
from app.api.v1.organization import router as org_router
from app.api.v1.payments import get_payment_service, router as payments_router
from app.api.v1.qr import get_qr_service, router as qr_router
from app.api.v1.settlements import get_settlement_service, settlement_router
from app.core.config.base import get_settings
from app.core.security.jwt import JWTConfig
from app.core.security.password import PasswordHasher
from app.models import (
    Branch,
    Merchant,
    PaymentInstrument,
    Permission,
    Role,
    RolePermission,
    Till,
    User,
)
from app.models.base import Base
from app.models.enums import PaymentInstrumentStatus, PaymentInstrumentType, ProviderCode, TransactionStatus
from app.models.payment import PaymentProvider
from app.payments.catalog import seed_provider_catalog
from app.permissions.catalog import PERMISSIONS, SYSTEM_ROLES
from app.services.organization import OrganizationService
from app.services.payment import PaymentConflictError, PaymentService
from app.services.qr import QRConflictError, QRForbiddenError, QRInvalidError, QRService
from app.services.settlement import SettlementService


def _jwt() -> JWTConfig:
    return JWTConfig(get_settings())


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        # Seed permissions & system roles
        perms: dict[str, Permission] = {}
        for p_def in PERMISSIONS:
            perm = Permission(code=p_def.code, description=p_def.description)
            test_session.add(perm)
            perms[p_def.code] = perm
        await test_session.flush()

        for code, (name, desc, p_codes) in SYSTEM_ROLES.items():
            role = Role(code=code, name=name, description=desc, is_system_role=True, is_active=True)
            test_session.add(role)
            await test_session.flush()
            for p_code in p_codes:
                if p_code in perms:
                    test_session.add(
                        RolePermission(role_id=role.id, permission_id=perms[p_code].id, granted_at=datetime.now(UTC))
                    )
        await test_session.flush()
        await seed_provider_catalog(test_session)
        yield test_session
    await engine.dispose()


async def _create_test_context(session: AsyncSession):
    hasher = PasswordHasher()
    admin_role = await session.scalar(select(Role).where(Role.code == "platform_admin"))
    merchant_role = await session.scalar(select(Role).where(Role.code == "merchant_owner"))
    customer_role = await session.scalar(select(Role).where(Role.code == "customer"))

    # Merchant A
    merchant_a = Merchant(
        name="POMPO Demo Merchant A",
        registration_number="DEMO-A",
        contact_email="demo.a@pompo.mw",
        contact_phone="+265999000100",
        is_active=True,
    )
    session.add(merchant_a)
    await session.flush()
    branch_a = Branch(merchant_id=merchant_a.id, name="Branch A", is_active=True)
    session.add(branch_a)
    await session.flush()
    till_a = Till(branch_id=branch_a.id, code="TILL-A1", name="Till A1", is_active=True)
    session.add(till_a)

    # Merchant B (unauthorized target)
    merchant_b = Merchant(
        name="POMPO Demo Merchant B",
        registration_number="DEMO-B",
        contact_email="demo.b@pompo.mw",
        contact_phone="+265999000200",
        is_active=True,
    )
    session.add(merchant_b)
    await session.flush()
    branch_b = Branch(merchant_id=merchant_b.id, name="Branch B", is_active=True)
    session.add(branch_b)
    await session.flush()
    till_b = Till(branch_id=branch_b.id, code="TILL-B1", name="Till B1", is_active=True)
    session.add(till_b)

    # Users
    admin_user = User(
        email="demo.admin@pompo.mw",
        hashed_password=hasher.hash("pass"),
        full_name="Platform Admin",
        role_id=admin_role.id,
        merchant_id=None,
        branch_id=None,
        is_active=True,
    )
    merchant_user = User(
        email="demo.merchant@pompo.mw",
        hashed_password=hasher.hash("pass"),
        full_name="Merchant User A",
        role_id=merchant_role.id,
        merchant_id=merchant_a.id,
        branch_id=branch_a.id,
        is_active=True,
    )
    customer_user = User(
        email="demo.customer@pompo.mw",
        hashed_password=hasher.hash("pass"),
        full_name="Customer User",
        role_id=customer_role.id,
        merchant_id=None,
        branch_id=None,
        is_active=True,
    )
    session.add_all([admin_user, merchant_user, customer_user])
    await session.flush()

    return {
        "admin": admin_user,
        "merchant_user": merchant_user,
        "customer": customer_user,
        "merchant_a": merchant_a,
        "branch_a": branch_a,
        "till_a": till_a,
        "merchant_b": merchant_b,
        "branch_b": branch_b,
        "till_b": till_b,
    }


# ======================================================================
# 1. PLATFORM ADMIN CAPABILITY CHECK (ADMIN DOES NOT IMPLY MERCHANT)
# ======================================================================

@pytest.mark.asyncio
async def test_platform_admin_does_not_imply_merchant_access(session: AsyncSession) -> None:
    ctx = await _create_test_context(session)
    org_svc = OrganizationService(session)

    # Admin without merchant_id MUST NOT be allowed to operate Merchant Mode
    admin_access = await org_svc.get_merchant_access(ctx["admin"])
    assert admin_access["allowed"] is False
    assert admin_access["merchant"] is None
    assert admin_access["can_generate_qr"] is False

    # Customer without merchant_id MUST NOT be allowed
    cust_access = await org_svc.get_merchant_access(ctx["customer"])
    assert cust_access["allowed"] is False
    assert cust_access["can_generate_qr"] is False

    # Merchant user with merchant_id MUST be allowed
    merch_access = await org_svc.get_merchant_access(ctx["merchant_user"])
    assert merch_access["allowed"] is True
    assert merch_access["can_generate_qr"] is True
    assert merch_access["merchant"].id == ctx["merchant_a"].id


# ======================================================================
# 2. CUSTOMER JWT ACCESS RESTRICTIONS (QR, TRANSACTIONS, SETTLEMENTS)
# ======================================================================

@pytest.mark.asyncio
async def test_customer_jwt_forbidden_on_merchant_endpoints(session: AsyncSession) -> None:
    ctx = await _create_test_context(session)
    jwt_cfg = _jwt()
    customer_token = jwt_cfg.create_access_token(subject=str(ctx["customer"].id))

    app = FastAPI()
    app.include_router(qr_router, prefix="/api/v1")
    app.include_router(payments_router, prefix="/api/v1")
    app.include_router(settlement_router, prefix="/api/v1")
    app.dependency_overrides[deps.get_db_session] = lambda: session
    app.dependency_overrides[deps.get_jwt_config] = lambda: jwt_cfg
    app.dependency_overrides[get_qr_service] = lambda: QRService(session)
    app.dependency_overrides[get_payment_service] = lambda: PaymentService(session)
    app.dependency_overrides[get_settlement_service] = lambda: SettlementService(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {customer_token}"}

        # 1. Customer cannot create static QR
        resp = await client.post(
            "/api/v1/qr/static",
            headers=headers,
            json={
                "merchant_id": str(ctx["merchant_a"].id),
                "branch_id": str(ctx["branch_a"].id),
                "till_id": str(ctx["till_a"].id),
            },
        )
        assert resp.status_code == 403

        # 2. Customer cannot create dynamic QR
        resp = await client.post(
            "/api/v1/qr/dynamic",
            headers=headers,
            json={
                "merchant_id": str(ctx["merchant_a"].id),
                "branch_id": str(ctx["branch_a"].id),
                "till_id": str(ctx["till_a"].id),
                "amount": "1000.00",
                "currency": "MWK",
                "payment_method": "mobile_money",
                "idempotency_key": f"cust-dyn-{uuid.uuid4().hex}",
            },
        )
        assert resp.status_code == 403

        # 3. Customer cannot access merchant payments list
        resp = await client.get("/api/v1/payments", headers=headers)
        assert resp.status_code == 403

        # 4. Customer cannot access merchant settlements summary
        resp = await client.get("/api/v1/settlements/summary", headers=headers)
        assert resp.status_code == 403


# ======================================================================
# 3. MERCHANT CAN ONLY ACCESS AUTHORIZED MERCHANT / BRANCH / TILL
# ======================================================================

@pytest.mark.asyncio
async def test_merchant_cross_tenant_isolation(session: AsyncSession) -> None:
    ctx = await _create_test_context(session)
    qr_svc = QRService(session)

    # Merchant A attempts to create QR for Merchant B -> Forbidden
    with pytest.raises(QRForbiddenError):
        await qr_svc.create_static_qr(
            ctx["merchant_user"],
            {
                "merchant_id": ctx["merchant_b"].id,
                "branch_id": ctx["branch_b"].id,
                "till_id": ctx["till_b"].id,
            },
        )

    # Merchant A attempts to create QR with arbitrary / non-existent till -> Invalid/Forbidden
    with pytest.raises((QRInvalidError, QRForbiddenError)):
        await qr_svc.create_static_qr(
            ctx["merchant_user"],
            {
                "merchant_id": ctx["merchant_a"].id,
                "branch_id": ctx["branch_a"].id,
                "till_id": uuid.uuid4(),
            },
        )

    # Merchant A creates QR for authorized branch & till -> Success
    qr = await qr_svc.create_static_qr(
        ctx["merchant_user"],
        {
            "merchant_id": ctx["merchant_a"].id,
            "branch_id": ctx["branch_a"].id,
            "till_id": ctx["till_a"].id,
        },
    )
    assert qr.public_identifier.startswith("QR")
    assert qr.merchant_id == ctx["merchant_a"].id


# ======================================================================
# 4. PUBLIC QR INTEGRITY & SERVER-AUTHORITATIVE DYNAMIC AMOUNT
# ======================================================================

@pytest.mark.asyncio
async def test_public_qr_integrity_and_server_authoritative_amount(session: AsyncSession) -> None:
    ctx = await _create_test_context(session)
    qr_svc = QRService(session)

    # Create dynamic QR for MWK 3500.00
    dyn_qr = await qr_svc.create_dynamic_qr(
        ctx["merchant_user"],
        {
            "merchant_id": ctx["merchant_a"].id,
            "branch_id": ctx["branch_a"].id,
            "till_id": ctx["till_a"].id,
            "amount": Decimal("3500.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated",
            "idempotency_key": f"dyn-test-{uuid.uuid4().hex}",
        },
    )
    assert dyn_qr.amount == Decimal("3500.00")

    # Customer attempts to pay dynamic QR with tampered amount (e.g. MWK 100.00)
    # Backend must reject this: amount for dynamic QR is strictly server-authoritative
    with pytest.raises(QRInvalidError, match="Amount cannot be modified for dynamic QR"):
        await qr_svc.initiate_payment_from_qr(
            ctx["customer"],
            {
                "public_identifier": dyn_qr.public_identifier,
                "amount": Decimal("100.00"),
                "idempotency_key": f"tamper-amt-{uuid.uuid4().hex}",
            },
        )

    # Customer pays without overriding amount -> uses server-authoritative MWK 3500.00
    payment = await qr_svc.initiate_payment_from_qr(
        ctx["customer"],
        {
            "public_identifier": dyn_qr.public_identifier,
            "idempotency_key": f"valid-pay-{uuid.uuid4().hex}",
        },
    )
    assert payment.amount == Decimal("3500.00")
    assert payment.status == TransactionStatus.PENDING


# ======================================================================
# 5. SIMULATED PROVIDER DETERMINISTIC OUTCOMES
# ======================================================================

@pytest.mark.asyncio
async def test_simulated_provider_deterministic_outcomes(session: AsyncSession) -> None:
    ctx = await _create_test_context(session)
    qr_svc = QRService(session)
    pmt_svc = PaymentService(session)

    # 1. SUCCESS OUTCOME (simulated provider)
    static_qr = await qr_svc.create_static_qr(
        ctx["merchant_user"],
        {
            "merchant_id": ctx["merchant_a"].id,
            "branch_id": ctx["branch_a"].id,
            "till_id": ctx["till_a"].id,
        },
    )
    idem_key = f"succ-{uuid.uuid4().hex}"
    tx_success = await qr_svc.initiate_payment_from_qr(
        ctx["customer"],
        {
            "public_identifier": static_qr.public_identifier,
            "amount": Decimal("1500.00"),
            "provider_code": "simulated",
            "idempotency_key": idem_key,
        },
    )
    processed = await pmt_svc.process_payment(ctx["customer"], tx_success.reference)
    assert processed.status == TransactionStatus.SUCCESS

    # 2. IDEMPOTENT REPLAY
    tx_replay = await qr_svc.initiate_payment_from_qr(
        ctx["customer"],
        {
            "public_identifier": static_qr.public_identifier,
            "amount": Decimal("1500.00"),
            "provider_code": "simulated",
            "idempotency_key": idem_key,
        },
    )
    assert tx_replay.id == tx_success.id

    # Idempotent replay with different amount must fail
    with pytest.raises(QRInvalidError, match="Idempotency key was used with a different request"):
        await qr_svc.initiate_payment_from_qr(
            ctx["customer"],
            {
                "public_identifier": static_qr.public_identifier,
                "amount": Decimal("9999.00"),
                "provider_code": "simulated",
                "idempotency_key": idem_key,
            },
        )

    # 3. FAILED OUTCOME (simulated_failure provider)
    tx_fail = await qr_svc.initiate_payment_from_qr(
        ctx["customer"],
        {
            "public_identifier": static_qr.public_identifier,
            "amount": Decimal("2000.00"),
            "provider_code": "simulated_failure",
            "idempotency_key": f"fail-{uuid.uuid4().hex}",
        },
    )
    processed_fail = await pmt_svc.process_payment(ctx["customer"], tx_fail.reference)
    assert processed_fail.status == TransactionStatus.FAILED

    # 4. PENDING OUTCOME (simulated_pending provider)
    tx_pending = await qr_svc.initiate_payment_from_qr(
        ctx["customer"],
        {
            "public_identifier": static_qr.public_identifier,
            "amount": Decimal("2500.00"),
            "provider_code": "simulated_pending",
            "idempotency_key": f"pend-{uuid.uuid4().hex}",
        },
    )
    processed_pending = await pmt_svc.process_payment(ctx["customer"], tx_pending.reference)
    assert processed_pending.status in (TransactionStatus.PENDING, TransactionStatus.PROCESSING)

    # 5. TIMEOUT OUTCOME (simulated_timeout provider)
    tx_timeout = await qr_svc.initiate_payment_from_qr(
        ctx["customer"],
        {
            "public_identifier": static_qr.public_identifier,
            "amount": Decimal("3000.00"),
            "provider_code": "simulated_timeout",
            "idempotency_key": f"time-{uuid.uuid4().hex}",
        },
    )
    processed_timeout = await pmt_svc.process_payment(ctx["customer"], tx_timeout.reference)
    # Timeouts in payment processing transition to FAILED or retryable status
    assert processed_timeout.status in (TransactionStatus.FAILED, TransactionStatus.PROCESSING)
