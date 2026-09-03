# Payment instruments and unified checkout

POMPO remains a payment gateway. This layer stores **safe payment-method
references**, not a wallet and not provider credentials.

## What is stored

Each `PaymentInstrument` belongs to one customer (`users.id`) and one
provider. The customer API exposes `public_identifier` (`PIM-…`) only.

Stored:

- provider
- instrument type (`mobile_money`, `visa`, `mastercard`)
- display name
- masked identifier (`+265 88•• ••21`, `•••• 4242`)
- HMAC-SHA256 digest of a provider/sandbox token (`token_reference`)
- status, default flag, sandbox flag
- authorization state
- safe metadata (channel/brand/last4)
- timestamps

Never stored:

- PIN, CVV, CVC, PAN, card number
- provider passwords, OTPs, access tokens

The digest is not reversible. Simulated sandbox tokens (`simtok_…`) are
created at enroll time, digested, and discarded.

## Token strategy

There is no invented card network or vault. Until a live acquirer issues
an opaque token:

1. Simulated enroll creates a random sandbox token.
2. POMPO stores `HMAC-SHA256(jwt_secret_key, token)`.
3. Charge uses the existing `initiate_payment` path with the instrument's
   provider. The plaintext token is not required and is not stored.

When a future provider documents reusable tokens, store that provider
reference (or its digest) in `token_reference`. Do not store PAN/PIN/CVV.

## Provider capabilities

New flags, default **false**:

- `supports_payment_instruments`
- `supports_instrument_enroll`
- `supports_instrument_charge`
- `supports_instrument_verify`
- `supports_instrument_remove`

Simulated sandbox adapters set these true. Airtel Money Malawi does **not**.
Collection APIs 2.0 swagger does not document a reusable account token, so
Airtel enroll is catalogued as unavailable. TNM and banks are "Coming soon".

## Lifecycle

`active` → `inactive` / `expired` / `revoked`.

Revoked methods cannot be default and cannot be charged. List APIs omit
revoked rows. One active default per customer (partial unique index).

## Customer APIs

| Method | Path | Notes |
|---|---|---|
| GET | `/payment-methods/catalog` | Offered types, including unavailable rails |
| GET | `/payment-methods` | Current user's active methods |
| POST | `/payment-methods` | Sandbox enroll only where `available` |
| GET | `/payment-methods/{id}` | Public id. Cross-user is `404` |
| POST | `/payment-methods/{id}/default` | Unsets the previous default |
| POST | `/payment-methods/{id}/verify` | Simulated no-op complete |
| DELETE | `/payment-methods/{id}` | Revoke |
| GET | `/payment-methods/admin` | `users:read`. Masked only |

Checkout:

`POST /payments/from-qr` accepts `payload` **or** `public_identifier`, plus
optional `payment_instrument_id`. Manual public-id entry still parses the
**stored signed payload**. It does not skip HMAC, expiry, or merchant checks.

The server derives provider and `payment_method` from the instrument.
A client `provider_code` that does not match the instrument is `422`.
Machine clients cannot charge a saved method.

Existing POS `POST /payments` without an instrument is unchanged.
Idempotency remains `(merchant_id, idempotency_key)` plus request fingerprint
(including the instrument public id).

## Authorization states

Provider-neutral values: `not_required`, `required`, `waiting_provider`,
`open_provider_flow`, `credential_required`, `otp_required`, `completed`,
`failed`, `unsupported`.

Simulated enroll completes immediately (`not_required` / `completed`).
There is no universal PIN screen. Airtel PIN/USSD UX must follow the live
contract when that contract exists.

## Unified checkout

Scan or enter QR → merchant/amount → choose saved method → confirm →
`PaymentService` → `ProviderRegistry` → adapter.

```text
PaymentInstrument → Provider → Payment
```

## Remaining external dependencies

- Airtel reusable account association: not documented; enroll blocked.
- TNM Mpamba, National Bank, Standard Bank, NBS, First Capital: not started.
- Card PAN tokenization: requires a real acquirer/vault contract.
