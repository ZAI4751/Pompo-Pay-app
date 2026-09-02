"""Partner webhook signing. Reuses the existing POMPO HMAC format."""

from __future__ import annotations

from app.payments.webhooks import (
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    compute_mock_signature,
    constant_time_compare,
    validate_mock_timestamp,
    verify_mock_signature,
)

EVENT_ID_HEADER = "x-pompo-event-id"
EVENT_TYPE_HEADER = "x-pompo-event-type"

__all__ = [
    "EVENT_ID_HEADER",
    "EVENT_TYPE_HEADER",
    "SIGNATURE_HEADER",
    "TIMESTAMP_HEADER",
    "compute_mock_signature",
    "constant_time_compare",
    "sign_outbound_body",
    "validate_mock_timestamp",
    "verify_mock_signature",
]


def sign_outbound_body(secret: str, timestamp: str, body: bytes) -> str:
    """Return ``sha256=<hex>`` over ``{timestamp}.{body}``."""

    return compute_mock_signature(secret, timestamp, body)
