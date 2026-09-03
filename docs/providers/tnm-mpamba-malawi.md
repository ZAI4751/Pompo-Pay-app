# TNM Mpamba Malawi — M017 contract capture

This file is the in-repository approval record for the TNM Mpamba Malawi
adapter. Items are tagged:

- **VERIFIED** — observed on TNM-owned or TNM-published surfaces on 2026-09-03
- **TNM CONTRACT DEPENDENCY** — required for live HTTP; not available from
  public TNM materials. Isolated behind `ProviderRegistry`. Not invented.
- **REJECTED SOURCE** — aggregator/SDK material that is not a TNM contract

Do not treat Malipo, PayChangu, GitHub SDKs, Medium posts, or unofficial
clients as TNM sources.

`AUTHORITATIVE_CONTRACTS` must stay empty for `tnm_mpamba` until this file
records verified endpoints, authentication, payloads, and callback signing
from TNM-owned documentation or an authenticated TNM partner pack.

## Official sources inspected

| Source | What it established |
|--------|---------------------|
| https://www.tnm.co.mw | Telekom Networks Malawi Plc exists; enterprise contact `enterprisecare@tnm.co.mw`. |
| https://www.tnm.co.mw/website-api/storage/384/STRATEGIC-CHANNELS-MANAGER.pdf | TNM job description lists **Mpamba** wallet/agent growth and **Merchant Payments** expansion as commercial functions. |
| https://www.tnmmpamba.co.mw | TNM Mpamba consumer site exists. The fetched public HTML did not include API hosts, swagger, or partner docs. |
| TNM LinkedIn (TNM always with you), 2024-08-13 | **Mpamba Business Wallet** is a TNM product. Activation described as USSD `*444#`, option 7. |
| NBS Bank plc news, 2020-09-13 (`nbs.mw`) | TNM Mpamba Limited is named as Malawi's digital financial services provider; bank↔wallet push uses USSD `*444#`, not a public HTTP collection API. |

No TNM developer portal, OpenAPI host, or partner swagger was found on TNM-owned
surfaces. Collection/merchant HTTP remains a **TNM CONTRACT DEPENDENCY**.

## REJECTED sources (not used)

| Source | Why rejected |
|--------|----------------|
| https://malipo.mw/documentation | Aggregator API (`app.malipo.mw`). Not TNM. |
| https://developer.paychangu.com | Aggregator. Not TNM. |
| Unofficial GitHub SDKs claiming Mpamba URLs | Not TNM-owned. Paths/keys are not authoritative. |
| `tnm.co.mw/website-api/storage/…` | TNM careers CMS files. Not a payment API. |

## Environment separation

**TNM CONTRACT DEPENDENCY.** Sandbox and production base URLs were not published
on inspected TNM surfaces.

POMPO config keys exist so a later partner pack can be wired without renaming:

```text
PROVIDER_TNM_MPAMBA_BASE_URL
PROVIDER_TNM_MPAMBA_ENVIRONMENT
PROVIDER_TNM_MPAMBA_CLIENT_ID
PROVIDER_TNM_MPAMBA_CREDENTIAL_REF
PROVIDER_TNM_MPAMBA_WEBHOOK_SECRET_REF
PROVIDER_TNM_MPAMBA_TIMEOUT_SECONDS
```

Do **not** put guessed hosts in `PROVIDER_TNM_MPAMBA_BASE_URL`. Setting these
variables does **not** make the adapter `live_contract_ready`. The adapter
never calls a TNM host until this document records a verified URL and the
mapper is registered in `AUTHORITATIVE_CONTRACTS`.

Production rails remain blocked unless `APP_ENV=production` (existing
credential resolver).

## Country / currency (VERIFIED at product level)

TNM Mpamba is a Malawi mobile-money product. POMPO already restricts live
payments to **MWK**. No TNM HTTP field names for country/currency were verified.

## Authentication

**TNM CONTRACT DEPENDENCY.** Mechanism unknown: OAuth, API key, mutual TLS,
VPN, or another partner scheme. Token lifecycle, scopes, and error bodies were
not published.

