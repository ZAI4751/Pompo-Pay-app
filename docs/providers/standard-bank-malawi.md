# Standard Bank Malawi — M018 contract capture

This file is the in-repository approval record for the Standard Bank Malawi
card/acquiring rail. Items are tagged:

- **VERIFIED** — observed on Standard Bank Malawi–owned surfaces on 2026-09-03
- **STANDARD BANK CONTRACT DEPENDENCY** — required for live HTTP; not available
  from public Standard Bank Malawi materials. Isolated behind `ProviderRegistry`.
  Not invented.
- **REJECTED SOURCE** — group portals, vendor generic docs, or aggregator
  material that is not a Standard Bank Malawi HTTP contract

`AUTHORITATIVE_CONTRACTS` must stay empty for `standard_bank` until this file
records verified hosts, authentication, payloads, 3-D Secure / hosted-page
return behaviour, and callback signing from Standard Bank Malawi–owned
documentation or an authenticated Card and Payments Malawi partner pack.

Do **not** invent a Standard Bank or N-Genius API from third-party blogs.

## Official sources inspected

| Source | What it established |
|--------|---------------------|
| https://www.standardbank.co.mw/malawi/business/ways-to-bank/self-service-banking/merchant-solutions | Merchant solutions: Visa and Mastercard acceptance; purchases, refunds, and reversals; mark-off file to device level; end-of-day terminal banking; daily/monthly statements. Contact path: call 242 / branch. Link to Ecommerce Gateway FAQs. |
| https://www.standardbank.co.mw/static_file/Malawi/Downloadable%20files/EcommerceGatewayFAQs.pdf | **E-commerce gateway** accepts physical cards (number, expiry, CVV) and virtual cards. Access requires a **Standard Bank business account**. Onboarding: email `CardandPaymentsMalawi@standardbank.co.mw` with subject `e-commerce gateway request`. Commercial agreement precedes integration. Portal login is issued by email after forms. Three **deployment models** (product description only): (1) **Hosted Payment Page** / Pay Page — described as PCI DSS compliant; (2) **Direct API** — REST JSON; Direct API merchants must consider PCI-DSS for capturing/transmitting card details; (3) **Invoicing (Pay-by-Link) via N-Genius Online APIs**. Commission charged to the business; end users are not charged. |
| https://www.standardbank.co.mw/static_file/Malawi/Downloadable%20files/POSMerchantStandardTCs2020.pdf | POS merchant T&Cs: card present and card-not-present; **Authenticated Procedures** (bank-approved); merchant may use a Standard Bank–approved **Payment Service Provider**; processing via POS device or bank-approved web system; Merchant Portal for viewing/reconciling transactions. |

No Standard Bank Malawi developer portal, OpenAPI host, sandbox base URL, or
partner swagger was found on `standardbank.co.mw`. Collection/acquiring HTTP
remains a **STANDARD BANK CONTRACT DEPENDENCY**.

## Actual integration model (product-level)

Distinguished from POMPO-callable HTTP:

| Model | Status |
|-------|--------|
| A. Bank account payment (A2A / debit order API) | **Not verified** as a public merchant collection API for this rail. Business Online / host-to-host are corporate banking channels, not this e-commerce gateway. |
| B. Card acquiring | **VERIFIED** commercially: Visa/Mastercard merchant acceptance. |
| C. Payment gateway | **VERIFIED** as a product: Standard Bank e-commerce gateway. |
| D. Bank-hosted payment page | **VERIFIED** as a deployment model (Hosted Payment Page / Pay Page). Preferred PCI boundary when a contract exists: card data stays on the bank page. |
| E. Tokenized card payment | **STANDARD BANK CONTRACT DEPENDENCY.** No public tokenization/vault API. |
| F. POS / acquirer terminals | **VERIFIED** commercially (POS T&Cs, terminals, mark-off file). POS devices talk to the bank; POMPO POS must still call **POMPO APIs**, not the bank, unless a later approved architecture says otherwise. |

