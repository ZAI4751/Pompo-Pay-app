"""Authentication service: login, token refresh/rotation, logout, current-user.

This is the application/service layer for M003. It contains all
authentication business logic and must not import anything from FastAPI —
the API layer (app/api/v1/auth.py) is responsible for translating the
exceptions raised here into HTTP responses.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security.exceptions import (
    AccountDeactivatedError,
    AccountStateError,
    AdminAccessDeniedError,
    InactiveUserError,
    InvalidConfirmationError,
    InvalidCredentialsError,
    InvalidTokenError,
    RateLimitAuthError,
    TokenExpiredError,
    TokenReplayError,
)
from app.core.security.jwt import JWTConfig
from app.core.security.password import PasswordHasher, get_dummy_password_hash
from app.models.audit import AuditLog
from app.models.auth import AccountSecurityToken, RefreshSession
from app.models.enums import AccountLifecycleStatus
from app.models.user import User
from app.repositories.auth import AccountSecurityTokenRepository, RefreshSessionRepository
from app.repositories.user import UserRepository
from app.services.email import EmailDispatcher

logger = get_logger(__name__)

DEACTIVATION_CONFIRMATION = "DEACTIVATE"
TOKEN_TYPE_ACCOUNT_REACTIVATION = "account_reactivation"
_SECURITY_TOKEN_TYPES_ON_DEACTIVATE = (
    "email_verification",
    "password_reset",
    TOKEN_TYPE_ACCOUNT_REACTIVATION,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Normalize a datetime read back from the DB to be timezone-aware UTC.

    SQLite (used in the unit-test suite) doesn't preserve tzinfo on
    ``DateTime(timezone=True)`` columns — a value written as UTC-aware comes
    back naive. PostgreSQL (production) does preserve it. We always write
    UTC-aware values, so treating a naive read-back as "already UTC" is
    correct on both backends and avoids a naive/aware comparison crash.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _hash_token(raw_token: str) -> str:
    """Return a SHA-256 hex digest of a raw JWT string.

    This is not a password hash (no need for salt/slow-hash here — the
    input already has 256+ bits of signature entropy); it exists purely so
    the raw refresh token is never persisted, per the design requirement.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _request_id() -> str | None:
    try:
        from structlog.contextvars import get_contextvars

        value = get_contextvars().get("request_id")
    except Exception:  # pragma: no cover - contextvars unavailable in some tests
        return None
    return str(value) if value else None


@dataclass(frozen=True)
class AuthTokens:
    """Access + refresh token pair returned by login/refresh."""

    access_token: str
    refresh_token: str
    expires_in: int
    is_email_verified: bool = False


