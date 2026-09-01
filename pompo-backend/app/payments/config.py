"""Provider runtime configuration resolved from environment references.

Secrets are never stored in the catalog. This module only reads environment
variable *names* (references) and whether the named secret is present. Values
are never logged or returned to API callers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_PROVIDER_TIMEOUT_SECONDS = 15


def provider_env_key(code: str, suffix: str) -> str:
    return f"PROVIDER_{code.upper()}_{suffix}"


@dataclass(frozen=True)
class ProviderRuntimeConfig:
    code: str
    base_url_configured: bool
    timeout_seconds: int
    secrets_configured: bool
    webhook_signing_configured: bool
    configuration_complete: bool


def _truthy_present(name: str | None) -> bool:
    if not name:
        return False
    value = os.environ.get(name)
    return bool(value and value.strip())


def resolve_provider_runtime_config(code: str, *, simulated: bool) -> ProviderRuntimeConfig:
    timeout_raw = os.environ.get(provider_env_key(code, "TIMEOUT_SECONDS"))
    try:
        timeout_seconds = int(timeout_raw) if timeout_raw else DEFAULT_PROVIDER_TIMEOUT_SECONDS
    except ValueError:
        timeout_seconds = DEFAULT_PROVIDER_TIMEOUT_SECONDS
    timeout_seconds = max(1, min(timeout_seconds, 120))

    base_url_configured = _truthy_present(provider_env_key(code, "BASE_URL"))
    credential_ref = os.environ.get(provider_env_key(code, "CREDENTIAL_REF"), "").strip() or None
    webhook_ref = os.environ.get(provider_env_key(code, "WEBHOOK_SECRET_REF"), "").strip() or None
    secrets_configured = _truthy_present(credential_ref)
    webhook_signing_configured = _truthy_present(webhook_ref)

    if simulated:
        configuration_complete = True
    else:
        configuration_complete = base_url_configured and secrets_configured

    return ProviderRuntimeConfig(
        code=code,
        base_url_configured=base_url_configured,
        timeout_seconds=timeout_seconds,
        secrets_configured=secrets_configured,
        webhook_signing_configured=webhook_signing_configured,
        configuration_complete=configuration_complete,
    )
