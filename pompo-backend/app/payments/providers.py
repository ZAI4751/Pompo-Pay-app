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
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_push_payment: bool = True
    supports_status_query: bool = True
    supports_cancel: bool = False
    supports_refund: bool = False
    supports_webhooks: bool = False
    supports_qr: bool = False


@dataclass(frozen=True)
class ProviderPaymentRequest:
    reference: str
    amount: Decimal
    currency: str
    merchant_id: str
    customer_phone: str | None = None
    narration: str | None = None
    idempotency_key: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResult:
    outcome: ProviderOutcome
    provider_reference: str | None = None
    provider_status: str | None = None
    message: str | None = None
    retryable: bool = False


class ProviderError(Exception):
    """Normalized provider failure safe for the payment core."""

    def __init__(self, code: ProviderErrorCode, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


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


class ProviderAdapter(Protocol):
    code: str
    capabilities: ProviderCapabilities

    async def initiate_payment(self, request: ProviderPaymentRequest) -> ProviderResult: ...

    async def get_payment_status(self, provider_reference: str) -> ProviderResult: ...

    async def cancel_payment(self, provider_reference: str) -> ProviderResult: ...

    async def refund_payment(self, provider_reference: str, amount: Decimal) -> ProviderResult: ...
