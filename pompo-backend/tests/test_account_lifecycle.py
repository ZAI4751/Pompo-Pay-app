"""Account lifecycle: customer deactivation, reactivation, and enforcement."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
from app.api.v1.auth import router as auth_router
from app.api.v1.instruments import get_instrument_service, router as instruments_router
from app.api.v1.organization import router as org_router
from app.api.v1.payments import get_payment_service, router as payments_router
from app.core.security.exceptions import (
    AccountDeactivatedError,
    AccountStateError,
    InactiveUserError,
    InvalidConfirmationError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    TokenReplayError,
)
from app.core.security.jwt import JWTConfig
from app.core.security.password import PasswordHasher
from app.models import (
    AuditLog,
    Branch,
    CustomerPreference,
    Merchant,
    PaymentInstrument,
    Permission,
    RefreshSession,
    Role,
    RolePermission,
    Till,
    User,
)
from app.models.base import Base
from app.models.enums import (
    AccountLifecycleStatus,
    PaymentInstrumentStatus,
    PaymentInstrumentType,
    ProviderAuthorizationState,
)
from app.models.payment import PaymentProvider
from app.payments.catalog import seed_provider_catalog
from app.repositories.auth import AccountSecurityTokenRepository
from app.services.auth import (
    DEACTIVATION_CONFIRMATION,
    TOKEN_TYPE_ACCOUNT_REACTIVATION,
    AuthService,
)
from app.services.instrument import PaymentInstrumentService
from app.services.organization import OrganizationService
from app.services.payment import PaymentService


class _FakeSettings:
    jwt_secret_key = "unit-test-jwt-secret-key-minimum-32-chars"
    jwt_algorithm = "HS256"
    jwt_access_token_expire_minutes = 15
    jwt_refresh_token_expire_days = 7


PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher()


@pytest.fixture
def jwt_config() -> JWTConfig:
    return JWTConfig(_FakeSettings())


@pytest.fixture
def auth_service(session: AsyncSession, jwt_config: JWTConfig, hasher: PasswordHasher) -> AuthService:
    return AuthService(session=session, jwt_config=jwt_config, password_hasher=hasher)


async def _role(session: AsyncSession, code: str, *permissions: str) -> Role:
    role = Role(code=code, name=code.replace("_", " ").title(), is_active=True)
    session.add(role)
    await session.flush()
    for perm_code in permissions:
        existing = await session.scalar(select(Permission).where(Permission.code == perm_code))
        if existing is None:
            existing = Permission(code=perm_code)
            session.add(existing)
            await session.flush()
        session.add(RolePermission(role_id=role.id, permission_id=existing.id))
    await session.flush()
    return role


async def _user(
    session: AsyncSession,
    hasher: PasswordHasher,
    role: Role,
    *,
    email: str,
    merchant_id=None,
    branch_id=None,
    is_active: bool = True,
    account_status: str = AccountLifecycleStatus.ACTIVE.value,
) -> User:
    user = User(
        role=role,
        email=email,
        full_name=email.split("@")[0],
        hashed_password=hasher.hash(PASSWORD),
        merchant_id=merchant_id,
        branch_id=branch_id,
        is_active=is_active,
        account_status=account_status,
        is_email_verified=True,
    )
    session.add(user)
    await session.commit()
    return user


def _app(session: AsyncSession, auth_service: AuthService, jwt_config: JWTConfig) -> FastAPI:
    application = FastAPI()
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(instruments_router, prefix="/api/v1")
    application.include_router(org_router, prefix="/api/v1")
    application.include_router(payments_router, prefix="/api/v1")
    application.dependency_overrides[deps.get_db_session] = lambda: session
    application.dependency_overrides[deps.get_auth_service] = lambda: auth_service
    application.dependency_overrides[deps.get_jwt_config] = lambda: jwt_config
    application.dependency_overrides[get_instrument_service] = lambda: PaymentInstrumentService(session)
    application.dependency_overrides[get_payment_service] = lambda: PaymentService(session)
    return application


@pytest.mark.asyncio
async def test_active_account_works_normally(
    auth_service: AuthService, session: AsyncSession, hasher: PasswordHasher
) -> None:
    role = await _role(session, "customer")
    user = await _user(session, hasher, role, email="active@example.com")
    tokens, resolved = await auth_service.login(user.email, PASSWORD)
    me = await auth_service.get_current_user(tokens.access_token)
    assert resolved.id == user.id
    assert me.id == user.id
    assert user.can_authenticate is True
    assert user.account_status == AccountLifecycleStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_customer_can_deactivate_own_account(
    auth_service: AuthService, session: AsyncSession, hasher: PasswordHasher
) -> None:
    role = await _role(session, "customer")
    user = await _user(session, hasher, role, email="self@example.com")
    await auth_service.deactivate_account(user, PASSWORD, DEACTIVATION_CONFIRMATION)
    await session.refresh(user)
    assert user.is_active is False
    assert user.account_status == AccountLifecycleStatus.DEACTIVATED.value
    assert user.deactivated_at is not None
    assert user.deleted_at is None


@pytest.mark.asyncio
async def test_deactivation_requires_password_and_confirmation(
    auth_service: AuthService, session: AsyncSession, hasher: PasswordHasher
) -> None:
    role = await _role(session, "customer")
    user = await _user(session, hasher, role, email="confirm@example.com")
    with pytest.raises(InvalidConfirmationError):
        await auth_service.deactivate_account(user, PASSWORD, "yes")
    with pytest.raises(InvalidCredentialsError):
        await auth_service.deactivate_account(user, "wrong-password", DEACTIVATION_CONFIRMATION)
    await session.refresh(user)
    assert user.can_authenticate is True


@pytest.mark.asyncio
async def test_deactivation_revokes_sessions_and_rejects_refresh(
    auth_service: AuthService, session: AsyncSession, hasher: PasswordHasher
) -> None:
    role = await _role(session, "customer")
    user = await _user(session, hasher, role, email="sessions@example.com")
    tokens, _ = await auth_service.login(user.email, PASSWORD)
    await auth_service.deactivate_account(user, PASSWORD, DEACTIVATION_CONFIRMATION)

    rows = list(
        (
            await session.scalars(
                select(RefreshSession).where(RefreshSession.user_id == user.id)
            )
        ).all()
    )
    assert rows
    assert all(row.revoked_at is not None for row in rows)

    with pytest.raises((InvalidTokenError, InactiveUserError, TokenReplayError)):
        await auth_service.refresh(tokens.refresh_token)


@pytest.mark.asyncio
async def test_existing_access_token_rejected_after_deactivation(
    auth_service: AuthService, session: AsyncSession, hasher: PasswordHasher
) -> None:
    role = await _role(session, "customer")
    user = await _user(session, hasher, role, email="token@example.com")
    tokens, _ = await auth_service.login(user.email, PASSWORD)
    await auth_service.deactivate_account(user, PASSWORD, DEACTIVATION_CONFIRMATION)
    with pytest.raises(InactiveUserError):
        await auth_service.get_current_user(tokens.access_token)


@pytest.mark.asyncio
async def test_login_after_deactivation_requires_reactivation(
    auth_service: AuthService, session: AsyncSession, hasher: PasswordHasher
) -> None:
    role = await _role(session, "customer")
    user = await _user(session, hasher, role, email="login-deact@example.com")
    await auth_service.deactivate_account(user, PASSWORD, DEACTIVATION_CONFIRMATION)
    with pytest.raises(AccountDeactivatedError):
        await auth_service.login(user.email, PASSWORD)


@pytest.mark.asyncio
async def test_deactivated_account_cannot_use_payments_or_methods(
    auth_service: AuthService,
    session: AsyncSession,
    hasher: PasswordHasher,
    jwt_config: JWTConfig,
) -> None:
    role = await _role(session, "customer", "transactions:create")
    user = await _user(session, hasher, role, email="pay@example.com")
    tokens, _ = await auth_service.login(user.email, PASSWORD)
    await auth_service.deactivate_account(user, PASSWORD, DEACTIVATION_CONFIRMATION)

    application = _app(session, auth_service, jwt_config)
    transport = ASGITransport(app=application)
    headers = {"Authorization": f"Bearer {tokens.access_token}"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        methods = await client.get("/api/v1/payment-methods", headers=headers)
        assert methods.status_code == 401
        pay = await client.post(
            "/api/v1/payments/from-qr",
            headers=headers,
            json={"public_identifier": "qr-none", "idempotency_key": "deact-1"},
        )
        assert pay.status_code == 401
        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 401


@pytest.mark.asyncio
async def test_deactivated_merchant_user_cannot_enter_merchant_operations(
    auth_service: AuthService,
    session: AsyncSession,
    hasher: PasswordHasher,
    jwt_config: JWTConfig,
) -> None:
    merchant_role = await _role(
        session,
        "merchant_owner",
        "merchants:read",
        "qr:create",
        "qr:read",
    )
    merchant = Merchant(
        name="Apex",
        contact_email="owner@apex.mw",
        contact_phone="+265991000000",
        is_active=True,
    )
    session.add(merchant)
    await session.flush()
    branch = Branch(merchant_id=merchant.id, name="Main", is_active=True)
    session.add(branch)
    await session.flush()
    till = Till(branch_id=branch.id, code="T1", name="Door", is_active=True)
    session.add(till)
    await session.commit()

    user = await _user(
        session,
        hasher,
        merchant_role,
        email="owner@apex.mw",
        merchant_id=merchant.id,
        branch_id=branch.id,
    )
    tokens, _ = await auth_service.login(user.email, PASSWORD)
    await auth_service.deactivate_account(user, PASSWORD, DEACTIVATION_CONFIRMATION)

    await session.refresh(user)
    assert user.merchant_id == merchant.id
    org = OrganizationService(session)
    access = await org.get_merchant_access(user)
    assert access["allowed"] is True
    assert access["merchant"].id == merchant.id

    application = _app(session, auth_service, jwt_config)
    headers = {"Authorization": f"Bearer {tokens.access_token}"}
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        merchants = await client.get("/api/v1/organization/merchants", headers=headers)
        assert merchants.status_code == 401
        mine = await client.get("/api/v1/organization/my-access", headers=headers)
        assert mine.status_code == 401


@pytest.mark.asyncio
async def test_customer_cannot_deactivate_another_account(
    auth_service: AuthService,
    session: AsyncSession,
    hasher: PasswordHasher,
    jwt_config: JWTConfig,
) -> None:
    role = await _role(session, "customer")
    alice = await _user(session, hasher, role, email="alice@example.com")
    bob = await _user(session, hasher, role, email="bob@example.com")
    tokens, _ = await auth_service.login(alice.email, PASSWORD)

    application = _app(session, auth_service, jwt_config)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/deactivate-account",
            headers={"Authorization": f"Bearer {tokens.access_token}"},
            json={"current_password": PASSWORD, "confirmation": DEACTIVATION_CONFIRMATION},
        )
        assert response.status_code == 204

    await session.refresh(alice)
    await session.refresh(bob)
    assert alice.account_status == AccountLifecycleStatus.DEACTIVATED.value
    assert bob.account_status == AccountLifecycleStatus.ACTIVE.value
    assert bob.can_authenticate is True


@pytest.mark.asyncio
async def test_reactivation_requires_fresh_token_and_password(
    auth_service: AuthService, session: AsyncSession, hasher: PasswordHasher
) -> None:
    role = await _role(session, "customer")
    user = await _user(session, hasher, role, email="react@example.com")
    old_tokens, _ = await auth_service.login(user.email, PASSWORD)
    await auth_service.deactivate_account(user, PASSWORD, DEACTIVATION_CONFIRMATION)

    with pytest.raises((InvalidTokenError, InactiveUserError, TokenReplayError)):
        await auth_service.refresh(old_tokens.refresh_token)

    none_token, _ = await auth_service.request_account_reactivation("nobody@example.com")
    assert none_token is None

    raw_token, _ = await auth_service.request_account_reactivation(user.email)
    assert raw_token is not None

    with pytest.raises(InvalidCredentialsError):
        await auth_service.reactivate_account(raw_token, "wrong-password")

    with pytest.raises(InvalidTokenError):
        await auth_service.reactivate_account(old_tokens.refresh_token, PASSWORD)

    tokens, restored = await auth_service.reactivate_account(raw_token, PASSWORD)
    assert restored.id == user.id
    await session.refresh(user)
    assert user.can_authenticate is True
    assert user.account_status == AccountLifecycleStatus.ACTIVE.value
    assert user.reactivated_at is not None
    me = await auth_service.get_current_user(tokens.access_token)
    assert me.id == user.id
    assert tokens.refresh_token != old_tokens.refresh_token


@pytest.mark.asyncio
async def test_reactivation_token_replay_and_expiry_fail(
    auth_service: AuthService, session: AsyncSession, hasher: PasswordHasher
) -> None:
    role = await _role(session, "customer")
    user = await _user(session, hasher, role, email="replay@example.com")
    await auth_service.deactivate_account(user, PASSWORD, DEACTIVATION_CONFIRMATION)
    raw_token, _ = await auth_service.request_account_reactivation(user.email)
    assert raw_token is not None
    await auth_service.reactivate_account(raw_token, PASSWORD)
    with pytest.raises(TokenReplayError):
        await auth_service.reactivate_account(raw_token, PASSWORD)

    await auth_service.deactivate_account(user, PASSWORD, DEACTIVATION_CONFIRMATION)
    expired, _ = await auth_service.request_account_reactivation(user.email)
    repo = AccountSecurityTokenRepository(session)
    record = await repo.get_latest_active_token(user.id, TOKEN_TYPE_ACCOUNT_REACTIVATION)
    assert record is not None
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await session.commit()
    with pytest.raises(TokenExpiredError):
        await auth_service.reactivate_account(expired, PASSWORD)


@pytest.mark.asyncio
async def test_account_history_remains_intact(
    auth_service: AuthService, session: AsyncSession, hasher: PasswordHasher
) -> None:
    role = await _role(session, "customer")
    user = await _user(session, hasher, role, email="history@example.com")
    prefs = CustomerPreference(user_id=user.id, preferred_mode="customer")
    session.add(prefs)
    await seed_provider_catalog(session)
    provider_row = (await session.scalars(select(PaymentProvider))).first()
    assert provider_row is not None
    instrument = PaymentInstrument(
        customer_id=user.id,
        provider_id=provider_row.id,
        public_identifier=f"pi_{uuid.uuid4().hex[:16]}",
        instrument_type=PaymentInstrumentType.MOBILE_MONEY,
        display_name="Airtel ****1234",
        masked_identifier="****1234",
        token_reference=f"tok_{uuid.uuid4().hex}",
        status=PaymentInstrumentStatus.ACTIVE,
        authorization_state=ProviderAuthorizationState.COMPLETED,
    )
    session.add(instrument)
    await session.commit()
    instrument_id = instrument.id

    await auth_service.deactivate_account(user, PASSWORD, DEACTIVATION_CONFIRMATION)
    await session.refresh(user)
    kept_prefs = await session.scalar(
        select(CustomerPreference).where(CustomerPreference.user_id == user.id)
    )
    kept_instrument = await session.get(PaymentInstrument, instrument_id)
    assert user.deleted_at is None
    assert kept_prefs is not None
    assert kept_instrument is not None
    assert kept_instrument.masked_identifier == "****1234"


@pytest.mark.asyncio
async def test_audit_events_recorded(
    auth_service: AuthService, session: AsyncSession, hasher: PasswordHasher
) -> None:
    role = await _role(session, "customer")
    user = await _user(session, hasher, role, email="audit@example.com")
    await auth_service.deactivate_account(user, PASSWORD, DEACTIVATION_CONFIRMATION)
    raw, _ = await auth_service.request_account_reactivation(user.email)
    await auth_service.reactivate_account(raw, PASSWORD)
    actions = set(
        (
            await session.scalars(
                select(AuditLog.action).where(AuditLog.entity_id == str(user.id))
            )
        ).all()
    )
    assert {
        "account_deactivated",
        "account_reactivation_requested",
        "account_reactivated",
    }.issubset(actions)


@pytest.mark.asyncio
async def test_suspended_accounts_remain_distinct(
    auth_service: AuthService, session: AsyncSession, hasher: PasswordHasher
) -> None:
    role = await _role(session, "customer")
    user = await _user(
        session,
        hasher,
        role,
        email="suspended@example.com",
        is_active=False,
        account_status=AccountLifecycleStatus.SUSPENDED.value,
    )
    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(user.email, PASSWORD)
    token, _ = await auth_service.request_account_reactivation(user.email)
    assert token is None
    with pytest.raises(AccountStateError):
        await auth_service.deactivate_account(user, PASSWORD, DEACTIVATION_CONFIRMATION)


@pytest.mark.asyncio
async def test_reactivation_http_contract_and_enumeration(
    auth_service: AuthService,
    session: AsyncSession,
    hasher: PasswordHasher,
    jwt_config: JWTConfig,
) -> None:
    role = await _role(session, "customer")
    user = await _user(session, hasher, role, email="http-life@example.com")
    tokens, _ = await auth_service.login(user.email, PASSWORD)
    application = _app(session, auth_service, jwt_config)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        bad_confirm = await client.post(
            "/api/v1/auth/deactivate-account",
            headers={"Authorization": f"Bearer {tokens.access_token}"},
            json={"current_password": PASSWORD, "confirmation": "please"},
        )
        assert bad_confirm.status_code == 400

        deactivated = await client.post(
            "/api/v1/auth/deactivate-account",
            headers={"Authorization": f"Bearer {tokens.access_token}"},
            json={"current_password": PASSWORD, "confirmation": DEACTIVATION_CONFIRMATION},
        )
        assert deactivated.status_code == 204

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": PASSWORD},
        )
        assert login.status_code == 403
        assert "deactivated" in login.json()["detail"].lower()

        unknown = await client.post(
            "/api/v1/auth/reactivate-account/request",
            json={"email": "missing@example.com"},
        )
        known = await client.post(
            "/api/v1/auth/reactivate-account/request",
            json={"email": user.email},
        )
        assert unknown.status_code == 200
        assert known.status_code == 200
        assert unknown.json()["detail"] == known.json()["detail"]

        repo = AccountSecurityTokenRepository(session)
        record = await repo.get_latest_active_token(user.id, TOKEN_TYPE_ACCOUNT_REACTIVATION)
        assert record is not None
        record.created_at = datetime.now(UTC) - timedelta(seconds=61)
        await session.commit()
        raw, _ = await auth_service.request_account_reactivation(user.email)
        assert raw is not None

        confirm = await client.post(
            "/api/v1/auth/reactivate-account",
            json={"token": raw, "password": PASSWORD},
        )
        assert confirm.status_code == 200
        body = confirm.json()
        assert body["access_token"]
        assert body["refresh_token"] != tokens.refresh_token

        me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert me.status_code == 200
        assert me.json()["account_status"] == "active"
