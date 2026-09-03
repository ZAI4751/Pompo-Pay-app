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

    Simulated codes are the only adapters that execute a payment. Airtel, TNM,
    and bank codes have structured stub adapters until a real contract exists.
    """

    AIRTEL_MONEY = "airtel_money"
    TNM_MPAMBA = "tnm_mpamba"
    NATIONAL_BANK = "national_bank"
    FDH_BANK = "fdh_bank"
    STANDARD_BANK = "standard_bank"
    SIMULATED = "simulated"
    SIMULATED_PENDING = "simulated_pending"
    SIMULATED_FAILURE = "simulated_failure"
    SIMULATED_TIMEOUT = "simulated_timeout"


class ProviderType(str, enum.Enum):
    """High-level rail family. Distinct from operational health."""

    SIMULATED = "simulated"
    MOBILE_MONEY = "mobile_money"
    BANK = "bank"


class ProviderHealthState(str, enum.Enum):
    """Operational lifecycle. Registered is not the same as operational."""

    ACTIVE = "active"
    DISABLED = "disabled"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class QRType(str, enum.Enum):
    """POMPO QR code classification."""

    STATIC = "static"
    DYNAMIC = "dynamic"


class QRStatus(str, enum.Enum):
    """Operational lifecycle for a merchant QR code."""

    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class WebhookProcessingStatus(str, enum.Enum):
    """Lifecycle for inbound provider webhook events."""

    RECEIVED = "received"
    QUEUED = "queued"
    PROCESSING = "processing"
    PROCESSED = "processed"
    DUPLICATE = "duplicate"
    FAILED = "failed"
    REJECTED = "rejected"
    RECONCILIATION = "reconciliation"


class WebhookFailureCategory(str, enum.Enum):
    """Classification for webhook ingestion/processing failures."""

    INVALID_SIGNATURE = "invalid_signature"
    MALFORMED = "malformed"
    UNKNOWN_PROVIDER = "unknown_provider"
    UNKNOWN_PAYMENT = "unknown_payment"
    PROVIDER_MISMATCH = "provider_mismatch"
    STATE_CONFLICT = "state_conflict"
    UNSUPPORTED_EVENT = "unsupported_event"
    INFRASTRUCTURE = "infrastructure"


class FeeType(str, enum.Enum):
    """Supported pricing components. Forward-compatible; not a billing platform."""

    ZERO = "zero"
    FIXED = "fixed"
    PERCENTAGE = "percentage"


class SettlementStatus(str, enum.Enum):
    """Lifecycle of a provider settlement record. Independent of payment status."""

    RECEIVED = "received"
    PROCESSING = "processing"
    SETTLED = "settled"
    RECONCILED = "reconciled"
    EXCEPTION = "exception"


class SettlementBatchStatus(str, enum.Enum):
    """Lifecycle of an ingested provider settlement batch."""

    RECEIVED = "received"
    PROCESSING = "processing"
    SETTLED = "settled"
    FAILED = "failed"


class ReconciliationStatus(str, enum.Enum):
    """Comparison outcome between POMPO expected records and provider settlement."""

    MATCHED = "matched"
    PARTIAL_MATCH = "partial_match"
    UNMATCHED = "unmatched"
    DISCREPANCY = "discrepancy"
    INVESTIGATION = "investigation"
    RESOLVED = "resolved"


class MismatchCategory(str, enum.Enum):
    """Why expected and actual financial records differ. Never auto-corrected."""

    AMOUNT_MISMATCH = "amount_mismatch"
    CURRENCY_MISMATCH = "currency_mismatch"
    PROVIDER_REFERENCE_MISMATCH = "provider_reference_mismatch"
    MISSING_POMPO_TRANSACTION = "missing_pompo_transaction"
    MISSING_SETTLEMENT = "missing_settlement"
    DUPLICATE_SETTLEMENT = "duplicate_settlement"
    FEE_MISMATCH = "fee_mismatch"
    STATUS_MISMATCH = "status_mismatch"
    TIMING_DISCREPANCY = "timing_discrepancy"


class ReconciliationRunStatus(str, enum.Enum):
    """Lifecycle of a provider reconciliation window."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class APIClientType(str, enum.Enum):
    """Machine-client identity. Distinct from human UserRoleCode."""

    DEVELOPER = "developer"
    MERCHANT_POS = "merchant_pos"
    PARTNER = "partner"


class APIClientStatus(str, enum.Enum):
    """Operational lifecycle for an integration application."""

    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"


class APIClientEnvironment(str, enum.Enum):
    """Credential environment stamped into issued API keys."""

    SANDBOX = "sandbox"
    LIVE = "live"


class OutboundWebhookStatus(str, enum.Enum):
    """Delivery lifecycle for partner/POS outbound webhooks."""

    PENDING = "pending"
    RETRYING = "retrying"
    SENT = "sent"
    FAILED = "failed"


class OutboundWebhookFailureCategory(str, enum.Enum):
    """Why an outbound partner webhook delivery stopped or will retry."""

    NETWORK = "network"
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    INVALID_DESTINATION = "invalid_destination"
    EXHAUSTED = "exhausted"


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
    CUSTOMER = "customer"


class PaymentRequestStatus(str, enum.Enum):
    """Lifecycle of a shareable payment instruction. Not a stored balance."""

    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BillSplitStatus(str, enum.Enum):
    """Aggregate state derived from child payment requests."""

    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class NotificationType(str, enum.Enum):
    """In-app notification event types corresponding to real POMPO events."""

    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_REQUEST_RECEIVED = "payment_request_received"
    PAYMENT_REQUEST_PAID = "payment_request_paid"
    PAYMENT_REQUEST_EXPIRING = "payment_request_expiring"
    PAYMENT_REQUEST_EXPIRED = "payment_request_expired"
    MERCHANT_PAYMENT_RECEIVED = "merchant_payment_received"
    MERCHANT_PAYMENT_FAILED = "merchant_payment_failed"


class SupportRequestStatus(str, enum.Enum):
    """Lightweight support request lifecycle. Not a ticketing platform."""

    OPEN = "open"
    CLOSED = "closed"


class SupportCategory(str, enum.Enum):
    """Why a customer opened a support request."""

    PAYMENT_PROBLEM = "payment_problem"
    REPORT_TRANSACTION = "report_transaction"
    REFERENCE_LOOKUP = "reference_lookup"
    OTHER = "other"


class PaymentInstrumentType(str, enum.Enum):
    """Customer-facing instrument family. Banks are providers, not types."""

    MOBILE_MONEY = "mobile_money"
    VISA = "visa"
    MASTERCARD = "mastercard"


class PaymentInstrumentStatus(str, enum.Enum):
    """Lifecycle of a saved payment method. Revoked methods cannot be charged."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ProviderAuthorizationState(str, enum.Enum):
    """Provider-neutral authorization UX. The concrete flow is adapter-specific."""

    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    WAITING_PROVIDER = "waiting_provider"
    OPEN_PROVIDER_FLOW = "open_provider_flow"
    CREDENTIAL_REQUIRED = "credential_required"
    OTP_REQUIRED = "otp_required"
    COMPLETED = "completed"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"
