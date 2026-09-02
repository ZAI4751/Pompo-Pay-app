# M013 — POS + Developer Platform

Canonical partner docs: [docs/integrations/](../../docs/integrations/README.md).

This file remains as a backend pointer. Do not duplicate a second payment engine.

POMPO exposes a machine integration layer for merchant POS systems, developer
applications, and partner software. This is not a second payment engine.
`PaymentService`, QR payloads, provider routing, and inbound provider webhooks
remain authoritative.

## Identities

| Actor | How it authenticates | Authorization |
|-------|----------------------|---------------|
| Human user | JWT (`Authorization: Bearer`) | RBAC permissions (`api_keys:*`, etc.) |
| API client / POS / partner | API key (`X-API-Key` or Bearer `pompo_…`) | Integration scopes |

POS software must not log in as a human user.

## API clients

An **integration client** is the application identity:

- `public_id` (e.g. `app_ab12cd34`)
- `client_type`: `developer` · `merchant_pos` · `partner`
- `environment`: `sandbox` · `live`
- `status`: `active` · `disabled` · `revoked`
- merchant ownership, optional branch/till binding
- scopes
- optional partner webhook URL
- `last_used_at`

`merchant_pos` clients must be bound to merchant → branch → till. The server
derives that context from the authenticated client. Client-supplied merchant,
branch, or till IDs are only accepted as a consistency check.

## API keys

Format: `pompo_test_<hex>` or `pompo_live_<hex>`.

- Shown **once** at creation or rotation
- Only HMAC-SHA256(`SECRET_KEY`, raw key) is stored
- Prefix (16 characters) is kept for operational identification
- Rotation issues a new key and revokes previous active keys by default
- Revocation and client disable are immediate
- Keys never appear in list responses, logs, or OpenAPI examples

## Scopes (machine)

| Scope | Purpose |
|-------|---------|
| `payments:create` | Create payment requests |
| `payments:read` | Read payment status |
| `qr:create` | Create dynamic QR checkout |
| `qr:read` | Read QR context |
| `transactions:read` | Alias of `payments:read` |
| `webhooks:read` | Read this client's outbound deliveries |

Never granted to POS clients: `providers:manage`, `rbac:manage`,
`settlements:manage`, `reconciliation:manage`.

Human administrators use existing `api_keys:read|create|revoke`.

## POS payment flow

```text
API key → client identity → merchant/branch/till from client
       → PaymentService (idempotency + provider selection)
       → optional dynamic QR (existing M009 signer)
       → status poll and/or partner webhook
```

### Create payment (and QR)

```http
POST /api/v1/integrations/payments
X-API-Key: pompo_test_…
Idempotency-Key: order-123

{
  "amount": "250.00",
  "currency": "MWK",
  "payment_method": "mobile_money",
  "idempotency_key": "order-123",
  "generate_qr": true
}
```

`201` example (no provider credentials):

```json
{
  "reference": "PMP-…",
  "status": "qr_generated",
  "amount": "250.00",
  "currency": "MWK",
  "merchant_id": "…",
  "branch_id": "…",
  "till_id": "…",
  "qr": {
    "public_identifier": "QR…",
    "encoded_payload": "POMPO:1:dynamic:…",
    "qr_type": "dynamic",
    "status": "active",
    "expires_at": "…"
  }
}
```

Customer scan uses the existing mobile contract (`GET /qr/{id}`,
`POST /payments/from-qr`). POS polls:

```http
GET /api/v1/integrations/payments/{reference}
X-API-Key: pompo_test_…
```

## Idempotency

Reuses `(merchant_id, idempotency_key)` on `transactions`. Same key + fingerprint
returns the same payment. Same key + different body is `409` /
`idempotency_conflict`. Concurrent duplicates resolve to one financial row.

## Outbound partner webhooks

When a payment created by an API client changes status, POMPO queues an
outbound event (Celery, bounded retries).

Events: `payment.pending` · `payment.processing` · `payment.success` ·
`payment.failed` · `payment.timeout`.

Stable event ID: `evt_{reference}_{status-suffix}`. Duplicate inbound provider
webhooks do not create a second partner event (unique on
client + transaction + event type).

### Signing

Same POMPO HMAC used for inbound mock provider webhooks:

```text
signed_payload = "{unix_timestamp}." + raw_body
X-Pompo-Signature: sha256={HMAC_SHA256(webhook_signing_secret, signed_payload)}
X-Pompo-Timestamp: {unix_timestamp}
X-Pompo-Event-Id: evt_…
X-Pompo-Event-Type: payment.success
```

Replay window for verifiers: 300 seconds. Signing secrets are derived from
`SECRET_KEY` + client id + version and shown once; they are never stored.

### Retries

Pending → retrying → sent, or failed. Maximum 5 attempts. Backoff
10s / 30s / 120s / 300s / 900s. 4xx (except 408/429) is permanent.
Invalid destinations fail immediately. Delivery rows are auditable in Master
Admin.

## Rate limiting

IP buckets remain. Requests presenting a `pompo_` key also consume a
prefix-scoped bucket. Repeated authentication failures are counted per IP.
Responses use `429` with `code=rate_limited`, `Retry-After`, and
`X-RateLimit-*` headers.

## Error contract

Integration endpoints return:

```json
{ "detail": "Invalid API key", "code": "invalid_api_key", "request_id": "…" }
```

| Code | HTTP |
|------|------|
| `invalid_api_key` | 401 |
| `api_key_revoked` | 401 |
| `api_key_expired` | 401 |
| `api_key_inactive` | 401 |
| `insufficient_scope` | 403 |
| `invalid_till` | 422 |
| `invalid_amount` | 422 |
| `invalid_request` | 422 |
| `unsupported_currency` | 422 |
| `idempotency_conflict` | 409 |
| `payment_not_found` | 404 |
| `rate_limited` | 429 |

No stack traces. Cross-tenant payment lookups return `payment_not_found`.

## Admin APIs (JWT)

| Method | Path | Permission |
|--------|------|------------|
| POST | `/integrations/clients` | `api_keys:create` |
| GET | `/integrations/clients` | `api_keys:read` |
| GET | `/integrations/clients/{id}` | `api_keys:read` |
| PATCH | `/integrations/clients/{id}` | `api_keys:create` (name, scopes, webhook URL, disable/enable) |
| POST | `/integrations/clients/{id}/keys` | `api_keys:create` |
| POST | `/integrations/clients/{id}/webhook-secret` | `api_keys:create` |
| POST | `/integrations/clients/{id}/revoke` | `api_keys:revoke` |
| GET | `/integrations/clients/{id}/deliveries` | `api_keys:read` |

Master Admin **API Keys** creates clients, assigns scopes, binds POS
merchant/branch/till, rotates keys, disables or revokes clients, and inspects
outbound deliveries. Secrets are shown once.

## Example client

See `scripts/pos_simulator.py` for a sandbox client that authenticates, creates
a dynamic QR payment, polls status, and verifies webhook signatures.

`scripts/verify_m013_sandbox.py` runs the full M013 checks against a live API
(create client, QR payment, customer scan, simulated process, idempotency,
outbound events, revoke, insufficient scope). It never prints secrets.

## Migration

`0013_m013_integrations` — after `0012_m012_mobile`.
