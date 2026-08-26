"""Authentication domain exceptions.

Raised by ``app.services.auth.AuthService``. The API layer (app/api/v1/auth.py)
catches these and maps them to HTTP responses — the service layer itself
must not depend on FastAPI, per the project's layering rules.

Deliberately coarse-grained on purpose in most call sites: login collapses
unknown-email, wrong-password, and inactive-account into the same
``InvalidCredentialsError`` / generic response so the API never reveals
*why* a login failed (see docs/decisions.md, "Authentication enumeration").
The distinct exception types below exist so internal logging can still tell
these apart even though the client-facing message doesn't.
"""

from __future__ import annotations


class AuthError(Exception):
    """Base class for all authentication failures."""


class InvalidCredentialsError(AuthError):
    """Email/password combination did not authenticate."""


class InactiveUserError(AuthError):
    """The user account exists but is disabled."""


class InvalidTokenError(AuthError):
    """A token (access or refresh) failed signature, shape, or lookup validation."""


class TokenExpiredError(AuthError):
    """A token was structurally valid but has expired."""


class TokenReplayError(AuthError):
    """A previously-rotated (already-revoked) refresh token was presented again."""
