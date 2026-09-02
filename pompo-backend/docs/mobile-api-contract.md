# POMPO M012 — Mobile API contract

The mobile app consumes the existing `/api/v1` surface. The backend remains
authoritative for authentication, authorization, QR validation, payment
state, provider routing, webhooks, and settlement.

Production base URL:

`https://pompo-api-production.up.railway.app/api/v1`

Development: `EXPO_PUBLIC_API_BASE_URL` (typically `http://localhost:8000/api/v1`
on iOS simulator, `http://10.0.2.2:8000/api/v1` on Android emulator).

All authenticated endpoints require `Authorization: Bearer <access_token>`.
Error bodies use FastAPI `{ "detail": ... }` plus the `X-Request-ID` header
when present. Never display stack traces.

Idempotency: `POST /payments` and `POST /payments/from-qr` require
`idempotency_key`. Replaying the same key with the same fingerprint returns
the original payment. A different fingerprint with the same key is `409`.

## Authentication

| Flow | Method | Path | Auth | Notes |
|---|---|---|---|---|
| Login | POST | `/auth/login` | none | `{email, password}` → `{access_token, refresh_token, token_type, expires_in}` |
| Refresh | POST | `/auth/refresh` | none | `{refresh_token}` → new token pair. Failed refresh is `401`. |
| Logout | POST | `/auth/logout` | none | `{refresh_token}` → `204` even if the token is already invalid |
| Current user | GET | `/auth/me` | access | Includes `role_code` for mode switching. Does **not** include permission catalogs. |

`role_code` values used by mobile UX (authorization is still server-side):

- `customer` — customer mode only
- `merchant_owner`, `branch_manager`, `cashier` — merchant mode default, can switch to customer
- `platform_admin` — both modes; merchant screens stay operational, not Master Admin

## Customer QR pay

| Flow | Method | Path | Auth | Request | Success |
|---|---|---|---|---|---|
| Extract public id | client parse only | — | — | `POMPO:1:static\|dynamic:<public_id>:...` | Public id only. Do not trust amount/expiry/signature locally. |
| Inspect | GET | `/qr/{public_identifier}` | **public** | — | Safe merchant/amount/status. `404` unknown, `422` expired/revoked/malformed state, `409` already used |
| Pay from QR | POST | `/payments/from-qr` | `transactions:create` | `{payload, idempotency_key, amount?}` | `201` payment. `amount` required for **static** only. Dynamic amount is server-authoritative; a client amount that differs is `422`. |
| Process | POST | `/payments/{reference}/process` | `transactions:update` | — | Runs PaymentService + simulated/live provider |
| Status | GET | `/payments/{reference}` | `transactions:read` | — | Payer (`cashier_id`) or same-merchant staff |
| History | GET | `/payments/mine` | `transactions:read` | `limit`, `offset` | Payments initiated by the current user |
| Cancel | POST | `/payments/{reference}/cancel` | `transactions:cancel` | — | Existing state machine |

Direct `POST /payments` remains a merchant POS create. Customers receive `403`
because they have no merchant membership. Do not use it for scan-to-pay.

## Merchant mode

| Flow | Method | Path | Auth |
|---|---|---|---|
| Context | GET | `/organization/merchants`, `/organization/merchants/{id}/branches`, `/organization/branches/{id}/tills` | merchant/branch permissions |
| Static QR | POST | `/qr/static` | `qr:create` |
| Dynamic QR | POST | `/qr/dynamic` | `qr:create` — creates a `qr_generated` payment; amount is fixed |
| List QR | GET | `/qr` | `qr:read` — optional `till_id` |
| Admin QR | GET | `/qr/{public_identifier}/admin` | `qr:read` |
| Revoke | POST | `/qr/{public_identifier}/revoke` | `qr:revoke` |
| Activity | GET | `/payments` | `transactions:read` + merchant context. `403` without `merchant_id`. |

Render `encoded_payload` from the API. Do not sign QR payloads in the app.

## Payment statuses (server)

`created`, `qr_generated`, `pending`, `processing`, `success`, `failed`,
`cancelled`, `timeout`, `reversed`, `unknown`. Map these in UI; do not invent
incompatible mobile-only financial states.

## Gaps not invented in mobile

- Customer self-registration is not part of M012. Provision users via Master Admin / `users:create` with the `customer` role.
- Push notifications, wallets, and stored cards are out of scope.
- Settlement and webhook administration stay in Master Admin.
