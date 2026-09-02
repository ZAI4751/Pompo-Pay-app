"""Least-privilege scopes for machine API clients.

These are independent of human RBAC permission codes. Human administrators
manage clients with ``api_keys:*``. POS/developer clients never receive
provider, RBAC, settlement, or reconciliation management.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationScopeDefinition:
    code: str
    description: str


INTEGRATION_SCOPES: tuple[IntegrationScopeDefinition, ...] = (
    IntegrationScopeDefinition("payments:create", "Create payment requests."),
    IntegrationScopeDefinition("payments:read", "Read payment status."),
    IntegrationScopeDefinition("qr:create", "Create dynamic QR checkout contexts."),
    IntegrationScopeDefinition("qr:read", "Read QR checkout contexts."),
    IntegrationScopeDefinition("transactions:read", "Read transaction status (alias of payments:read)."),
    IntegrationScopeDefinition("webhooks:read", "Read outbound webhook delivery status for this client."),
)

INTEGRATION_SCOPE_CODES = frozenset(scope.code for scope in INTEGRATION_SCOPES)

# Privileged human/admin capabilities that must never be assigned to POS clients.
FORBIDDEN_INTEGRATION_SCOPES = frozenset(
    {
        "providers:manage",
        "providers:create",
        "providers:update",
        "rbac:manage",
        "roles:create",
        "roles:update",
        "roles:delete",
        "role_permissions:grant",
        "role_permissions:revoke",
        "users:roles:assign",
        "users:roles:revoke",
        "settlements:manage",
        "settlements:create",
        "reconciliation:manage",
        "reconciliation:update",
    }
)

DEFAULT_POS_SCOPES: tuple[str, ...] = (
    "payments:create",
    "payments:read",
    "qr:create",
    "qr:read",
    "transactions:read",
    "webhooks:read",
)

DEFAULT_DEVELOPER_SCOPES: tuple[str, ...] = DEFAULT_POS_SCOPES
DEFAULT_PARTNER_SCOPES: tuple[str, ...] = DEFAULT_POS_SCOPES

READ_PAYMENT_SCOPES = frozenset({"payments:read", "transactions:read"})
CREATE_PAYMENT_SCOPES = frozenset({"payments:create"})
CREATE_QR_SCOPES = frozenset({"qr:create"})
READ_QR_SCOPES = frozenset({"qr:read", "qr:create"})
READ_WEBHOOK_SCOPES = frozenset({"webhooks:read"})


def normalize_scopes(scopes: list[str] | tuple[str, ...] | None, *, default: tuple[str, ...]) -> list[str]:
    """Return a de-duplicated, validated scope list."""

    raw = list(scopes) if scopes else list(default)
    normalized: list[str] = []
    seen: set[str] = set()
    unknown: list[str] = []
    forbidden: list[str] = []
    for code in raw:
        value = code.strip().lower()
        if not value:
            continue
        if value in FORBIDDEN_INTEGRATION_SCOPES:
            forbidden.append(value)
            continue
        if value not in INTEGRATION_SCOPE_CODES:
            unknown.append(value)
            continue
        if value not in seen:
            seen.add(value)
            normalized.append(value)
    if forbidden:
        raise ValueError(f"Forbidden integration scopes: {sorted(set(forbidden))}")
    if unknown:
        raise ValueError(f"Unknown integration scopes: {sorted(set(unknown))}")
    if not normalized:
        raise ValueError("At least one integration scope is required")
    return normalized


def has_scope(granted: list[str] | tuple[str, ...], required: frozenset[str] | str) -> bool:
    if isinstance(required, str):
        return required in granted
    return bool(required.intersection(granted))
