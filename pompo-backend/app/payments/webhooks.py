"""Provider-neutral webhook verification and normalization contracts."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.payments.credentials import ProviderCredentials
from app.payments.providers import ProviderOutcome

SIGNATURE_HEADER = "x-pompo-signature"
TIMESTAMP_HEADER = "x-pompo-timestamp"
DEFAULT_REPLAY_TOLERANCE_SECONDS = 300

SENSITIVE_PAYLOAD_KEYS = frozenset(
    {
        "secret",
        "password",
        "token",
        "authorization",
        "api_key",
        "apikey",
        "pin",
        "webhook_secret",
        "signing_key",
    }
)


@dataclass(frozen=True)
class WebhookVerificationResult:
    verified: bool
    timestamp_validated: bool = False
    failure_reason: str | None = None


@dataclass(frozen=True)
class NormalizedWebhookEvent:
    provider_event_id: str
    event_type: str
    event_version: str | None
    payment_reference: str | None
    provider_transaction_reference: str | None
    outcome: ProviderOutcome | None
    message: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class WebhookAdapter(Protocol):
    """Optional webhook contract layered on payment provider adapters."""

    async def verify_webhook(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
        credentials: ProviderCredentials,
    ) -> WebhookVerificationResult: ...

    async def parse_webhook(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> NormalizedWebhookEvent: ...


def normalize_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key.lower(): value for key, value in headers.items()}


def sanitize_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive keys from persisted webhook payloads."""

    def _clean(value: Any) -> Any:
        if isinstance(value, dict):
            cleaned: dict[str, Any] = {}
            for key, nested in value.items():
                if key.lower() in SENSITIVE_PAYLOAD_KEYS:
                    cleaned[key] = "[redacted]"
                else:
                    cleaned[key] = _clean(nested)
            return cleaned
        if isinstance(value, list):
            return [_clean(item) for item in value]
        return value

    return _clean(data)


def constant_time_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode(), right.encode())


def compute_mock_signature(secret: str, timestamp: str, body: bytes) -> str:
    message = f"{timestamp}.".encode() + body
    digest = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def validate_mock_timestamp(
    timestamp_header: str | None,
    *,
    tolerance_seconds: int = DEFAULT_REPLAY_TOLERANCE_SECONDS,
) -> bool:
    if not timestamp_header:
        return False
    try:
        timestamp = int(timestamp_header)
    except ValueError:
        return False
    now = int(time.time())
    return abs(now - timestamp) <= tolerance_seconds


def verify_mock_signature(
    *,
    headers: dict[str, str],
    body: bytes,
    secret: str | None,
    require_timestamp: bool = True,
) -> WebhookVerificationResult:
    normalized = normalize_headers(headers)
    signature = normalized.get(SIGNATURE_HEADER)
    timestamp = normalized.get(TIMESTAMP_HEADER)
    if not secret:
        return WebhookVerificationResult(False, failure_reason="Webhook secret not configured")
    if not signature:
        return WebhookVerificationResult(False, failure_reason="Missing signature header")
    expected = compute_mock_signature(secret, timestamp or "", body)
    if not constant_time_compare(signature, expected):
        return WebhookVerificationResult(False, failure_reason="Invalid signature")
    timestamp_validated = True
    if require_timestamp:
        timestamp_validated = validate_mock_timestamp(timestamp)
        if not timestamp_validated:
            return WebhookVerificationResult(
                False,
                timestamp_validated=False,
                failure_reason="Invalid or stale timestamp",
            )
    return WebhookVerificationResult(True, timestamp_validated=timestamp_validated)


def parse_mock_webhook_body(body: bytes) -> NormalizedWebhookEvent:
    try:
        payload = json.loads(body.decode())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Malformed webhook JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Webhook payload must be a JSON object")

    event_id = payload.get("event_id")
    event_type = payload.get("event_type")
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("Missing provider event identifier")
    if not isinstance(event_type, str) or not event_type.strip():
        raise ValueError("Missing event type")

    outcome_raw = payload.get("outcome")
    outcome = None
    if isinstance(outcome_raw, str):
        normalized = outcome_raw.strip().lower()
        try:
            outcome = ProviderOutcome(normalized)
        except ValueError as exc:
            raise ValueError(f"Unsupported webhook outcome: {outcome_raw}") from exc

    payment_reference = payload.get("payment_reference")
    provider_transaction_reference = payload.get("provider_transaction_id") or payload.get(
        "provider_transaction_reference"
    )
    event_version = payload.get("event_version")
    message = payload.get("message")

    metadata: dict[str, str] = {}
    for key, value in payload.items():
        if key in {
            "event_id",
            "event_type",
            "event_version",
            "payment_reference",
            "provider_transaction_id",
            "provider_transaction_reference",
            "outcome",
            "message",
        }:
            continue
        if isinstance(value, (str, int, float, bool)):
            metadata[key] = str(value)

    return NormalizedWebhookEvent(
        provider_event_id=event_id.strip(),
        event_type=event_type.strip(),
        event_version=str(event_version).strip() if event_version is not None else None,
        payment_reference=str(payment_reference).strip() if payment_reference else None,
        provider_transaction_reference=(
            str(provider_transaction_reference).strip() if provider_transaction_reference else None
        ),
        outcome=outcome,
        message=str(message) if message is not None else None,
        metadata=metadata,
    )


def is_supported_mock_event_type(event_type: str) -> bool:
    return bool(re.match(r"^payment\.(success|failure|timeout|update)$", event_type))
