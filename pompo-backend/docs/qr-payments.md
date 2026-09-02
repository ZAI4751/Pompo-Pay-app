# M009 — QR Payments

POMPO QR is an **internal protocol** for identifying payment context at a
merchant till. It is not an Airtel/TNM/bank network payload. Financial truth
remains in PostgreSQL; payments flow through the existing `PaymentService` and
provider registry.

## Architecture

```text
Merchant admin → QRService → signed payload + QRCode row
Customer scan  → parse/verify → PaymentService → ProviderAdapter
```

- **Static QR** — identifies merchant/branch/till. No amount in the payload.
  Payment is created only when the customer confirms an amount via
  `POST /api/v1/payments/from-qr`.
- **Dynamic QR** — tied to a pre-created payment intent (`Transaction` in
  `qr_generated` status) with fixed amount and expiry. The client cannot
  override the amount.

## Payload format (version 1)

Deterministic, compact strings suitable for QR encoding:

```text
Static:  POMPO:1:static:<public_id>:<signature>
Dynamic: POMPO:1:dynamic:<public_id>:<amount_minor>:<currency>:<exp_unix>:<payment_ref>:<signature>
```

- `amount_minor` — integer minor units (e.g. `12550` = MWK 125.50)
- `signature` — first 22 chars of URL-safe Base64(HMAC-SHA256(signing_key, canonical_body))
- Signing key — application `SECRET_KEY` (never embedded in payloads)

The server stores the canonical payload on the `qr_codes` row and rejects scans
when the presented string does not match (tamper detection).

## Database model (`qr_codes`)

| Field | Purpose |
|-------|---------|
| `public_identifier` | Stable external ID (e.g. `QRABC123456789`) |
| `merchant_id`, `branch_id`, `till_id` | Payment destination context |
| `qr_type` | `static` or `dynamic` |
| `status` | `active`, `disabled`, `revoked`, `expired`, `consumed` |
| `transaction_id` | Linked payment for dynamic QR |
| `amount`, `currency`, `payment_reference` | Dynamic context (server authoritative) |
| `expires_at` | Dynamic QR expiry |
| `payload` | Canonical signed string |
| `revoked_at` | Administrative revocation timestamp |

## API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/qr/static` | `qr:create` | Create static till QR |
| POST | `/api/v1/qr/dynamic` | `qr:create` | Create dynamic checkout QR + payment intent |
| GET | `/api/v1/qr/{public_identifier}` | Public | Safe scan preview |
| GET | `/api/v1/qr/{public_identifier}/admin` | `qr:read` | Full admin view |
| POST | `/api/v1/qr/{public_identifier}/revoke` | `qr:revoke` | Revoke QR |
| POST | `/api/v1/payments/from-qr` | `transactions:create` | Initiate payment from scanned payload |

## Security

- HMAC signature verification on every scan
- Tenant isolation on admin operations (merchant/branch scope)
- RBAC permissions: `qr:read`, `qr:create`, `qr:revoke`
- No secrets, JWTs, or credentials in QR payloads
- Audit events: `qr_static_created`, `qr_dynamic_created`, `qr_revoked`,
  `payment_initiated_from_qr`, `qr_invalid_attempt`
- Dynamic amount is never read from the client request body

## Idempotency

Static QR payments use the existing `(merchant_id, idempotency_key)` constraint
via `PaymentService.create_payment`.

Dynamic QR returns the linked transaction; repeated scans with the same QR
advance `qr_generated → pending` once. Terminal payment outcomes mark the QR
`consumed` (success, failure, cancel, timeout, refund).

### Signing key separation (future)

Today QR HMAC uses the application `SECRET_KEY`. That is acceptable for the
current single-service architecture, but **long-term production hardening**
should introduce a dedicated `QR_SIGNING_KEY` (or KMS-backed secret) so QR
payload rotation does not require rotating JWT/session signing material.
Do not change production secrets without an explicit migration plan.

## Migration

`0009_m009_qr_payments` expands `qr_codes` and seeds QR permissions.

## Mobile-ready flow

1. **Scan** — `GET /qr/{id}` for merchant/amount preview
2. **Confirm** — customer confirms amount (static) or fixed amount (dynamic)
3. **Pay** — `POST /payments/from-qr` with payload + idempotency key
4. **Status** — `GET /payments/{reference}` and optional `POST .../process`