POMPO must not assume the merchant solution is a public REST collection API.
Live calls require a partner pack from Card and Payments Malawi.

Until that pack is in this file, `live_contract_ready` stays false and no host
is contacted.

## REJECTED sources (not used)

| Source | Why rejected |
|--------|----------------|
| https://developer.standardbank.com | Standard Bank **Group** API marketplace (SnapScan, SBSA QR, Standard Bank Pay, Send Money). Not Malawi N-Genius e-commerce. Sign-in required; no Malawi acquiring swagger was established from public pages. |
| Network International / generic N-Genius Online developer docs | Platform **name** appears in the Malawi FAQ. Generic vendor URLs, identity-token paths, and payloads were **not** published by Standard Bank Malawi. Copying them would invent a Malawi contract. |
| TechCartel / other gateway round-ups | Not Standard Bank Malawi. |
| Unofficial GitHub N-Genius SDKs | Not bank-owned. |

## Environment separation

**STANDARD BANK CONTRACT DEPENDENCY.** Sandbox and production base URLs were
not published on inspected Standard Bank Malawi surfaces.

POMPO config keys exist so a later partner pack can be wired without renaming:

```text
PROVIDER_STANDARD_BANK_BASE_URL
PROVIDER_STANDARD_BANK_ENVIRONMENT
PROVIDER_STANDARD_BANK_CLIENT_ID
PROVIDER_STANDARD_BANK_CREDENTIAL_REF
PROVIDER_STANDARD_BANK_WEBHOOK_SECRET_REF
PROVIDER_STANDARD_BANK_TIMEOUT_SECONDS
```

Do **not** put guessed N-Genius hosts in `PROVIDER_STANDARD_BANK_BASE_URL`.
Setting these variables does **not** make the adapter `live_contract_ready`.
The adapter never calls a bank host until this document records a verified URL
and the mapper is registered in `AUTHORITATIVE_CONTRACTS`.

Production rails remain blocked unless `APP_ENV=production` (existing
credential resolver).

## Country / currency (VERIFIED at product level)

Standard Bank Plc Malawi is licensed by the Reserve Bank of Malawi. POMPO
already restricts live payments to **MWK**. Gateway FAQ mentions “a wide range
of currencies” for hosted pages; HTTP field names were not verified.

## Authentication

**STANDARD BANK CONTRACT DEPENDENCY.** Portal username/password is issued by
email after onboarding. API authentication (OAuth, API key, identity token,
mTLS) was not published.

POMPO will not send client secrets, invent grant types, or cache tokens until
the mechanism is documented here. Portal passwords are not API credentials and
must never be stored in POMPO.

## Payment initiation

**STANDARD BANK CONTRACT DEPENDENCY.** Path, method, headers, body, hosted-page
redirect URL, and idempotency semantics were not published.

POMPO transaction reference remains the canonical POMPO identity. Any bank
reference required by a future contract will be stored on `PaymentAttempt`
without replacing the POMPO reference.

The adapter does not POST. `supports_push_payment` is false until initiation
is documented.

## Customer authorization / 3-D Secure

POS T&Cs require bank-approved **Authenticated Procedures** for relevant
transactions. The e-commerce FAQ does not name 3DS, OTP, or redirect URLs.

**STANDARD BANK CONTRACT DEPENDENCY:** whether checkout uses 3-D Secure,
OTP, a hosted Pay Page, or another bank-controlled flow.

POMPO must not collect card PIN, CVV, full PAN, or banking passwords.
There is no universal PIN form. Until a contract exists, checkout cannot
honestly claim “continue on Standard Bank” for a POMPO-initiated payment.

If a future hosted-page contract requires a redirect:

```text
POMPO payment created → authorization_required → provider page → return/callback → PaymentService
```

Secrets stay off the mobile app.

## Payment instruments (M016) / tokenization

**STANDARD BANK CONTRACT DEPENDENCY.** No reusable card token / network token
/ vault API was published.

POMPO does **not** enroll live Standard Bank Visa or Mastercard as a saved
payment method. Catalog rows are unavailable. Sandbox saved cards continue to
use the **simulated** provider only.

