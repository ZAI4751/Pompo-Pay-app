"""Stable RBAC permission and system-role definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDefinition:
    """A database-backed permission contract."""

    code: str
    description: str


PERMISSIONS: tuple[PermissionDefinition, ...] = (
    PermissionDefinition("users:read", "View users."),
    PermissionDefinition("users:create", "Create users."),
    PermissionDefinition("users:update", "Update users."),
    PermissionDefinition("users:delete", "Deactivate users."),
    PermissionDefinition("roles:read", "View roles."),
    PermissionDefinition("roles:create", "Create custom roles."),
    PermissionDefinition("roles:update", "Update custom roles."),
    PermissionDefinition("roles:delete", "Deactivate custom roles."),
    PermissionDefinition("permissions:read", "View registered permissions."),
    PermissionDefinition("role_permissions:grant", "Grant permissions to roles."),
    PermissionDefinition("role_permissions:revoke", "Revoke permissions from roles."),
    PermissionDefinition("users:roles:assign", "Assign roles to users."),
    PermissionDefinition("users:roles:revoke", "Remove roles from users."),
    PermissionDefinition("merchants:read", "View merchants."),
    PermissionDefinition("merchants:create", "Create merchants."),
    PermissionDefinition("merchants:update", "Update merchants."),
    PermissionDefinition("merchants:delete", "Deactivate merchants."),
    PermissionDefinition("branches:read", "View branches."),
    PermissionDefinition("branches:create", "Create branches."),
    PermissionDefinition("branches:update", "Update branches."),
    PermissionDefinition("branches:delete", "Deactivate branches."),
    PermissionDefinition("tills:read", "View tills."),
    PermissionDefinition("tills:create", "Create tills."),
    PermissionDefinition("tills:update", "Update tills."),
    PermissionDefinition("tills:delete", "Deactivate tills."),
    PermissionDefinition("providers:read", "View the payment provider catalog."),
    PermissionDefinition("providers:update", "Enable, disable, or prioritize payment providers."),
    PermissionDefinition("transactions:read", "View transactions."),
    PermissionDefinition("transactions:create", "Create transactions."),
    PermissionDefinition("transactions:update", "Update transactions."),
    PermissionDefinition("transactions:cancel", "Cancel transactions."),
    PermissionDefinition("transactions:refund", "Refund transactions."),
    PermissionDefinition("reports:read", "View reports."),
    PermissionDefinition("reports:export", "Export reports."),
    PermissionDefinition("api_keys:read", "View API keys."),
    PermissionDefinition("api_keys:create", "Create API keys."),
    PermissionDefinition("api_keys:revoke", "Revoke API keys."),
)

PERMISSION_BY_CODE = {permission.code: permission for permission in PERMISSIONS}


SYSTEM_ROLES: dict[str, tuple[str, str, frozenset[str]]] = {
    "platform_admin": (
        "Platform administrator",
        "Full platform administration through explicit permissions.",
        frozenset(permission.code for permission in PERMISSIONS),
    ),
    "merchant_owner": (
        "Merchant owner",
        "Manage a merchant's operational data and payment activity.",
        frozenset(
            {
                "users:read",
                "users:create",
                "users:update",
                "merchants:read",
                "merchants:update",
                "branches:read",
                "branches:create",
                "branches:update",
                "branches:delete",
                "tills:read",
                "tills:create",
                "tills:update",
                "tills:delete",
                "providers:read",
                "transactions:read",
                "transactions:create",
                "transactions:update",
                "transactions:cancel",
                "transactions:refund",
                "reports:read",
                "reports:export",
                "api_keys:read",
                "api_keys:create",
                "api_keys:revoke",
            }
        ),
    ),
    "branch_manager": (
        "Branch manager",
        "Manage activity for an assigned branch.",
        frozenset(
            {
                "users:read",
                "branches:read",
                "tills:read",
                "tills:create",
                "tills:update",
                "transactions:read",
                "transactions:create",
                "transactions:update",
                "transactions:cancel",
                "reports:read",
            }
        ),
    ),
    "cashier": (
        "Cashier",
        "Process assigned checkout transactions.",
        frozenset({"transactions:read", "transactions:create"}),
    ),
}


def validate_catalog() -> None:
    """Fail fast if the application permission contract is internally invalid."""
    codes = [permission.code for permission in PERMISSIONS]
    if len(codes) != len(set(codes)):
        raise ValueError("Permission catalog contains duplicate codes")
    if any(code != code.lower() or not code.count(":") for code in codes):
        raise ValueError("Permission codes must use lowercase resource:action syntax")
    unknown = {
        code
        for _, _, role_permissions in SYSTEM_ROLES.values()
        for code in role_permissions
        if code not in PERMISSION_BY_CODE
    }
    if unknown:
        raise ValueError(f"System role references unknown permissions: {sorted(unknown)}")


validate_catalog()