"""Password hashing utilities.

Uses the ``bcrypt`` library directly rather than passlib's ``CryptContext``
wrapper. Discovered while building M003: passlib (unmaintained since 2020)
is incompatible with modern bcrypt (>=4.1 dropped the ``__about__`` attribute
passlib's backend-detection probes for, and tightened 72-byte-secret
enforcement in a way that breaks passlib's own self-test) — see
docs/decisions.md, "Password hashing library". Calling ``bcrypt`` directly
avoids that entire fragile compatibility layer.
"""

from functools import lru_cache

import bcrypt

# bcrypt's underlying algorithm only uses the first 72 bytes of the input;
# recent bcrypt releases raise ValueError instead of silently truncating.
# We truncate ourselves so a long (but legitimate) password doesn't crash
# login instead of just having its extra bytes ignored, same as bcrypt's
# historical behavior.
_MAX_PASSWORD_BYTES = 72


class PasswordHasher:
    """Secure password hashing using bcrypt directly."""

    def hash(self, password: str) -> str:
        """Hash a plaintext password."""
        encoded = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
        return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a hash."""
        encoded = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
        try:
            return bcrypt.checkpw(encoded, hashed_password.encode("utf-8"))
        except ValueError:
            # Malformed/foreign hash format — never valid, never raise.
            return False


@lru_cache
def get_dummy_password_hash() -> str:
    """Return a fixed bcrypt hash to compare against on unknown-email login.

    Computed once per process (bcrypt hashing is deliberately slow). Running
    a verify against this constant when the email lookup misses keeps login
    latency roughly the same for "unknown email" and "wrong password", so a
    timing side-channel doesn't reveal which case occurred — see
    docs/decisions.md.
    """
    return PasswordHasher().hash("pompo-timing-safety-dummy-password")
