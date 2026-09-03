"""Comprehensive security tests for account lifecycle, verification, reset, and tenant authorization."""

from __future__ import annotations

import secrets
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
from app.api.v1.customers import get_customer_service, router as customers_router
from app.api.v1.organization import router as org_router
from app.api.v1.payments import get_payment_service, router as payments_router
from app.api.v1.qr import get_qr_service, router as qr_router
from app.api.v1.settlements import get_settlement_service, settlement_router
from app.core.config.base import get_settings
from app.core.security.exceptions import (
    InvalidTokenError,
    RateLimitAuthError,
    TokenExpiredError,
    TokenReplayError,
)
from app.core.security.jwt import JWTConfig
from app.core.security.password import PasswordHasher
from app.models import (
    AccountSecurityToken,
    Branch,
    CustomerPreference,
    Merchant,
    Permission,
    RefreshSession,
    Role,
    RolePermission,
    Till,
    User,
)
from app.models.base import Base
from app.payments.catalog import seed_provider_catalog
from app.repositories.auth import AccountSecurityTokenRepository, RefreshSessionRepository
from app.repositories.rbac import AuthorizationRepository
from app.repositories.user import UserRepository
from app.services.auth import AuthService
from app.services.authorization import AuthorizationService
from app.services.customer import CustomerService
from app.services.organization import OrganizationForbiddenError, OrganizationService
from app.services.payment import PaymentService
from app.services.qr import QRForbiddenError, QRInvalidError, QRService
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
        yield test_session
    await engine.dispose()


async def _get_or_create_permission(session: AsyncSession, code: str) -> Permission:
    p = await session.scalar(select(Permission).where(Permission.code == code))
    if p is None:
        p = Permission(code=code)
        session.add(p)
        await session.flush()
    return p


async def _create_role_with_perms(
    session: AsyncSession, code: str, name: str, perms: tuple[str, ...]
) -> Role:
    role = Role(code=code, name=name, is_active=True)
    session.add(role)
    await session.flush()
    for code_name in perms:
        perm = await _get_or_create_permission(session, code_name)
        session.add(RolePermission(role_id=role.id, permission_id=perm.id))
    await session.flush()
    return role


# ======================================================================
# 1. ACCOUNT LIFECYCLE & SECURITY TESTS
# ======================================================================


@pytest.mark.asyncio
async def test_customer_registration_and_unverified_policy(session: AsyncSession) -> None:
    """Customer registration produces a hashed-password user with is_email_verified=False."""
    await _create_role_with_perms(session, "customer", "Customer", ())
    jwt_cfg = _jwt()
    hasher = PasswordHasher()
    customer_svc = CustomerService(session, jwt_config=jwt_cfg, password_hasher=hasher)
    auth_svc = AuthService(session, jwt_cfg, hasher)

    email = "unverified-customer@example.com"
    tokens, user = await customer_svc.register(
        {
            "email": email,
            "full_name": "Test Customer",
            "password": "Password123!",
            "phone": "+265991112233",
        }
    )

    assert user.is_email_verified is False
    assert user.email_verified_at is None
    assert hasher.verify("Password123!", user.hashed_password)
    assert tokens.is_email_verified is False

    # Login succeeds but reports is_email_verified=False
    login_tokens, login_user = await auth_svc.login(email, "Password123!")
    assert login_tokens.is_email_verified is False
    assert login_user.is_email_verified is False