POMPO will not build a card vault. Tokenization, if any, must be owned by the
bank, scheme, or a PCI-compliant processor named in the partner pack.

## Status enquiry

**STANDARD BANK CONTRACT DEPENDENCY.** No status URL, polling interval, or
timeout guidance was published.

## Callbacks / webhooks

**STANDARD BANK CONTRACT DEPENDENCY.** Endpoint, headers, signature algorithm,
signed input, replay window, event identity, and payload were not published.

Inbound route `POST /api/v1/webhooks/standard_bank` remains the M010 generic
path. The adapter **fail-closes** verification and does not parse invented
callback JSON. Simulated HMAC (`x-pompo-signature`) is not treated as a bank
signature.

## Refunds / reversals

**VERIFIED** as merchant **product** transaction types (purchases, refunds,
reversals) on the Merchant Solutions page.

**STANDARD BANK CONTRACT DEPENDENCY** for HTTP: no refund vs reversal
endpoints, amount rules, or idempotency were published. Adapter
`supports_refund` stays false. POMPO will not add ad-hoc refund tables.
Existing `transactions:refund` permission still has no HTTP implementation.

## Settlement / reconciliation

**VERIFIED** commercially: mark-off file (device level), automatic end-of-day
terminal banking, daily reports and monthly statements.

**STANDARD BANK CONTRACT DEPENDENCY** for mapping into M011: file format,
delivery channel, and field names were not published. Do not build a
Standard Bank–specific reconciliation system. When a format is documented,
map into existing settlement ingestion.

## Error codes / retry

**STANDARD BANK CONTRACT DEPENDENCY.** No official success/failure/pending
tokens or error table was published.

Until HTTP exists, initiation is a non-retryable unsupported operation.
A future POST must not be transport-retried (`ProviderHttpClient`).

## Health

**STANDARD BANK CONTRACT DEPENDENCY.** No public health path was verified.
Health reports `contract_ready=false` and does not probe a guessed host.

## Merchant requirements (VERIFIED commercially)

- Standard Bank business account for e-commerce gateway
- Signed commercial agreement before integration
- Forms + credentials via `CardandPaymentsMalawi@standardbank.co.mw`
- POS: bank-approved equipment / Payment Service Provider

POMPO does not automate that onboarding.

## QR / POS

POMPO QR remains POMPO-signed. There is no Standard Bank–specific POMPO QR
format. POS continues to call POMPO integration APIs, never the bank API.

If a future contract supports collection, QR checkout selects payment method
`card` / provider `standard_bank` and still goes
`PaymentService → ProviderRegistry → StandardBankMalawiAdapter`.

## PCI / security boundary (not a compliance claim)

POMPO is **not** claiming PCI DSS certification.

Intended boundary until a partner pack exists:

- Application database must not store PAN, CVV/CVC, card PIN, or portal passwords.
- Enrollment APIs reject those fields (`reject_secret_fields`).
- Direct API card capture would expand PCI scope; it is **not** implemented.
- Hosted Payment Page is the bank-described PCI-safer model; it is **not**
  wired because return URLs, session tokens, and signatures are undocumented.
- Logs must not contain PAN, CVV, secrets, or authorization headers.
- Duplicate charges: existing PostgreSQL idempotency + no invented POST.

## Adapter behaviour until the contract arrives

| Flag | Value |
|------|--------|
| `live_contract_ready` | false |
| `supports_push_payment` | false |
| `supports_status_query` | false |
| `supports_refund` | false |
| `supports_webhooks` | false |
| `supports_qr` | false |
| `supports_payment_instruments` | false |
| Catalog `is_active` | false (not default) |
| Catalog `is_simulated` | false (real rail, contract pending) |
| Catalog payment methods | `card` |

Simulated sandbox adapters remain the default payment rail.
Airtel Money Malawi and TNM Mpamba are unchanged.
National Bank and FDH remain unstructured-contract stubs.
Do not start another bank (NBS, First Capital) from M018.