POMPO will not send client secrets, invent grant types, or cache tokens until
the mechanism is documented here.

## Payment initiation

**TNM CONTRACT DEPENDENCY.** Path, method, headers, body, and idempotency
semantics were not published.

POMPO transaction reference remains the canonical POMPO identity. Any TNM
reference required by a future contract will be stored on `PaymentAttempt`
without replacing the POMPO reference.

The adapter does not POST. `supports_push_payment` is false until initiation
is documented.

## Customer authorization (VERIFIED at product level, HTTP BLOCKED)

Verified customer channels:

- USSD `*444#` (TNM/NBS/LinkedIn materials)
- Mpamba Business Wallet via the same USSD menu (TNM LinkedIn)

**TNM CONTRACT DEPENDENCY:** whether merchant collection uses USSD push, app
approval, PIN on the TNM app, OTP, or another flow for API-initiated payments.

POMPO must not store Mpamba PIN, OTP, or TNM passwords. Saved-Mpamba tokens
are not invented. Until a collection HTTP contract exists, checkout cannot
honestly claim “approve on TNM” for a POMPO-initiated payment.

## Payment instruments (M016)

**TNM CONTRACT DEPENDENCY.** No reusable account/tokenization API was published.

POMPO does **not** enroll live TNM Mpamba as a saved payment method. Catalog
row is unavailable. Sandbox “saved mobile money” continues to use the
simulated provider only.

## Status enquiry

**TNM CONTRACT DEPENDENCY.** No status URL, polling interval, or timeout
guidance was published. POMPO will not poll an invented endpoint.

## Callbacks / webhooks

**TNM CONTRACT DEPENDENCY.** Endpoint, headers, signature algorithm, signed
input, replay window, event identity, and payload were not published.

Inbound route `POST /api/v1/webhooks/tnm_mpamba` remains the M010 generic
path. The TNM adapter **fail-closes** verification and does not parse
invented callback JSON. Simulated HMAC (`x-pompo-signature`) is not treated
as a TNM signature.

## Status tokens / error codes

**TNM CONTRACT DEPENDENCY.** No official success/failure/pending tokens or
error table was published. POMPO does not invent mappings.

Retry classification for a future HTTP mapper:

- Retryable (existing POMPO policy): timeout, connection failure, HTTP 5xx, 429
- Non-retryable: invalid credentials, malformed request, rejected payment
- POST is never transport-retried (`ProviderHttpClient`)

Until HTTP exists, initiation is a non-retryable unsupported operation.

## Health

**TNM CONTRACT DEPENDENCY.** No public health path was verified. Health reports
`contract_ready=false` and does not probe a guessed host. A missing contract
must not auto-disable other providers.

## Settlement (TNM CONTRACT DEPENDENCY)

No TNM Malawi settlement file/API contract was published on inspected
surfaces. M011 remains provider-neutral. Do not build a TNM settlement system.

## Merchant requirements (VERIFIED at commercial level)

TNM recruits merchant-payment channel capacity and offers Mpamba Business
Wallet. Partner API onboarding is not self-serve on the public web. Contact
TNM enterprise (`enterprisecare@tnm.co.mw`) / Mpamba commercial teams for a
partner pack. POMPO does not automate that onboarding.

## QR / POS

POMPO QR remains POMPO-signed. There is no TNM-specific POMPO QR format.
POS continues to call POMPO integration APIs, never TNM.

If a future TNM contract supports collection, QR checkout selects payment
method `mobile_money` / provider `tnm_mpamba` and still goes
`PaymentService → ProviderRegistry → TnmMpambaMalawiAdapter`.

## Adapter behaviour until the contract arrives

| Flag | Value |
|------|--------|
| `live_contract_ready` | false |
| `supports_push_payment` | false |
| `supports_status_query` | false |
| `supports_webhooks` | false |
| `supports_qr` | false |
| `supports_payment_instruments` | false |
| Catalog `is_active` | false (not default) |
| Catalog `is_simulated` | false (real rail, contract pending) |

Simulated sandbox adapters remain the default payment rail.
Airtel Money Malawi is unchanged.