class AuthService:
    """Authenticates users and manages the refresh-token session lifecycle."""

    def __init__(
        self,
        session: AsyncSession,
        jwt_config: JWTConfig,
        password_hasher: PasswordHasher,
        email_dispatcher: EmailDispatcher | None = None,
    ) -> None:
        self._session = session
        self._jwt_config = jwt_config
        self._password_hasher = password_hasher
        self._users = UserRepository(session)
        self._refresh_sessions = RefreshSessionRepository(session)
        self._security_tokens = AccountSecurityTokenRepository(session)
        self._email_dispatcher = email_dispatcher or EmailDispatcher()

    @property
    def access_token_expire_seconds(self) -> int:
        return self._jwt_config.access_token_expire_minutes * 60

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(
        self,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[AuthTokens, User]:
        """Verify credentials and issue a new access/refresh token pair.

        Unknown email and wrong password raise ``InvalidCredentialsError``.
        A correct password on a customer-deactivated account raises
        ``AccountDeactivatedError`` so the caller can offer reactivation
        without enumerating emails. Suspended/disabled accounts still
        collapse into the generic credentials error.
        """
        email = email.strip().lower()
        user = await self._users.get_by_email(email)

        if user is None:
            # Burn roughly the same time as a real verify so response
            # latency doesn't leak whether the email exists.
            self._password_hasher.verify(password, get_dummy_password_hash())
            raise InvalidCredentialsError("Unknown email")

        if not self._password_hasher.verify(password, user.hashed_password):
            raise InvalidCredentialsError("Incorrect password")

        if user.lifecycle_status is AccountLifecycleStatus.DEACTIVATED:
            raise AccountDeactivatedError("Account is deactivated")

        if not user.can_authenticate:
            raise InvalidCredentialsError("Account is inactive")

        user.last_login_at = _utcnow()
        tokens = await self._issue_new_session(
            user, family_id=None, user_agent=user_agent, ip_address=ip_address
        )
        await self._session.commit()
        return tokens, user

    async def admin_login(
        self,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[AuthTokens, User]:
        """Authenticate a platform administrator for Master Admin.

        Credential failures use the same generic path as ``login``. A
        correct password on a non-``platform_admin`` account raises
        ``AdminAccessDeniedError`` and does **not** issue tokens, so a
        customer cannot establish a Master Admin session. Deactivated
        platform admins still raise ``AccountDeactivatedError``.
        """
        email = email.strip().lower()
        user = await self._users.get_by_email(email)

        if user is None:
            self._password_hasher.verify(password, get_dummy_password_hash())
            raise InvalidCredentialsError("Unknown email")

        if not self._password_hasher.verify(password, user.hashed_password):
            raise InvalidCredentialsError("Incorrect password")

        role = user.role
        if role is None or role.code != "platform_admin":
            raise AdminAccessDeniedError("Account cannot access Master Admin")

        if user.lifecycle_status is AccountLifecycleStatus.DEACTIVATED:
            raise AccountDeactivatedError("Account is deactivated")

        if not user.can_authenticate:
            raise InvalidCredentialsError("Account is inactive")

        user.last_login_at = _utcnow()
        tokens = await self._issue_new_session(
            user, family_id=None, user_agent=user_agent, ip_address=ip_address
        )
        await self._session.commit()
        return tokens, user

    # ------------------------------------------------------------------
    # Refresh (with rotation + replay detection)
    # ------------------------------------------------------------------

    async def refresh(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[AuthTokens, User]:
        """Validate, rotate, and reissue a refresh token.

        Rotation: the presented session is revoked and a brand-new session
        (same ``family_id``) is created for the new refresh token. Replay
        detection: if the presented session was *already* revoked, someone
        is reusing a token we already rotated away from — the entire family
        is revoked in response, forcing re-login on every device sharing
        that lineage.
        """
        payload = self._decode(refresh_token, expected_type="refresh")

        jti = payload.get("jti")
        subject = payload.get("sub")
        if not jti or not subject:
            raise InvalidTokenError("Refresh token missing required claims")

        try:
            session_id = uuid.UUID(str(jti))
        except ValueError as exc:
            raise InvalidTokenError("Malformed session identifier") from exc

        session_row = await self._refresh_sessions.get_by_id(session_id)
        if session_row is None:
            raise InvalidTokenError("Unknown refresh session")

        if session_row.revoked_at is not None:
            await self._refresh_sessions.revoke_family(session_row.family_id)
            await self._session.commit()
            raise TokenReplayError("Refresh token reuse detected; session family revoked")

        if _as_utc(session_row.expires_at) < _utcnow():
            raise TokenExpiredError("Refresh session expired")

        if session_row.token_hash != _hash_token(refresh_token):
            # Valid signature and live session row, but the token bytes
            # don't match what we issued for this jti — treat as invalid
            # rather than trusting the claim alone.
            raise InvalidTokenError("Refresh token does not match session record")

        user = await self._users.get_active_by_id(session_row.user_id)
        if user is None:
            raise InvalidTokenError("User no longer exists")
        if not user.can_authenticate:
            raise InactiveUserError("Account is inactive")

        session_row.revoked_at = _utcnow()
        new_session_id = uuid.uuid4()

        tokens = await self._issue_new_session(
            user,
            family_id=session_row.family_id,
            user_agent=user_agent,
            ip_address=ip_address,
            session_id=new_session_id,
        )
        # Only point the old row at its successor once that successor
        # actually exists in the database. Setting replaced_by_id before
        # the new row is inserted works fine under SQLite (no FK
        # enforcement) but violates refresh_sessions_replaced_by_id_fkey
        # under PostgreSQL, since flush would try to UPDATE this row to
        # reference an id that hasn't been INSERTed yet in the same flush.
        session_row.replaced_by_id = new_session_id

        await self._session.commit()
        return tokens, user

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    async def logout(self, refresh_token: str) -> None:
        """Revoke the session behind a refresh token.

        Intentionally silent/idempotent on any failure (malformed token,
        unknown session, already revoked) — logout should never leak
        whether a token was valid, and calling it twice must not error.
        Access tokens are not revocable server-side; they simply expire
        (see docs/decisions.md, "Logout and access tokens").
        """
        try:
            payload = self._decode(refresh_token, expected_type="refresh")
        except (InvalidTokenError, TokenExpiredError):
            return

        jti = payload.get("jti")
        if not jti:
            return

        try:
            session_id = uuid.UUID(str(jti))
        except ValueError:
            return

        session_row = await self._refresh_sessions.get_by_id(session_id)
        if session_row is not None and session_row.revoked_at is None:
            session_row.revoked_at = _utcnow()
            await self._session.commit()

    async def issue_session_tokens(
        self,
        user: User,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthTokens:
        """Issue a refresh session without committing. Used by registration."""
        return await self._issue_new_session(
            user, family_id=None, user_agent=user_agent, ip_address=ip_address
        )

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        """Replace the password hash after verifying the current password."""
        if not self._password_hasher.verify(current_password, user.hashed_password):
            raise InvalidCredentialsError("Incorrect password")
        user.hashed_password = self._password_hasher.hash(new_password)
        await self._refresh_sessions.revoke_all_for_user(user.id)
        await self._session.commit()

    async def logout_all(self, user: User) -> None:
        """Revoke every refresh session for the user."""
        await self._refresh_sessions.revoke_all_for_user(user.id)
        await self._session.commit()

    async def deactivate_account(
        self,
        user: User,
        current_password: str,
        confirmation: str,
        *,
        ip_address: str | None = None,
    ) -> None:
        """Deactivate the signed-in account after password + confirmation.

        Sets lifecycle DEACTIVATED, clears ``is_active``, revokes every
        refresh session, and invalidates outstanding security tokens.
        Transaction, receipt, settlement, and merchant membership rows
        are left intact.
        """
        if confirmation.strip() != DEACTIVATION_CONFIRMATION:
            raise InvalidConfirmationError("Confirmation does not match")
        if not self._password_hasher.verify(current_password, user.hashed_password):
            raise InvalidCredentialsError("Incorrect password")
        if user.lifecycle_status is AccountLifecycleStatus.SUSPENDED or (
            not user.is_active and user.lifecycle_status is not AccountLifecycleStatus.DEACTIVATED
        ):
            raise AccountStateError("Account cannot be self-deactivated")
        if user.lifecycle_status is AccountLifecycleStatus.DEACTIVATED:
            raise AccountStateError("Account is already deactivated")

        now = _utcnow()
        before = {
            "is_active": user.is_active,
            "account_status": user.account_status,
        }
        user.account_status = AccountLifecycleStatus.DEACTIVATED.value
        user.is_active = False
        user.deactivated_at = now
        await self._refresh_sessions.revoke_all_for_user(user.id)
        for token_type in _SECURITY_TOKEN_TYPES_ON_DEACTIVATE:
            await self._security_tokens.invalidate_all_for_user(user.id, token_type)
        self._session.add(
            AuditLog(
                created_at=now,
                actor_user_id=user.id,
                merchant_id=user.merchant_id,
                action="account_deactivated",
                entity_type="user",
                entity_id=str(user.id),
                before_state=before,
                after_state={
                    "is_active": False,
                    "account_status": AccountLifecycleStatus.DEACTIVATED.value,
                    "source": "self_service",
                    "request_id": _request_id(),
                },
                ip_address=ip_address,
            )
        )
        await self._session.commit()
        logger.info("account_deactivated", user_id=str(user.id))

    async def request_account_reactivation(
        self,
        email: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str | None, dict[str, Any]]:
        """Issue a one-time reactivation token if the account is deactivated.

        Always behaves the same to the caller for unknown, active, and
        suspended accounts so emails cannot be enumerated.
        """
        normalized_email = email.strip().lower()
        user = await self._users.get_by_email(normalized_email)
        if user is None or user.lifecycle_status is not AccountLifecycleStatus.DEACTIVATED:
            self._password_hasher.verify("dummy_password", get_dummy_password_hash())
            return None, {"status": "not_configured"}

        latest = await self._security_tokens.get_latest_active_token(
            user.id, TOKEN_TYPE_ACCOUNT_REACTIVATION
        )
        if latest is not None and _utcnow() - _as_utc(latest.created_at) < timedelta(seconds=60):
            return None, {"status": "cooldown"}

        await self._security_tokens.invalidate_all_for_user(
            user.id, TOKEN_TYPE_ACCOUNT_REACTIVATION
        )

        raw_token = secrets.token_urlsafe(32)
        now = _utcnow()
        token_record = AccountSecurityToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_type=TOKEN_TYPE_ACCOUNT_REACTIVATION,
            token_hash=_hash_token(raw_token),
            created_at=now,
            expires_at=now + timedelta(hours=1),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self._security_tokens.add(token_record)
        dispatch_result = await self._email_dispatcher.send_account_reactivation_email(
            recipient_email=user.email,
            user_name=user.full_name,
            reactivation_link=f"/reactivate?token={raw_token}",
        )
        self._session.add(
            AuditLog(
                created_at=now,
                actor_user_id=user.id,
                merchant_id=user.merchant_id,
                action="account_reactivation_requested",
                entity_type="user",
                entity_id=str(user.id),
                before_state={"account_status": user.account_status},
                after_state={
                    "source": "self_service",
                    "request_id": _request_id(),
                },
                ip_address=ip_address,
            )
        )
        await self._session.commit()
        return raw_token, dispatch_result

    async def reactivate_account(
        self,
        raw_token: str,
        password: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[AuthTokens, User]:
        """Reactivate a deactivated account with a one-time token and password.

        Issues a fresh session. Old refresh tokens remain revoked.
        """
        token_hash = _hash_token(raw_token.strip())
        record = await self._security_tokens.get_by_hash_and_type(
            token_hash, TOKEN_TYPE_ACCOUNT_REACTIVATION
        )
        if record is None:
            raise InvalidTokenError("Invalid or expired reactivation token")

        if record.used_at is not None:
            raise TokenReplayError("Reactivation token has already been used")

        if _as_utc(record.expires_at) < _utcnow():
            raise TokenExpiredError("Reactivation token has expired")

        user = await self._users.get_active_by_id(record.user_id)
        if user is None:
            raise InvalidTokenError("Invalid or expired reactivation token")

        if user.lifecycle_status is AccountLifecycleStatus.SUSPENDED:
            raise InvalidTokenError("Invalid or expired reactivation token")

        if user.lifecycle_status is AccountLifecycleStatus.ACTIVE:
            raise AccountStateError("Account is already active")

        if user.lifecycle_status is not AccountLifecycleStatus.DEACTIVATED:
            raise AccountStateError("Account cannot be reactivated")

        if not self._password_hasher.verify(password, user.hashed_password):
            raise InvalidCredentialsError("Incorrect password")

        now = _utcnow()
        before = {
            "is_active": user.is_active,
            "account_status": user.account_status,
        }
        record.used_at = now
        user.account_status = AccountLifecycleStatus.ACTIVE.value
        user.is_active = True
        user.reactivated_at = now
        user.last_login_at = now
        await self._refresh_sessions.revoke_all_for_user(user.id)
        await self._security_tokens.invalidate_all_for_user(
            user.id, TOKEN_TYPE_ACCOUNT_REACTIVATION
        )
        tokens = await self._issue_new_session(
            user, family_id=None, user_agent=user_agent, ip_address=ip_address
        )
        self._session.add(
            AuditLog(
                created_at=now,
                actor_user_id=user.id,
                merchant_id=user.merchant_id,
                action="account_reactivated",
                entity_type="user",
                entity_id=str(user.id),
                before_state=before,
                after_state={
                    "is_active": True,
                    "account_status": AccountLifecycleStatus.ACTIVE.value,
                    "source": "self_service",
                    "request_id": _request_id(),
                },
                ip_address=ip_address,
            )
        )
        await self._session.commit()
        logger.info("account_reactivated", user_id=str(user.id))
        return tokens, user

    # ------------------------------------------------------------------
    # Current user (access token -> User)
    # ------------------------------------------------------------------

    async def get_current_user(self, access_token: str) -> User:
        """Resolve the authenticated user from a bearer access token."""
        payload = self._decode(access_token, expected_type="access")

        subject = payload.get("sub")
        if not subject:
            raise InvalidTokenError("Access token missing subject claim")

        try:
            user_id = uuid.UUID(str(subject))
        except ValueError as exc:
            raise InvalidTokenError("Malformed subject claim") from exc

        user = await self._users.get_active_by_id(user_id)
        if user is None:
            raise InvalidTokenError("User no longer exists")
        if not user.can_authenticate:
            raise InactiveUserError("Account is inactive")
        return user

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _decode(self, token: str, expected_type: str) -> dict:
        try:
            payload = self._jwt_config.decode_token(token)
        except ValueError as exc:
            # JWTConfig.decode_token collapses jose's ExpiredSignatureError
            # and every other JWTError into one ValueError. We don't
            # currently need to tell "expired" apart from "malformed" for
            # access/refresh decoding here (both fail the same way for the
            # caller), so both map to InvalidTokenError at this boundary.
            raise InvalidTokenError("Token failed validation") from exc

        if payload.get("type") != expected_type:
            raise InvalidTokenError(f"Expected a {expected_type} token")
        return payload

    async def _issue_new_session(
        self,
        user: User,
        *,
        family_id: uuid.UUID | None,
        user_agent: str | None,
        ip_address: str | None,
        session_id: uuid.UUID | None = None,
    ) -> AuthTokens:
        session_id = session_id or uuid.uuid4()
        resolved_family_id = family_id or session_id

        access_token = self._jwt_config.create_access_token(subject=str(user.id))
        refresh_token = self._jwt_config.create_refresh_token(
            subject=str(user.id), jti=str(session_id)
        )

        refresh_session = RefreshSession(
            id=session_id,
            user_id=user.id,
            family_id=resolved_family_id,
            token_hash=_hash_token(refresh_token),
            created_at=_utcnow(),
            expires_at=_utcnow() + timedelta(days=self._jwt_config.refresh_token_expire_days),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self._refresh_sessions.add(refresh_session)

        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_seconds,
            is_email_verified=user.is_email_verified,
        )

    # ------------------------------------------------------------------
    # Email Verification
    # ------------------------------------------------------------------

    async def request_email_verification(
        self,
        user: User,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Generate a verification token and dispatch email via dispatcher.

        Enforces a 60-second cooldown between requests to prevent spam.
        Returns the raw token (for testing/dispatch) and dispatch status.
        """
        latest = await self._security_tokens.get_latest_active_token(
            user.id, "email_verification"
        )
        if latest is not None:
            created_at = _as_utc(latest.created_at)
            if _utcnow() - created_at < timedelta(seconds=60):
                raise RateLimitAuthError("Please wait 60 seconds before requesting another verification email")

        await self._security_tokens.invalidate_all_for_user(user.id, "email_verification")

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        now = _utcnow()
        expires_at = now + timedelta(hours=24)

        token_record = AccountSecurityToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_type="email_verification",
            token_hash=token_hash,
            created_at=now,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self._security_tokens.add(token_record)

        dispatch_result = await self._email_dispatcher.send_verification_email(
            recipient_email=user.email,
            user_name=user.full_name,
            verification_link=f"/verify-email?token={raw_token}",
        )
        await self._session.commit()
        return raw_token, dispatch_result

    async def verify_email(self, raw_token: str) -> User:
        """Verify an account email with a single-use token."""
        token_hash = _hash_token(raw_token.strip())
        record = await self._security_tokens.get_by_hash_and_type(
            token_hash, "email_verification"
        )
        if record is None:
            raise InvalidTokenError("Invalid verification token")

        if record.used_at is not None:
            raise TokenReplayError("Verification token has already been used")

        if _as_utc(record.expires_at) < _utcnow():
            raise TokenExpiredError("Verification token has expired")

        user = await self._users.get_active_by_id(record.user_id)
        if user is None or not user.can_authenticate:
            raise InvalidTokenError("Account is inactive or not found")

        record.used_at = _utcnow()
        user.is_email_verified = True
        user.email_verified_at = _utcnow()
        await self._session.commit()
        return user

    # ------------------------------------------------------------------
    # Password Reset
    # ------------------------------------------------------------------

    async def request_password_reset(
        self,
        email: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str | None, dict[str, Any]]:
        """Generate a one-time password reset token and dispatch email.

        Constant-time failure to prevent email enumeration.
        """
        normalized_email = email.strip().lower()
        user = await self._users.get_by_email(normalized_email)
        if user is None or not user.can_authenticate:
            self._password_hasher.verify("dummy_password", get_dummy_password_hash())
            return None, {"status": "not_configured"}

        latest = await self._security_tokens.get_latest_active_token(
            user.id, "password_reset"
        )
        if latest is not None and _utcnow() - _as_utc(latest.created_at) < timedelta(seconds=60):
            return None, {"status": "cooldown"}

        await self._security_tokens.invalidate_all_for_user(user.id, "password_reset")

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        now = _utcnow()
        expires_at = now + timedelta(hours=1)

        token_record = AccountSecurityToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_type="password_reset",
            token_hash=token_hash,
            created_at=now,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self._security_tokens.add(token_record)

        dispatch_result = await self._email_dispatcher.send_password_reset_email(
            recipient_email=user.email,
            user_name=user.full_name,
            reset_link=f"/reset-password?token={raw_token}",
        )
        await self._session.commit()
        return raw_token, dispatch_result

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        """Reset user password, invalidating token and all active refresh sessions."""
        token_hash = _hash_token(raw_token.strip())
        record = await self._security_tokens.get_by_hash_and_type(
            token_hash, "password_reset"
        )
        if record is None:
            raise InvalidTokenError("Invalid or expired password reset token")

        if record.used_at is not None:
            raise TokenReplayError("Password reset token has already been used")

        if _as_utc(record.expires_at) < _utcnow():
            raise TokenExpiredError("Password reset token has expired")

        user = await self._users.get_active_by_id(record.user_id)
        if user is None or not user.can_authenticate:
            raise InvalidTokenError("Account is inactive or not found")

        record.used_at = _utcnow()
        user.hashed_password = self._password_hasher.hash(new_password)
        await self._refresh_sessions.revoke_all_for_user(user.id)
        await self._session.commit()