@pytest.mark.asyncio
async def test_email_verification_lifecycle_expiry_and_replay(session: AsyncSession) -> None:
    """Email verification token can be verified once; replay and expiry are rejected."""
    role = await _create_role_with_perms(session, "customer", "Customer", ())
    hasher = PasswordHasher()
    jwt_cfg = _jwt()
    auth_svc = AuthService(session, jwt_cfg, hasher)

    user = User(
        email="verify-test@example.com",
        full_name="Verify User",
        hashed_password=hasher.hash("Password123!"),
        role_id=role.id,
        is_email_verified=False,
    )
    session.add(user)
    await session.commit()

    # 1. Request verification token
    raw_token, dispatch = await auth_svc.request_email_verification(user)
    assert raw_token is not None
    assert dispatch["status"] == "not_configured"

    # Rate limiting: second request within 60s raises RateLimitAuthError
    with pytest.raises(RateLimitAuthError, match="wait 60 seconds"):
        await auth_svc.request_email_verification(user)

    # 2. Successfully verify with raw token
    verified_user = await auth_svc.verify_email(raw_token)
    assert verified_user.is_email_verified is True
    assert verified_user.email_verified_at is not None

    # 3. Replay attack: reusing token raises TokenReplayError
    with pytest.raises(TokenReplayError, match="already been used"):
        await auth_svc.verify_email(raw_token)

    # 4. Expiry test
    user2 = User(
        email="expired-token@example.com",
        full_name="Expired User",
        hashed_password=hasher.hash("Password123!"),
        role_id=role.id,
        is_email_verified=False,
    )
    session.add(user2)
    await session.commit()

    raw_token2, _ = await auth_svc.request_email_verification(user2)
    # Manually expire token
    token_repo = AccountSecurityTokenRepository(session)
    tok_record = await token_repo.get_latest_active_token(user2.id, "email_verification")
    assert tok_record is not None
    tok_record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await session.commit()

    with pytest.raises(TokenExpiredError, match="expired"):
        await auth_svc.verify_email(raw_token2)


@pytest.mark.asyncio
async def test_forgot_and_reset_password_flow(session: AsyncSession) -> None:
    """Password reset updates hash, invalidates token and all active sessions."""
    role = await _create_role_with_perms(session, "customer", "Customer", ())
    hasher = PasswordHasher()
    jwt_cfg = _jwt()
    auth_svc = AuthService(session, jwt_cfg, hasher)

    user = User(
        email="reset-test@example.com",
        full_name="Reset User",
        hashed_password=hasher.hash("OldPassword123!"),
        role_id=role.id,
        is_active=True,
    )
    session.add(user)
    await session.commit()

    # Active session
    tokens, _ = await auth_svc.login("reset-test@example.com", "OldPassword123!")
    refresh_repo = RefreshSessionRepository(session)
    active_sessions = await session.scalars(
        select(RefreshSession).where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
    )
    assert len(list(active_sessions)) == 1

    # Forgot password on non-existent email -> does not enumerate (returns None, generic info)
    none_tok, _ = await auth_svc.request_password_reset("nonexistent@example.com")
    assert none_tok is None

    # Forgot password on existing email -> returns raw token
    raw_token, _ = await auth_svc.request_password_reset("reset-test@example.com")
    assert raw_token is not None

    # Reset password with valid token
    await auth_svc.reset_password(raw_token, "NewPassword456!")

    # Verify new password works and old password fails
    with pytest.raises(Exception):
        await auth_svc.login("reset-test@example.com", "OldPassword123!")

    new_tokens, _ = await auth_svc.login("reset-test@example.com", "NewPassword456!")
    assert new_tokens.access_token is not None

    # Replay: used reset token is rejected
    with pytest.raises(TokenReplayError, match="already been used"):
        await auth_svc.reset_password(raw_token, "AnotherPassword789!")


# ======================================================================
# 2. AUTHORIZATION & TENANT CAPABILITY TESTS
# ======================================================================


