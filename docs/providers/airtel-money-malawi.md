# Airtel Money Malawi — M014 contract capture

This file is the in-repository approval record for the Airtel Money Malawi
adapter. Items are tagged:

- **VERIFIED** — observed on Airtel-owned surfaces on 2026-09-02
- **RFC6749** — OAuth 2.0 fields implied by Airtel's own OAuth error schema
- **PLACEHOLDER** — login-gated Collection APIs 2.0 swagger was not retrievable;
  implemented behind an isolated mapper and locked by contract tests
- **BLOCKED** — not implemented; needs portal login or Airtel support

Do not treat GitHub SDKs, Medium posts, or unofficial clients as sources.

## Official sources inspected

| Source | What it established |
|--------|---------------------|
| https://developers.airtel.africa/docs | Malawi is a selectable OpCo. Applications are per operating company. |
| https://developers.airtel.africa/documentation/authorization/1.0 | Authorization product exists; HTML is country-gated. |
| https://developers.airtel.africa/documentation/collection-apis/2.0 | Collection APIs 2.0 product exists; HTML is country-gated. |
| https://developers.airtel.mw/assets/app.config.json | Malawi OpCo config (deployment_date `2026-03-13`). |
| https://developers.airtel.africa/assets/app.config.json | Central portal; Uganda sample of the same OpenAPI host migration. |
| https://www.airtel.africa/assets/pdf/press-release/Airtel-Africa-Developer-Portal_ENGLISH.pdf | Official portal URL and collect/disburse Open API purpose. |
| `https://openapiuat.airtel.mw` live probes | Path existence and OAuth/token error schema. |

Collection APIs 2.0 and Authorization 1.0 request/response examples are served
from `/portal-bff/v1/documents/static/documentation` and returned
`invalid_token` without a developer-portal session. That swagger is **BLOCKED**
until POMPO has portal credentials.

## Environment separation (VERIFIED)

Malawi developer portal `highlight_message`:

- Staging: `https://openapiuat.airtel.mw`
- Production: `https://openapi.airtel.mw`

POMPO must set `PROVIDER_AIRTEL_MONEY_BASE_URL` explicitly. The adapter refuses
the production host when the catalog rail is `sandbox`, and refuses the staging
host when the catalog rail is `production`. Production rails remain blocked
unless `APP_ENV=production`.

## Country / currency (VERIFIED)

From Malawi `app.config.json`:

- `XCountry`: `MW` (OpCo id 12)
- `currency_code`: `MWK`
- Collection product id: `7`

This adapter is Malawi-only. It does not read a caller-supplied country.

## Authentication (VERIFIED + RFC6749)

Live sandbox host, 2026-09-02:

- `POST /auth/oauth2/token` exists.
- JSON `{"client_id","client_secret","grant_type":"client_credentials"}` is
  accepted as a token request (HTTP 400 `invalid_client`, not `invalid_request`).
- `application/x-www-form-urlencoded` produced the same `invalid_client` error.
- Error body: `{"error":"...","error_description":"..."}` (OAuth 2.0).

POMPO sends JSON. Successful token bodies were **not** observed (no credentials).
Token parsing therefore uses RFC 6749 `access_token` and optional `expires_in`.
If `expires_in` is absent the token is cached for 60 seconds only.

Tokens are cached in process memory with a 30-second expiry skew. Redis is not
financial truth and is not required. Tokens are never logged.

## Payment initiation (path VERIFIED, body PLACEHOLDER)

Live sandbox host:

- `POST /merchant/v1/payments/` exists.
- Missing bearer → HTTP 401
  `{"error":"invalid_token","error_description":"The access token is invalid or has expired","request_id":"..."}`.

`POST /merchant/v2/payments/` returned an Imperva HTML 403, not a JSON API
error. **v2 is not implemented.** Collection APIs **2.0** is the portal product
name; it is not assumed to be `/merchant/v2/`.

Request headers used by the adapter:

- `Authorization: Bearer <access_token>`
- `Content-Type: application/json`
- `Accept: application/json`
- `X-Country: MW`
- `X-Currency: MWK`

`X-Country` / `X-Currency` names are PLACEHOLDER header names corresponding to
official config keys `XCountry` / `currency_code`. They were not visually
confirmed in login-gated swagger.

Request body (PLACEHOLDER — Collection 2.0 swagger not retrieved):

```json
{
  "reference": "<POMPO transaction reference>",
  "subscriber": {
    "country": "MW",
    "currency": "MWK",
    "msisdn": "<national number, no 265 prefix>"
  },
  "transaction": {
    "amount": 250,
    "country": "MW",
    "currency": "MWK",
    "id": "<POMPO transaction reference>"
  }
}
```

`transaction.id` is the POMPO payment reference, never the attempt number.
Retries of the same payment reuse that id.

