"""Authentication service: login, token refresh/rotation, logout, current-user.

This is the application/service layer for M003. It contains all
authentication business logic and must not import anything from FastAPI —
the API layer (app/api/v1/auth.py) is responsible for translating the
exceptions raised here into HTTP responses.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    TokenReplayError,
)
from app.core.security.jwt import JWTConfig
from app.core.security.password import PasswordHasher, get_dummy_password_hash
from app.models.auth import RefreshSession
from app.models.user import User
from app.repositories.auth import RefreshSessionRepository
from app.repositories.user import UserRepository


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


@dataclass(frozen=True)
class AuthTokens:
    """Access + refresh token pair returned by login/refresh."""

    access_token: str
    refresh_token: str
    expires_in: int


class AuthService:
    """Authenticates users and manages the refresh-token session lifecycle."""

    def __init__(
        self, session: AsyncSession, jwt_config: JWTConfig, password_hasher: PasswordHasher
    ) -> None:
        self._session = session
        self._jwt_config = jwt_config
        self._password_hasher = password_hasher
        self._users = UserRepository(session)
        self._refresh_sessions = RefreshSessionRepository(session)

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

        Raises ``InvalidCredentialsError`` for unknown email, wrong
        password, AND disabled accounts alike — deliberately, so the API
        response can't be used to enumerate which case occurred.
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

        if not user.is_active:
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
        if not user.is_active:
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
        if not user.is_active:
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
        )
