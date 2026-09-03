"""Customer-friendly wording for real transaction statuses.

Does not invent or alter financial state. The backend status remains
authoritative; this module only maps copy for API/UI consumers.
"""

from __future__ import annotations

from app.models.enums import TransactionStatus

_COPY: dict[str, tuple[str, str]] = {
    TransactionStatus.CREATED.value: (
        "Ready",
        "Your payment is ready to start.",
    ),
    TransactionStatus.QR_GENERATED.value: (
        "Ready",
        "This payment is waiting for you to continue.",
    ),
    TransactionStatus.PENDING.value: (
        "Waiting",
        "We're waiting for the payment to continue.",
    ),
    TransactionStatus.PENDING_USER_PIN.value: (
        "Waiting for approval",
        "Approve the payment on your phone if prompted.",
    ),
    TransactionStatus.PROCESSING.value: (
        "Processing",
        "Your payment is being processed.",
    ),
    TransactionStatus.SUCCESS.value: (
        "Paid",
        "This payment completed successfully.",
    ),
    TransactionStatus.FAILED.value: (
        "Failed",
        "This payment did not go through.",
    ),
    TransactionStatus.TIMEOUT.value: (
        "No final response",
        "We haven't received a final response yet.",
    ),
    TransactionStatus.CANCELLED.value: (
        "Cancelled",
        "This payment was cancelled.",
    ),
    TransactionStatus.REFUNDED.value: (
        "Refunded",
        "This payment was refunded.",
    ),
}


def customer_status_label(status: str) -> str:
    """Return a short customer-facing label for a backend status."""
    return _COPY.get(status, ("Needs confirmation", "We're checking the payment status."))[0]


def customer_status_detail(status: str) -> str:
    """Return a one-line explanation that maps to the real backend status."""
    return _COPY.get(status, ("Needs confirmation", "We're checking the payment status."))[1]