A 2xx initiation with no terminal success/failure code is normalized as
**pending** (USSD push accepted, not paid). Success is never inferred from HTTP
200 alone.

## Status enquiry (path VERIFIED, status tokens PLACEHOLDER)

Live sandbox host:

- `GET /standard/v1/payments/{id}` exists.
- Missing bearer → HTTP 401
  `{"error":"invalid_request","error_description":"The access token is missing"}`.

`{id}` is the same POMPO reference sent as `transaction.id`.

Malawi `additionalStatusCountries` includes `MW`. The additional-status path
itself was **not** published in `app.config.json` and is **BLOCKED**.

POMPO does not run an uncontrolled polling loop. Status is called only when
PaymentService requests it.

## Callbacks / webhooks (product VERIFIED, payload/signing PLACEHOLDER)

Malawi portal flags:

- `showCallback_uat`: true
- `showCallback_prod`: true
- `messageSigningProducts` includes collection product `7`
- `messageSigningCountries`: `["MW"]`
- `messageSigningCountriesEnable`: true

The signing algorithm, signed input, and callback JSON were **not** in the
public config. They are PLACEHOLDER:

- JSON object with a `transaction` object
- `transaction.id` → POMPO payment reference
- `transaction.airtel_money_id` → provider reference
- `transaction.status_code` or `transaction.status` → outcome
- optional `hash` field

When a webhook secret is configured, POMPO fail-closes unless `hash` is present
and matches HMAC-SHA256(secret, raw body with `hash` removed) as hex or
standard base64. **This algorithm is a placeholder** and must be replaced from
Collection APIs 2.0 callback docs after portal login.

Unsigned callbacks are accepted only when
`PROVIDER_AIRTEL_MONEY_WEBHOOK_UNSIGNED=true` (sandbox use). Simulated HMAC
(`x-pompo-signature`) is **not** used.

Inbound processing remains M010 (`POST /api/v1/webhooks/airtel_money`).

## Status tokens used for normalization (PLACEHOLDER)

Only these Collection-product tokens are mapped. Anything else on HTTP 2xx is
pending (API) or ignored as unknown (webhook parse error if no transaction id).

| Token | POMPO outcome |
|-------|----------------|
| `TS`, `SUCCESS` | success |
| `TF`, `TE`, `FAILED`, `FAILURE` | failed |
| `TIP`, `TA`, `PENDING`, `IN_PROGRESS` | pending |

Airtel error codes are stored as `provider_status`. They are not translated
into invented categories such as `insufficient_funds` until Collection 2.0
error tables are retrieved.

## Retry / timeouts

Transport: existing `ProviderHttpClient`. POST is never retry-safe.

Retryable: timeout, connection failure, HTTP 5xx, HTTP 429.
Non-retryable: invalid client, malformed request, rejected payment, duplicate.

PaymentService remains the attempt authority (max 3). Same POMPO reference is
replayed to Airtel.

## Health

No public health path was verified. Health authenticates against
`POST /auth/oauth2/token`. A failed probe does not disable the catalog row.

## Settlement (BLOCKED)

No Airtel Malawi settlement file/API contract was published on the inspected
surfaces. M011 remains provider-neutral. Do not build an Airtel settlement
system.

## Merchant registration (VERIFIED at portal level)

Developers register an application on the Malawi OpCo portal, add Collection
APIs, and obtain a client id / client secret from key management. Live keys
require Airtel approval. POMPO does not automate that onboarding.

## Configuration references (no secrets in git)

```text
PROVIDER_AIRTEL_MONEY_BASE_URL=https://openapiuat.airtel.mw
PROVIDER_AIRTEL_MONEY_ENVIRONMENT=sandbox
PROVIDER_AIRTEL_MONEY_CLIENT_ID=<from portal>
PROVIDER_AIRTEL_MONEY_CREDENTIAL_REF=AIRTEL_MONEY_CLIENT_SECRET
AIRTEL_MONEY_CLIENT_SECRET=<from portal>
PROVIDER_AIRTEL_MONEY_WEBHOOK_SECRET_REF=AIRTEL_MONEY_WEBHOOK_SECRET
AIRTEL_MONEY_WEBHOOK_SECRET=<from portal, if signed callbacks>
PROVIDER_AIRTEL_MONEY_TIMEOUT_SECONDS=15
```

Production uses `https://openapi.airtel.mw` and `PROVIDER_AIRTEL_MONEY_ENVIRONMENT=production`.
Never put these values in mobile or frontend bundles.

## Payment instruments (M016)

Collection APIs 2.0 swagger still does not document a reusable customer-account
token. POMPO therefore does **not** enroll live Airtel Money as a saved payment
method and does not store Airtel PINs. Sandbox "Test Airtel Money" instruments
use the simulated provider only. See `pompo-backend/docs/payment-instruments.md`.