async def _setup_merchant_hierarchy(session: AsyncSession) -> tuple[Merchant, Branch, Till, User, User]:
    """Create Merchant A, Branch A, Till A, Merchant Owner A, and Ordinary Customer."""
    merchant_role = await _create_role_with_perms(
        session,
        "merchant_owner",
        "Merchant Owner",
        (
            "merchants:read",
            "branches:read",
            "tills:read",
            "qr:create",
            "qr:read",
            "transactions:read",
            "settlements:read",
        ),
    )
    customer_role = await _create_role_with_perms(session, "customer", "Customer", ())
    hasher = PasswordHasher()

    merchant = Merchant(
        name="Apex Stores",
        contact_email="owner@apex.mw",
        contact_phone="+265991000000",
        is_active=True,
    )
    session.add(merchant)
    await session.flush()

    branch = Branch(merchant_id=merchant.id, name="Downtown Branch", is_active=True)
    session.add(branch)
    await session.flush()

    till = Till(branch_id=branch.id, code="TILL-01", name="Till 1", is_active=True)
    session.add(till)
    await session.flush()

    merchant_user = User(
        email="merchant-owner@apex.mw",
        full_name="Apex Owner",
        hashed_password=hasher.hash("ApexSecret1!"),
        merchant_id=merchant.id,
        role_id=merchant_role.id,
        is_active=True,
        is_email_verified=True,
    )
    merchant_user.role = merchant_role

    customer_user = User(
        email="ordinary-customer@apex.mw",
        full_name="Ordinary Customer",
        hashed_password=hasher.hash("CustSecret1!"),
        merchant_id=None,
        role_id=customer_role.id,
        is_active=True,
        is_email_verified=True,
    )
    customer_user.role = customer_role

    session.add_all([merchant_user, customer_user])
    await session.commit()
    return merchant, branch, till, merchant_user, customer_user


@pytest.mark.asyncio
async def test_merchant_access_capability_check(session: AsyncSession) -> None:
    """get_merchant_access returns allowed=False for customer, allowed=True for authorized merchant."""
    merchant, branch, till, merchant_user, customer_user = await _setup_merchant_hierarchy(session)
    org_svc = OrganizationService(session)

    # Customer capability check
    cust_access = await org_svc.get_merchant_access(customer_user)
    assert cust_access["allowed"] is False
    assert cust_access["can_generate_qr"] is False
    assert len(cust_access["branches"]) == 0
    assert len(cust_access["tills"]) == 0

    # Merchant capability check
    merch_access = await org_svc.get_merchant_access(merchant_user)
    assert merch_access["allowed"] is True
    assert merch_access["can_generate_qr"] is True
    assert merch_access["merchant"].id == merchant.id
    assert len(merch_access["branches"]) == 1
    assert merch_access["branches"][0].id == branch.id
    assert len(merch_access["tills"]) == 1
    assert merch_access["tills"][0]["id"] == till.id
    assert merch_access["operating_branch_id"] == branch.id
    assert merch_access["operating_till_id"] == till.id


@pytest.mark.asyncio
async def test_cross_merchant_and_branch_till_isolation(session: AsyncSession) -> None:
    """Merchant user cannot create QR for another merchant or unassigned branch/till."""
    await seed_provider_catalog(session)
    m1, b1, t1, user1, _ = await _setup_merchant_hierarchy(session)

    # Create Merchant 2 and Branch 2 / Till 2
    m2 = Merchant(name="Other Merchant", contact_email="m2@other.mw", contact_phone="+265992222222")
    session.add(m2)
    await session.flush()
    b2 = Branch(merchant_id=m2.id, name="Other Branch", is_active=True)
    session.add(b2)
    await session.flush()
    t2 = Till(branch_id=b2.id, code="TILL-OTHER", name="Till Other", is_active=True)
    session.add(t2)
    await session.commit()

    qr_svc = QRService(session)

    # 1. Merchant 1 creates QR for own till -> SUCCESS
    valid_qr = await qr_svc.create_static_qr(
        user1,
        {
            "merchant_id": m1.id,
            "branch_id": b1.id,
            "till_id": t1.id,
        },
    )
    assert valid_qr.public_identifier is not None

    # 2. Attack: Merchant 1 tries to create QR targeting Merchant 2 -> DENIED
    with pytest.raises(QRForbiddenError, match="outside actor scope"):
        await qr_svc.create_static_qr(
            user1,
            {
                "merchant_id": m2.id,
                "branch_id": b2.id,
                "till_id": t2.id,
            },
        )

    # 3. Attack: Merchant 1 passes own merchant ID but Till 2 from Merchant 2 -> INVALID
    with pytest.raises(QRInvalidError, match="unavailable"):
        await qr_svc.create_static_qr(
            user1,
            {
                "merchant_id": m1.id,
                "branch_id": b1.id,
                "till_id": t2.id,
            },
        )


