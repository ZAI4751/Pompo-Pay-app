"""AuthService tests: login, access tokens, refresh rotation, replay, logout, /me.

Runs against an in-memory SQLite database (same pattern as
tests/test_models.py) so it's fast and doesn't require a live PostgreSQL
instance. This is where the actual security-critical logic
(rotation/replay/expiry) is exercised — the thin API layer in
app/api/v1/auth.py just translates these exceptions to HTTP status codes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security.exceptions import (
    AccountDeactivatedError,
    AdminAccessDeniedError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    TokenReplayError,
)
from app.core.security.jwt import JWTConfig
from app.core.security.password import PasswordHasher
from app.models import Role, User
from app.models.auth import RefreshSession
from app.models.base import Base
from app.models.enums import AccountLifecycleStatus
from app.services.auth import AuthService, _hash_token


class _FakeSettings:
    """Minimal settings stub — JWTConfig only reads these four attributes."""

    jwt_secret_key = "unit-test-jwt-secret-key-minimum-32-chars"
    jwt_algorithm = "HS256"
    jwt_access_token_expire_minutes = 15
    jwt_refresh_token_expire_days = 7


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher()


@pytest.fixture
def jwt_config() -> JWTConfig:
    return JWTConfig(_FakeSettings())


@pytest.fixture
async def active_user(session: AsyncSession, hasher: PasswordHasher) -> User:
    role = Role(code="cashier", name="Cashier")
    user = User(
        role=role,
        email="grace@chikondi.mw",
        full_name="Grace Banda",
        hashed_password=hasher.hash("correct-horse-battery-staple"),
        is_active=True,
    )
    session.add_all([role, user])
    await session.commit()
    return user


@pytest.fixture
def auth_service(session: AsyncSession, jwt_config: JWTConfig, hasher: PasswordHasher) -> AuthService:
    return AuthService(session=session, jwt_config=jwt_config, password_hasher=hasher)


# ----------------------------------------------------------------------
# Passwords
# ----------------------------------------------------------------------


def test_password_hash_is_not_the_plaintext(hasher: PasswordHasher) -> None:
    hashed = hasher.hash("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert hashed.startswith("$2b$")  # bcrypt


def test_password_verify_accepts_correct_password(hasher: PasswordHasher) -> None:
    hashed = hasher.hash("correct-horse-battery-staple")
    assert hasher.verify("correct-horse-battery-staple", hashed) is True


def test_password_verify_rejects_incorrect_password(hasher: PasswordHasher) -> None:
    hashed = hasher.hash("correct-horse-battery-staple")
    assert hasher.verify("wrong-password", hashed) is False


# ----------------------------------------------------------------------
# Login
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_with_valid_credentials_succeeds(
    auth_service: AuthService, active_user: User
) -> None:
    tokens, user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.expires_in == 15 * 60
    assert user.id == active_user.id


@pytest.mark.asyncio
async def test_login_normalizes_email_case(
    auth_service: AuthService, active_user: User
) -> None:
    tokens, user = await auth_service.login("  Grace@Chikondi.MW  ", "correct-horse-battery-staple")
    assert user.id == active_user.id
    assert tokens.access_token


@pytest.mark.asyncio
async def test_login_with_wrong_password_raises_invalid_credentials(
    auth_service: AuthService, active_user: User
) -> None:
    with pytest.raises(InvalidCredentialsError):
        await auth_service.login("grace@chikondi.mw", "wrong-password")


@pytest.mark.asyncio
async def test_login_with_unknown_email_raises_invalid_credentials(
    auth_service: AuthService, active_user: User
) -> None:
    with pytest.raises(InvalidCredentialsError):
        await auth_service.login("nobody@chikondi.mw", "whatever-password")


@pytest.mark.asyncio
async def test_login_with_inactive_user_raises_invalid_credentials(
    session: AsyncSession, auth_service: AuthService, hasher: PasswordHasher
) -> None:
    role = Role(code="cashier2", name="Cashier")
    inactive_user = User(
        role=role,
        email="disabled@chikondi.mw",
        full_name="Disabled User",
        hashed_password=hasher.hash("some-password"),
        is_active=False,
    )
    session.add_all([role, inactive_user])
    await session.commit()

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login("disabled@chikondi.mw", "some-password")


@pytest.mark.asyncio
async def test_login_response_never_contains_password_hash(
    auth_service: AuthService, active_user: User
) -> None:
    from app.schemas.auth import AuthenticatedUserResponse

    tokens, user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    response = AuthenticatedUserResponse.model_validate(user)
    dumped = response.model_dump()
    assert "hashed_password" not in dumped
    assert "password" not in dumped


@pytest.mark.asyncio
async def test_login_persists_only_a_hash_of_the_refresh_token(
    session: AsyncSession, auth_service: AuthService, active_user: User
) -> None:
    tokens, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")

    from sqlalchemy import select

    result = await session.execute(select(RefreshSession))
    stored = result.scalars().all()
    assert len(stored) == 1
    assert stored[0].token_hash == _hash_token(tokens.refresh_token)
    assert stored[0].token_hash != tokens.refresh_token


# ----------------------------------------------------------------------
# Access tokens / get_current_user
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_with_valid_token_returns_user(
    auth_service: AuthService, active_user: User
) -> None:
    tokens, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    resolved = await auth_service.get_current_user(tokens.access_token)
    assert resolved.id == active_user.id


@pytest.mark.asyncio
async def test_get_current_user_with_malformed_token_raises(auth_service: AuthService) -> None:
    with pytest.raises(InvalidTokenError):
        await auth_service.get_current_user("not-a-real-jwt")


@pytest.mark.asyncio
async def test_get_current_user_with_expired_token_raises(
    auth_service: AuthService, active_user: User
) -> None:
    from jose import jwt as jose_jwt

    expired_payload = {
        "sub": str(active_user.id),
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    expired_token = jose_jwt.encode(
        expired_payload, _FakeSettings.jwt_secret_key, algorithm=_FakeSettings.jwt_algorithm
    )
    with pytest.raises(InvalidTokenError):
        await auth_service.get_current_user(expired_token)


@pytest.mark.asyncio
async def test_get_current_user_rejects_a_refresh_token(
    auth_service: AuthService, active_user: User
) -> None:
    tokens, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    with pytest.raises(InvalidTokenError):
        await auth_service.get_current_user(tokens.refresh_token)


@pytest.mark.asyncio
async def test_get_current_user_rejects_inactive_user(
    session: AsyncSession, auth_service: AuthService, active_user: User
) -> None:
    tokens, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    active_user.is_active = False
    await session.commit()

    with pytest.raises(InactiveUserError):
        await auth_service.get_current_user(tokens.access_token)


# ----------------------------------------------------------------------
# Refresh / rotation / replay
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_with_valid_token_issues_new_pair(
    auth_service: AuthService, active_user: User
) -> None:
    tokens, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    new_tokens, user = await auth_service.refresh(tokens.refresh_token)

    # Refresh tokens always differ (unique jti per session). Access tokens
    # only carry second-resolution exp/sub claims, so two issued within the
    # same wall-clock second are legitimately identical — that's harmless,
    # since both are equally valid until their shared natural expiry.
    assert new_tokens.refresh_token != tokens.refresh_token
    assert new_tokens.access_token  # still a well-formed, non-empty token
    assert user.id == active_user.id


@pytest.mark.asyncio
async def test_refresh_rotates_and_revokes_the_old_session(
    session: AsyncSession, auth_service: AuthService, active_user: User
) -> None:
    tokens, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    old_payload = auth_service._jwt_config.decode_token(tokens.refresh_token)
    old_session_id = uuid.UUID(old_payload["jti"])

    await auth_service.refresh(tokens.refresh_token)

    old_session = await session.get(RefreshSession, old_session_id)
    assert old_session is not None
    assert old_session.revoked_at is not None
    assert old_session.replaced_by_id is not None


@pytest.mark.asyncio
async def test_refresh_keeps_the_same_family_id_across_rotation(
    session: AsyncSession, auth_service: AuthService, active_user: User
) -> None:
    tokens, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    original_payload = auth_service._jwt_config.decode_token(tokens.refresh_token)
    original_session = await session.get(RefreshSession, uuid.UUID(original_payload["jti"]))

    new_tokens, _user = await auth_service.refresh(tokens.refresh_token)
    new_payload = auth_service._jwt_config.decode_token(new_tokens.refresh_token)
    new_session = await session.get(RefreshSession, uuid.UUID(new_payload["jti"]))

    assert new_session.family_id == original_session.family_id


@pytest.mark.asyncio
async def test_refresh_with_expired_session_raises(
    session: AsyncSession, auth_service: AuthService, active_user: User, jwt_config: JWTConfig
) -> None:
    session_id = uuid.uuid4()
    raw_token = jwt_config.create_refresh_token(subject=str(active_user.id), jti=str(session_id))
    expired_row = RefreshSession(
        id=session_id,
        user_id=active_user.id,
        family_id=session_id,
        token_hash=_hash_token(raw_token),
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
        expires_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    session.add(expired_row)
    await session.commit()

    with pytest.raises(TokenExpiredError):
        await auth_service.refresh(raw_token)


@pytest.mark.asyncio
async def test_refresh_replay_of_a_rotated_token_is_detected_and_revokes_family(
    session: AsyncSession, auth_service: AuthService, active_user: User
) -> None:
    tokens, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")

    # First use: legitimate rotation.
    second_tokens, _user = await auth_service.refresh(tokens.refresh_token)

    # Replay: reusing the already-rotated (now revoked) first refresh token.
    with pytest.raises(TokenReplayError):
        await auth_service.refresh(tokens.refresh_token)

    # The whole family — including the second (still "legitimate") token —
    # must now be revoked, since we can no longer tell attacker from owner.
    with pytest.raises((InvalidTokenError, TokenReplayError)):
        await auth_service.refresh(second_tokens.refresh_token)


@pytest.mark.asyncio
async def test_refresh_with_malformed_token_raises(auth_service: AuthService) -> None:
    with pytest.raises(InvalidTokenError):
        await auth_service.refresh("garbage-not-a-jwt")


@pytest.mark.asyncio
async def test_refresh_rejects_an_access_token(
    auth_service: AuthService, active_user: User
) -> None:
    tokens, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    with pytest.raises(InvalidTokenError):
        await auth_service.refresh(tokens.access_token)


# ----------------------------------------------------------------------
# Logout
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_revokes_the_session(
    session: AsyncSession, auth_service: AuthService, active_user: User
) -> None:
    tokens, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    payload = auth_service._jwt_config.decode_token(tokens.refresh_token)

    await auth_service.logout(tokens.refresh_token)

    stored = await session.get(RefreshSession, uuid.UUID(payload["jti"]))
    assert stored.revoked_at is not None


@pytest.mark.asyncio
async def test_refresh_reuse_after_logout_fails(
    auth_service: AuthService, active_user: User
) -> None:
    tokens, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    await auth_service.logout(tokens.refresh_token)

    with pytest.raises((InvalidTokenError, TokenReplayError)):
        await auth_service.refresh(tokens.refresh_token)


@pytest.mark.asyncio
async def test_logout_with_garbage_token_does_not_raise(auth_service: AuthService) -> None:
    await auth_service.logout("not-a-real-token")  # must not raise


@pytest.mark.asyncio
async def test_logout_is_idempotent(auth_service: AuthService, active_user: User) -> None:
    tokens, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    await auth_service.logout(tokens.refresh_token)
    await auth_service.logout(tokens.refresh_token)  # must not raise second time


@pytest.mark.asyncio
async def test_logout_then_fresh_login_issues_a_new_session(
    session: AsyncSession, auth_service: AuthService, active_user: User
) -> None:
    first, _user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    await auth_service.logout(first.refresh_token)
    second, user = await auth_service.login("grace@chikondi.mw", "correct-horse-battery-staple")
    assert user.id == active_user.id
    assert second.access_token
    assert second.refresh_token != first.refresh_token
    resolved = await auth_service.get_current_user(second.access_token)
    assert resolved.id == active_user.id


@pytest.fixture
async def platform_admin_user(session: AsyncSession, hasher: PasswordHasher) -> User:
    role = Role(code="platform_admin", name="Platform administrator", is_system_role=True)
    user = User(
        role=role,
        email="admin@pompo.mw",
        full_name="Platform Admin",
        hashed_password=hasher.hash("correct-horse-battery-staple"),
        is_active=True,
    )
    session.add_all([role, user])
    await session.commit()
    return user


@pytest.fixture
async def customer_user(session: AsyncSession, hasher: PasswordHasher) -> User:
    role = Role(code="customer", name="Customer")
    user = User(
        role=role,
        email="customer@chikondi.mw",
        full_name="Customer User",
        hashed_password=hasher.hash("correct-horse-battery-staple"),
        is_active=True,
    )
    session.add_all([role, user])
    await session.commit()
    return user


@pytest.fixture
async def merchant_user(session: AsyncSession, hasher: PasswordHasher) -> User:
    role = Role(code="merchant_owner", name="Merchant owner")
    user = User(
        role=role,
        email="owner@shop.mw",
        full_name="Merchant Owner",
        hashed_password=hasher.hash("correct-horse-battery-staple"),
        is_active=True,
    )
    session.add_all([role, user])
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_admin_login_issues_tokens_for_platform_admin(
    auth_service: AuthService, platform_admin_user: User
) -> None:
    tokens, user = await auth_service.admin_login(
        "admin@pompo.mw", "correct-horse-battery-staple"
    )
    assert user.id == platform_admin_user.id
    assert user.role.code == "platform_admin"
    assert tokens.access_token
    assert tokens.refresh_token
    resolved = await auth_service.get_current_user(tokens.access_token)
    assert resolved.id == platform_admin_user.id


@pytest.mark.asyncio
async def test_admin_login_rejects_customer_without_issuing_tokens(
    session: AsyncSession, auth_service: AuthService, customer_user: User
) -> None:
    with pytest.raises(AdminAccessDeniedError):
        await auth_service.admin_login("customer@chikondi.mw", "correct-horse-battery-staple")
    from sqlalchemy import select

    stored = (await session.execute(select(RefreshSession))).scalars().all()
    assert stored == []


@pytest.mark.asyncio
async def test_admin_login_rejects_merchant_without_issuing_tokens(
    session: AsyncSession, auth_service: AuthService, merchant_user: User
) -> None:
    with pytest.raises(AdminAccessDeniedError):
        await auth_service.admin_login("owner@shop.mw", "correct-horse-battery-staple")
    from sqlalchemy import select

    stored = (await session.execute(select(RefreshSession))).scalars().all()
    assert stored == []


@pytest.mark.asyncio
async def test_admin_login_unknown_email_is_invalid_credentials(
    auth_service: AuthService,
) -> None:
    with pytest.raises(InvalidCredentialsError):
        await auth_service.admin_login("nobody@pompo.mw", "whatever-password")


@pytest.mark.asyncio
async def test_admin_login_wrong_password_is_invalid_credentials(
    auth_service: AuthService, platform_admin_user: User
) -> None:
    with pytest.raises(InvalidCredentialsError):
        await auth_service.admin_login("admin@pompo.mw", "wrong-password")


@pytest.mark.asyncio
async def test_admin_login_deactivated_customer_is_denied_not_reactivated(
    session: AsyncSession, auth_service: AuthService, customer_user: User
) -> None:
    customer_user.account_status = AccountLifecycleStatus.DEACTIVATED.value
    await session.commit()
    with pytest.raises(AdminAccessDeniedError):
        await auth_service.admin_login("customer@chikondi.mw", "correct-horse-battery-staple")


@pytest.mark.asyncio
async def test_admin_login_deactivated_platform_admin_raises_deactivated(
    session: AsyncSession, auth_service: AuthService, platform_admin_user: User
) -> None:
    platform_admin_user.account_status = AccountLifecycleStatus.DEACTIVATED.value
    await session.commit()
    with pytest.raises(AccountDeactivatedError):
        await auth_service.admin_login("admin@pompo.mw", "correct-horse-battery-staple")


@pytest.mark.asyncio
async def test_customer_login_does_not_become_admin_session(
    auth_service: AuthService, customer_user: User, platform_admin_user: User
) -> None:
    customer_tokens, customer = await auth_service.login(
        "customer@chikondi.mw", "correct-horse-battery-staple"
    )
    assert customer.role.code == "customer"
    admin_tokens, admin = await auth_service.admin_login(
        "admin@pompo.mw", "correct-horse-battery-staple"
    )
    assert admin.role.code == "platform_admin"
    assert customer_tokens.refresh_token != admin_tokens.refresh_token
    resolved_customer = await auth_service.get_current_user(customer_tokens.access_token)
    resolved_admin = await auth_service.get_current_user(admin_tokens.access_token)
    assert resolved_customer.id == customer_user.id
    assert resolved_admin.id == platform_admin_user.id
