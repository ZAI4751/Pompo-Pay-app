"""JWT configuration and token utilities."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.config.base import BaseAppSettings


class JWTConfig:
    """JWT token configuration and encoding/decoding utilities."""

    def __init__(self, settings: BaseAppSettings) -> None:
        self._secret_key = settings.jwt_secret_key
        self._algorithm = settings.jwt_algorithm
        self._access_expire_minutes = settings.jwt_access_token_expire_minutes
        self._refresh_expire_days = settings.jwt_refresh_token_expire_days

    @property
    def algorithm(self) -> str:
        """Return the configured JWT signing algorithm."""
        return self._algorithm

    @property
    def access_token_expire_minutes(self) -> int:
        """Return access token expiry in minutes."""
        return self._access_expire_minutes

    @property
    def refresh_token_expire_days(self) -> int:
        """Return refresh token expiry in days."""
        return self._refresh_expire_days

    def create_access_token(
        self,
        subject: str,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """Create a signed JWT access token."""
        expire = datetime.now(UTC) + timedelta(minutes=self._access_expire_minutes)
        payload: dict[str, Any] = {
            "sub": subject,
            "exp": expire,
            "type": "access",
        }
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(self, subject: str, jti: str) -> str:
        """Create a signed JWT refresh token.

        ``jti`` must be the primary key of the corresponding
        ``RefreshSession`` row (see app/models/auth.py) — it is how
        ``AuthService`` maps a presented token back to its server-side
        session for revocation, rotation, and replay detection. The JWT
        signature alone only proves the token was issued by us; the session
        lookup is what lets us revoke it before its natural expiry.
        """
        expire = datetime.now(UTC) + timedelta(days=self._refresh_expire_days)
        payload: dict[str, Any] = {
            "sub": subject,
            "exp": expire,
            "type": "refresh",
            "jti": jti,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT token."""
        try:
            return jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except JWTError as exc:
            raise ValueError("Invalid or expired token") from exc
