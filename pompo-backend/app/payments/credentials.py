"""Secure provider credential and rail-environment resolution.

Secrets stay in the process environment (or a secret manager that injects
environment variables). This module never logs or returns secret values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.core.config.base import AppEnvironment, get_settings
from app.payments.config import DEFAULT_PROVIDER_TIMEOUT_SECONDS, provider_env_key


class ProviderEnvironmentError(RuntimeError):
    """Raised when a production rail would run outside production."""


def normalize_rail_environment(value: str | None) -> str:
    raw = (value or "sandbox").strip().lower()
    if raw in {"live", "production", "prod"}:
        return "production"
    return "sandbox"


def production_rails_permitted(app_env: AppEnvironment | None = None) -> bool:
    env = app_env or get_settings().app_env
    return env is AppEnvironment.PRODUCTION


def assert_rail_environment_allowed(rail_environment: str, app_env: AppEnvironment | None = None) -> None:
    if normalize_rail_environment(rail_environment) == "production" and not production_rails_permitted(
        app_env
    ):
        raise ProviderEnvironmentError(
            "Production provider rails cannot be used outside APP_ENV=production"
        )


@dataclass
class ProviderCredentials:
    """Resolved credential *presence* plus a private secret handle."""

    code: str
    rail_environment: str
    client_id: str | None
    timeout_seconds: int
    base_url: str | None
    _secret: str | None
    _webhook_secret: str | None

    @property
    def secret_configured(self) -> bool:
        return bool(self._secret)

    @property
    def webhook_secret_configured(self) -> bool:
        return bool(self._webhook_secret)

    @property
    def configuration_complete(self) -> bool:
        return bool(self.base_url and self._secret)

    def secret(self) -> str | None:
        return self._secret

    def webhook_secret(self) -> str | None:
        return self._webhook_secret

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ProviderCredentials(code={self.code!r}, rail_environment={self.rail_environment!r}, "
            f"secret_configured={self.secret_configured}, "
            f"webhook_secret_configured={self.webhook_secret_configured})"
        )


def _present(name: str | None) -> str | None:
    if not name:
        return None
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def resolve_provider_credentials(
    code: str,
    *,
    catalog_environment: str = "sandbox",
    app_env: AppEnvironment | None = None,
) -> ProviderCredentials:
    env_override = _present(provider_env_key(code, "ENVIRONMENT"))
    rail_environment = normalize_rail_environment(env_override or catalog_environment)
    timeout_raw = _present(provider_env_key(code, "TIMEOUT_SECONDS"))
    try:
        timeout_seconds = int(timeout_raw) if timeout_raw else DEFAULT_PROVIDER_TIMEOUT_SECONDS
    except ValueError:
        timeout_seconds = DEFAULT_PROVIDER_TIMEOUT_SECONDS
    timeout_seconds = max(1, min(timeout_seconds, 120))

    credential_ref = _present(provider_env_key(code, "CREDENTIAL_REF"))
    webhook_ref = _present(provider_env_key(code, "WEBHOOK_SECRET_REF"))
    credentials = ProviderCredentials(
        code=code,
        rail_environment=rail_environment,
        client_id=_present(provider_env_key(code, "CLIENT_ID")),
        timeout_seconds=timeout_seconds,
        base_url=_present(provider_env_key(code, "BASE_URL")),
        _secret=_present(credential_ref),
        _webhook_secret=_present(webhook_ref),
    )
    if credentials.base_url or credentials.secret_configured:
        assert_rail_environment_allowed(rail_environment, app_env)
    return credentials
