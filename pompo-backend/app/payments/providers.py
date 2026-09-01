"""Provider-neutral contracts and normalized provider outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Protocol


class ProviderOutcome(StrEnum):
    SUCCESS = "success"
    PENDING = "pending"
    FAILED = "failed"
    TIMEOUT = "timeout"
    REJECTED = "rejected"


class ProviderErrorCode(StrEnum):
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    REJECTED = "rejected"
    AUTHENTICATION = "authentication"
    RATE_LIMITED = "rate_limited"
    INVALID_REQUEST = "invalid_request"
    DUPLICATE = "duplicate"
    UNKNOWN = "unknown"


class RetryClass(StrEnum):
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"


RETRYABLE_ERROR_CODES = frozenset(
    {
        ProviderErrorCode.TIMEOUT,
        ProviderErrorCode.UNAVAILABLE,
        ProviderErrorCode.RATE_LIMITED,
    }
)


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_push_payment: bool = True
    supports_status_query: bool = True
    supports_cancel: bool = False
    supports_refund: bool = False
    supports_webhooks: bool = False
    supports_qr: bool = False


@dataclass(frozen=True)
class ProviderHealth:
    """Normalized adapter health. Does not include the admin enabled flag."""

    configured: bool
    supports_health_check: bool
    reachable: bool | None = None
    contract_ready: bool = False
    message: str | None = None


@dataclass(frozen=True)
class ProviderPaymentRequest:
    reference: str
    amount: Decimal
    currency: str
    merchant_id: str
    customer_phone: str | None = None
    narration: str | None = None
    idempotency_key: str = ""
    rail_environment: str = "sandbox"
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResult:
    outcome: ProviderOutcome
    provider_reference: str | None = None
    provider_status: str | None = None
    provider_transaction_id: str | None = None
    correlation_id: str | None = None
    message: str | None = None
    retryable: bool = False
    error_code: ProviderErrorCode | None = None


class ProviderError(Exception):
    """Normalized provider failure safe for the payment core."""

    def __init__(
        self,
        code: ProviderErrorCode,
        message: str,
        retryable: bool,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable

    @property
    def retry_class(self) -> RetryClass:
        return RetryClass.RETRYABLE if self.retryable else RetryClass.NON_RETRYABLE


class ProviderUnavailable(ProviderError):
    def __init__(self, message: str = "Provider is unavailable") -> None:
        super().__init__(ProviderErrorCode.UNAVAILABLE, message, True)


class ProviderTimeout(ProviderError):
    def __init__(self, message: str = "Provider request timed out") -> None:
        super().__init__(ProviderErrorCode.TIMEOUT, message, True)


class ProviderRejected(ProviderError):
    def __init__(self, message: str = "Provider rejected payment") -> None:
        super().__init__(ProviderErrorCode.REJECTED, message, False)


class ProviderAuthenticationError(ProviderError):
    def __init__(self, message: str = "Provider authentication failed") -> None:
        super().__init__(ProviderErrorCode.AUTHENTICATION, message, False)


class ProviderRateLimited(ProviderError):
    def __init__(self, message: str = "Provider rate limit exceeded") -> None:
        super().__init__(ProviderErrorCode.RATE_LIMITED, message, True)


class ProviderInvalidRequest(ProviderError):
    def __init__(self, message: str = "Provider rejected the request format") -> None:
        super().__init__(ProviderErrorCode.INVALID_REQUEST, message, False)


class ProviderDuplicate(ProviderError):
    def __init__(self, message: str = "Provider reported a duplicate request") -> None:
        super().__init__(ProviderErrorCode.DUPLICATE, message, False)


class ProviderUnknownError(ProviderError):
    def __init__(self, message: str = "Provider returned an unclassified error") -> None:
        super().__init__(ProviderErrorCode.UNKNOWN, message, False)


class UnsupportedProviderOperation(ProviderError):
    def __init__(self, operation: str) -> None:
        super().__init__(
            ProviderErrorCode.INVALID_REQUEST,
            f"Provider does not support {operation}",
            False,
        )


class ProviderAdapter(Protocol):
    code: str
    capabilities: ProviderCapabilities
    live_contract_ready: bool

    async def initiate_payment(self, request: ProviderPaymentRequest) -> ProviderResult: ...

    async def get_payment_status(self, provider_reference: str) -> ProviderResult: ...

    async def cancel_payment(self, provider_reference: str) -> ProviderResult: ...

    async def refund_payment(self, provider_reference: str, amount: Decimal) -> ProviderResult: ...

    async def health_check(self) -> ProviderHealth: ...


def require_capability(adapter: ProviderAdapter, operation: str) -> None:
    mapping = {
        "initiate": adapter.capabilities.supports_push_payment,
        "status_query": adapter.capabilities.supports_status_query,
        "cancel": adapter.capabilities.supports_cancel,
        "refund": adapter.capabilities.supports_refund,
    }
    if operation not in mapping:
        raise UnsupportedProviderOperation(operation)
    if not mapping[operation]:
        raise UnsupportedProviderOperation(operation)


def retry_class_for(code: ProviderErrorCode) -> RetryClass:
    if code in RETRYABLE_ERROR_CODES:
        return RetryClass.RETRYABLE
    return RetryClass.NON_RETRYABLE
