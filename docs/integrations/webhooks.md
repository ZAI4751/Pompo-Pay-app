# Outbound partner webhooks

M010 is **provider → POMPO**. M013 adds **POMPO → POS/partner**.

Configure one or more HTTPS destinations per integration client. Signing secrets
are shown once (derived; not stored). Responses return only a prefix.

## Events

`payment.pending` · `payment.processing` · `payment.success` · `payment.failed` ·
`payment.timeout`

Event ID: `evt_{payment_reference}_{status-suffix}` (example `evt_PMP-ABC_success`).

The event ID is stable across retries and across destinations for the same
payment status. The JSON body does not change between retries. Delivery headers
(`X-Pompo-Timestamp`, `X-Pompo-Signature`) are generated per attempt.

## Signing

```text
signed_payload = "{unix_timestamp}." + raw_body
X-Pompo-Signature: sha256={HMAC_SHA256(webhook_signing_secret, signed_payload)}
X-Pompo-Timestamp: {unix_timestamp}
X-Pompo-Event-Id: evt_…
X-Pompo-Event-Type: payment.success
```

Verify with constant-time compare. Reject timestamps older than 300 seconds
(replay protection). Python:

```python
import hmac, hashlib

def verify(secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## Retries

Celery delivery, max 5 attempts, backoff 10s / 30s / 120s / 300s / 900s.
4xx except 408/429 is permanent. Invalid destinations fail immediately.

Inspect deliveries in Master Admin (API Keys → Deliveries).