# ======================================================================
# 3. DIRECT API-LEVEL ATTACK TESTS (CUSTOMER JWT VS MERCHANT ENDPOINTS)
# ======================================================================


@pytest.mark.asyncio
async def test_direct_api_level_customer_jwt_attack(session: AsyncSession) -> None:
    """Mandatory Section 22 Attack Test: Customer JWT calling merchant APIs directly."""
    await seed_provider_catalog(session)
    merchant, branch, till, merchant_user, customer_user = await _setup_merchant_hierarchy(session)
    jwt_cfg = _jwt()

    customer_token = jwt_cfg.create_access_token(subject=str(customer_user.id))
    merchant_token = jwt_cfg.create_access_token(subject=str(merchant_user.id))

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(org_router, prefix="/api/v1")
    app.include_router(qr_router, prefix="/api/v1")
    app.include_router(payments_router, prefix="/api/v1")
    app.include_router(settlement_router, prefix="/api/v1")

    # Dependency overrides
    app.dependency_overrides[deps.get_db_session] = lambda: session
    app.dependency_overrides[deps.get_jwt_config] = lambda: jwt_cfg
    app.dependency_overrides[get_qr_service] = lambda: QRService(session)
    app.dependency_overrides[get_payment_service] = lambda: PaymentService(session)
    app.dependency_overrides[get_settlement_service] = lambda: SettlementService(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        customer_headers = {"Authorization": f"Bearer {customer_token}"}
        merchant_headers = {"Authorization": f"Bearer {merchant_token}"}

        # ATTACK 1: Customer calls POST /api/v1/qr/static -> MUST BE 403 FORBIDDEN
        resp = await client.post(
            "/api/v1/qr/static",
            headers=customer_headers,
            json={
                "merchant_id": str(merchant.id),
                "branch_id": str(branch.id),
                "till_id": str(till.id),
            },
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

        # ATTACK 2: Customer calls POST /api/v1/qr/dynamic -> MUST BE 403 FORBIDDEN
        resp = await client.post(
            "/api/v1/qr/dynamic",
            headers=customer_headers,
            json={
                "merchant_id": str(merchant.id),
                "branch_id": str(branch.id),
                "till_id": str(till.id),
                "amount": "1500.00",
                "currency": "MWK",
                "payment_method": "mobile_money",
                "idempotency_key": "atk-dyn-1",
            },
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

        # ATTACK 3: Customer calls GET /api/v1/payments (merchant transactions) -> MUST BE 403 FORBIDDEN
        resp = await client.get("/api/v1/payments", headers=customer_headers)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

        # ATTACK 4: Customer calls GET /api/v1/settlements/summary -> MUST BE 403 FORBIDDEN
        resp = await client.get("/api/v1/settlements/summary", headers=customer_headers)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

        # ATTACK 5: Customer calls GET /api/v1/organization/merchants -> MUST BE 403 FORBIDDEN
        resp = await client.get("/api/v1/organization/merchants", headers=customer_headers)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

        # Capability check for customer -> 200 with allowed: false
        resp = await client.get("/api/v1/organization/my-access", headers=customer_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["allowed"] is False
        assert data["can_generate_qr"] is False
        assert len(data["branches"]) == 0

        # ATTACK 6: Customer calls GET /api/v1/qr (list merchant QR records) -> MUST BE 403 FORBIDDEN
        resp = await client.get("/api/v1/qr", headers=customer_headers)
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

        # ATTACK 7: Authorized merchant attempts to create QR on unauthorized branch/till -> 400 or 403
        fake_uuid = uuid.uuid4()
        resp = await client.post(
            "/api/v1/qr/static",
            headers=merchant_headers,
            json={
                "merchant_id": str(merchant.id),
                "branch_id": str(branch.id),
                "till_id": str(fake_uuid),
            },
        )
        assert resp.status_code in (400, 403, 404, 422), f"Expected client error, got {resp.status_code}"

        # AUTHORIZED MERCHANT SUCCESS: Merchant calls POST /api/v1/qr/static -> 201 CREATED
        merch_resp = await client.post(
            "/api/v1/qr/static",
            headers=merchant_headers,
            json={
                "merchant_id": str(merchant.id),
                "branch_id": str(branch.id),
                "till_id": str(till.id),
            },
        )
        assert merch_resp.status_code == 201, f"Expected 201, got {merch_resp.status_code}: {merch_resp.text}"
        qr_body = merch_resp.json()
        assert qr_body["merchant_id"] == str(merchant.id)
        assert qr_body["qr_type"] == "static"

        # AUTHORIZED MERCHANT SUCCESS: Merchant capability check -> allowed: true
        merch_cap = await client.get("/api/v1/organization/my-access", headers=merchant_headers)
        assert merch_cap.status_code == 200
        cap_body = merch_cap.json()
        assert cap_body["allowed"] is True
        assert cap_body["can_generate_qr"] is True
        assert cap_body["merchant"]["id"] == str(merchant.id)
        assert len(cap_body["branches"]) == 1
        assert len(cap_body["tills"]) == 1


@pytest.mark.asyncio
async def test_auth_http_endpoints_verification_and_reset(session: AsyncSession) -> None:
    """HTTP API endpoints for email verification, forgot-password and reset-password."""
    role = await _create_role_with_perms(session, "customer", "Customer", ())
    hasher = PasswordHasher()
    jwt_cfg = _jwt()

    user = User(
        email="http-verify@example.com",
        full_name="HTTP Verify User",
        hashed_password=hasher.hash("InitialPass1!"),
        role_id=role.id,
        is_active=True,
        is_email_verified=False,
    )
    session.add(user)
    await session.commit()

    auth_svc = AuthService(session, jwt_cfg, hasher)

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.dependency_overrides[deps.get_db_session] = lambda: session
    app.dependency_overrides[deps.get_auth_service] = lambda: auth_svc

    # Generate a verification token for this user
    raw_vtoken, _ = await auth_svc.request_email_verification(user)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Verify email via HTTP
        v_resp = await client.post("/api/v1/auth/verify-email", json={"token": raw_vtoken})
        assert v_resp.status_code == 200
        assert v_resp.json()["is_email_verified"] is True

        # 2. Replay verify email -> 400
        v_replay = await client.post("/api/v1/auth/verify-email", json={"token": raw_vtoken})
        assert v_replay.status_code == 400
        assert "already been used" in v_replay.text

        # 3. Forgot password -> generic 200 (records token in DB and dispatches via boundary)
        forgot_resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "http-verify@example.com"},
        )
        assert forgot_resp.status_code == 200
        assert forgot_resp.json()["email_delivery"] == "not_configured"

        # Forgot password for unknown email -> same generic 200 (no email enumeration)
        unknown_forgot = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nobody-exists@example.com"},
        )
        assert unknown_forgot.status_code == 200

        # Verify that a reset token was created for user
        tok_repo = AccountSecurityTokenRepository(session)
        reset_record = await tok_repo.get_latest_active_token(user.id, "password_reset")
        assert reset_record is not None
        assert reset_record.is_valid is True

        # Now test reset password with a known token for a second user
        user2 = User(
            email="reset-http@example.com",
            full_name="Reset User 2",
            hashed_password=hasher.hash("InitialPass2!"),
            role_id=role.id,
            is_active=True,
        )
        session.add(user2)
        await session.commit()

        raw_rtoken, _ = await auth_svc.request_password_reset("reset-http@example.com")
        assert raw_rtoken is not None

        # 4. Reset password via HTTP
        reset_resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_rtoken, "new_password": "BrandNewPassword1!"},
        )
        assert reset_resp.status_code == 200
        assert "successfully reset" in reset_resp.json()["detail"]

        # 5. Replay reset password -> 400
        replay_reset = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_rtoken, "new_password": "AnotherBrandNew1!"},
        )
        assert replay_reset.status_code == 400
        assert "already been used" in replay_reset.text
