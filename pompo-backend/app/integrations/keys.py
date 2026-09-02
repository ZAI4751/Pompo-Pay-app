"""API key generation and hashing. Plaintext is never persisted."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from uuid import UUID

from app.models.enums import APIClientEnvironment

KEY_PREFIX_LENGTH = 16
WEBHOOK_SECRET_PREFIX_LENGTH = 12


def hash_secret(secret_key: str, value: str) -> str:
    """HMAC-SHA256 digest suitable for unique lookup and timing-safe compare."""

    return hmac.new(secret_key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_api_key(environment: APIClientEnvironment | str) -> str:
    """Issue a high-entropy key with an operational prefix.

    Format: ``pompo_{test|live}_{48 hex chars}``. Only the hash is stored.
    """

    env = (
        environment.value
        if isinstance(environment, APIClientEnvironment)
        else str(environment)
    )
    stamp = "live" if env == APIClientEnvironment.LIVE.value else "test"
    return f"pompo_{stamp}_{secrets.token_hex(24)}"


def key_prefix(raw_key: str) -> str:
    return raw_key[:KEY_PREFIX_LENGTH]


def looks_like_api_key(value: str | None) -> bool:
    if not value:
        return False
    return value.startswith("pompo_test_") or value.startswith("pompo_live_")


def dummy_api_key_hash(secret_key: str) -> str:
    return hash_secret(secret_key, "pompo-timing-safety-dummy-api-key")


def generate_client_public_id() -> str:
    return f"app_{secrets.token_hex(8)}"


def derive_webhook_secret(secret_key: str, client_id: UUID, version: int) -> str:
    """Recomputable partner signing secret. Not stored; shown once per version."""

    material = f"pompo-webhook-v{version}:{client_id}".encode("utf-8")
    digest = hmac.new(secret_key.encode("utf-8"), material, hashlib.sha256).digest()
    return "whsec_" + digest.hex()


def webhook_secret_prefix(raw_secret: str) -> str:
    return raw_secret[:WEBHOOK_SECRET_PREFIX_LENGTH]
