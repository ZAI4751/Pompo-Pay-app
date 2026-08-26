"""Enumerations shared across the domain model.

Kept in one module so the transaction state machine (services/transactions,
future milestone) and the ORM layer reference a single source of truth.
"""

from __future__ import annotations

import enum


class TransactionStatus(str, enum.Enum):
    """Lifecycle states for a Pompo payment transaction.

    Valid transitions are enforced by the payment state machine service.
    """

    CREATED = "created"
    QR_GENERATED = "qr_generated"
    PENDING = "pending"
    PENDING_USER_PIN = "pending_user_pin"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


TERMINAL_TRANSACTION_STATUSES = frozenset(
    {
        TransactionStatus.SUCCESS,
        TransactionStatus.FAILED,
        TransactionStatus.TIMEOUT,
        TransactionStatus.CANCELLED,
        TransactionStatus.REFUNDED,
    }
)


class PaymentAttemptStatus(str, enum.Enum):
    """Lifecycle states for a single provider payment attempt."""

    INITIATED = "initiated"
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ProviderCode(str, enum.Enum):
    """Supported (or planned) payment provider integrations.

    Real provider adapters are out of scope for the foundation milestones —
    this enum exists so provider rows can be seeded and referenced by code
    before any adapter is implemented.
    """

    AIRTEL_MONEY = "airtel_money"
    TNM_MPAMBA = "tnm_mpamba"
    NATIONAL_BANK = "national_bank"
    FDH_BANK = "fdh_bank"
    STANDARD_BANK = "standard_bank"
    SIMULATED = "simulated"


class UserRoleCode(str, enum.Enum):
    """Well-known role codes seeded by default.

    Additional custom roles may be created at runtime — this enum only
    captures the roles the platform relies on programmatically (e.g. to
    gate platform-admin-only endpoints).
    """

    PLATFORM_ADMIN = "platform_admin"
    MERCHANT_OWNER = "merchant_owner"
    BRANCH_MANAGER = "branch_manager"
    CASHIER = "cashier"
