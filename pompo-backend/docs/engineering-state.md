# POMPO Engineering State

## CURRENT MILESTONE
M018 Standard Bank Malawi: named `StandardBankMalawiAdapter` behind
ProviderRegistry. Public merchant/e-commerce material confirms Visa/Mastercard
acquiring and a hosted-page / Direct API / Pay-by-Link product on N-Genius, but
no Standard Bank Malawi HTTP contract is in the repository. Live initiation,
3DS/hosted-page return, webhooks, tokenization, refunds, and settlement-file
mapping are STANDARD BANK CONTRACT DEPENDENCY and remain disabled. Simulated
sandbox stays the default rail. Airtel and TNM are unchanged.

Do not start another bank or M019.

See `docs/providers/standard-bank-malawi.md`.

## COMPLETED MILESTONES
M001 backend foundation; M002 domain model and database; M003 authentication;
M004 Phase 1 RBAC foundation; M004 Phase 2 authorization engine.
M005 merchant and branch administration vertical slice.
M006 payment core; live migration and Docker acceptance verified.
M007 provider contracts, registry, mock adapters, and payment integration implemented.
Operational till management, provider catalog, and admin integration.
Provider management APIs, routing, health, failure taxonomy, stub rails,
simulated variants, and Master Admin wiring.
M008 outbound HTTP client, credential-reference resolution, sandbox/production
gating, and admin contract-readiness visibility.
M009 QR payments; M010 inbound webhooks; M011 settlement/reconciliation;
M012 unified mobile app; M013 POS / developer platform;
M014 Airtel Money Malawi; M015 customer product / everyday utility;
M016 payment instruments / unified checkout; M017 TNM Mpamba Malawi
(adapter + contract capture; live HTTP blocked); M018 Standard Bank Malawi
(adapter + contract capture; live HTTP blocked).

## CURRENT ARCHITECTURE
FastAPI routes use dependencies, services, repositories, and async SQLAlchemy.
Authentication resolves identity; authorization resolves catalog permissions.
RBAC administration is under `/api/v1/rbac`; organization administration is under
`/api/v1/organization` (merchants, branches, tills). Payment APIs remain under
`/api/v1/payments`. Provider administration is under `/api/v1/providers`.
`/payments/providers` remains as a compatibility catalog surface.

Payment core path:

```text
PaymentService → select_provider → ProviderRegistry → ProviderAdapter
```

## DATABASE STATE
PostgreSQL migration graph head is `0019_m018_standard_bank` (parent
`0018_m017_tnm_mpamba`).
M018 updates the `standard_bank` catalog row (display name, capabilities,
card payment method). No new tables.
M017 updated the `tnm_mpamba` catalog row.
M016 adds `payment_instruments` and `transactions.payment_instrument_id`.
Token references are HMAC digests; PINs/CVVs/PANs are not stored.
M015 adds customer preferences, merchant favorites, payment requests, bill
splits, in-app notifications, support requests, and a partial unique index
on active user phones.
M008 required no schema change; attempt correlation metadata fits in existing
`provider_request` / `provider_response` JSON.
`0008` adds `provider_type`, `health_state`, `config_refs` on
`payment_providers`; `failure_code` and `retryable` on `payment_attempts`;
and `providers:create` for platform administrators.
Provider rows are still not seeded by migration. Use
`scripts/seed_providers.py` in non-production environments.

## PROVIDER ARCHITECTURE
`ProviderCode`, catalog definitions, registry adapter codes, and
`payment_providers.code` are the same identifiers.

Default registry:

- simulated (success) — live-contract-ready
- simulated_pending / simulated_failure / simulated_timeout — live-contract-ready, inactive by default
- airtel_money — Airtel Money Malawi Collection contract; inactive until credentials are configured and a platform admin enables it
- tnm_mpamba — TnmMpambaMalawiAdapter; not live-contract-ready; HTTP is a TNM CONTRACT DEPENDENCY
- standard_bank — StandardBankMalawiAdapter; not live-contract-ready; HTTP is a STANDARD BANK CONTRACT DEPENDENCY
- national_bank, fdh_bank — structured stubs, not live HTTP

`AUTHORITATIVE_CONTRACTS` registers `(airtel_money, sandbox|production)` from
`docs/providers/airtel-money-malawi.md`. TNM is captured in
`docs/providers/tnm-mpamba-malawi.md` but is **not** registered until TNM HTTP
is verified. Standard Bank is captured in `docs/providers/standard-bank-malawi.md`
but is **not** registered until Standard Bank Malawi HTTP is verified.

Airtel, TNM, and Standard Bank are never the unconditional default. Routing still prefers the lowest
priority active, matching, live-contract-ready provider. Simulated remains
priority 1.

Capabilities are explicit on the adapter (`supports_push_payment`,
`supports_status_query`, `supports_cancel`, `supports_refund`,
`supports_webhooks`, `supports_qr`). The core does not call unsupported
operations. Adapters never mutate transaction rows.

Health states: `active`, `disabled`, `degraded`, `unavailable`.
Registered ≠ operational. Health also reports `configured`, `contract_ready`,
and `reachable`. A rail without a live contract never appears as a working
production payment rail.

Configuration: environment references only. API returns `auth_configured` /
`signing_configured` / `base_url_configured` / `configuration_complete` /
`rail_environment` / `production_rail_permitted` / `contract_registered`.
Never secret values. Production credentials cannot be resolved when
`APP_ENV` is development or testing.

Outbound HTTP: `ProviderHttpClient` (httpx) with connect/read/write/pool
timeouts, pooling, `X-Request-ID` correlation, and HTTP-status translation into
the existing provider error taxonomy. POST is not retried at the transport
layer. Request bodies, Authorization, and API keys are not logged.

Routing: deterministic priority among active, matching, live-contract-ready
providers whose catalog environment is allowed for `APP_ENV`. Explicit
`provider_code` is validated against the same rules.

Failures: timeout / unavailable / rate limited are retryable; authentication,
invalid request, rejected, duplicate, unknown are not. Max three attempts.
Provider idempotency key is the POMPO transaction reference. PostgreSQL
unique constraints remain the financial identity authority.
Webhook engine is implemented for simulated rails and Airtel Money Malawi
callbacks (`POST /api/v1/webhooks/{provider_code}`). Attempts store
`provider_transaction_id` and `correlation_id` for later matching.

HTTP:

- `GET/POST /providers`
- `GET/PATCH /providers/{provider_code}`
- `POST /providers/{provider_code}/enable`
- `POST /providers/{provider_code}/disable`
- `GET /providers/{provider_code}/health`

RBAC: `providers:read` (also `transactions:read` for catalog reads),
`providers:create`, `providers:update`. Mutations are platform-admin only.
Merchants cannot change global rails.

## USER ADMINISTRATION
Customers can self-register at `POST /customers/register` (email/password,
existing JWT sessions). SMS phone verification is `not_configured`.
Role assignment remains `PUT /rbac/users/{user_id}/role` for a known user id.
There is still no general user-directory CRUD API.

## PAYMENT API COMPLETENESS
Usable by future POS/mobile clients for create, get-by-reference, cancel, and
process against simulated or Airtel-backed adapters once merchant, branch, till,
and an active catalog provider exist. `provider_code` may be omitted to use
deterministic routing. Airtel is not the global default.

Deferred: refunds, TNM, and bank HTTP adapters. Customer history search is
`GET /payments/mine`. Merchant activity search is `GET /payments`.

`QR_GENERATED` and `PENDING_USER_PIN` remain enum values for a future QR/PIN
checkout. They are not in `TRANSITIONS` and cannot be applied.

## FRONTEND INTEGRATION STATE
The admin frontend (`pompo-frontend`, Next.js) is a live control plane for
every capability the backend already exposes:

REAL API INTEGRATED: authentication (`/auth/login`, `/refresh`, `/logout`,
`/me`); RBAC roles/permissions/grants; merchant, branch, and till CRUD
(soft-delete); payment get-by-reference plus cancel/process; provider catalog
list/detail/enable-disable/health; health/readiness/liveness; QR codes;
inbound provider webhooks; settlements/reconciliation; integration API clients
and hashed API keys (`/api-keys`).

Effective permissions are loaded from `GET /rbac/roles/{role_id}`
(`permission_codes`). `/auth/me` still does not return permission codes.

MOCK / NOT YET AVAILABLE: user directory, audit logs, reports, TNM and bank
live adapters.

`NEXT_PUBLIC_USE_MOCKS=true` is opt-in demo mode. The default is live API.
Local Master Admin sign-in uses a seeded platform administrator; the frontend
does not contain credentials. Simulated providers are labeled as simulated.
Provider secret fields show Configured / Not configured only.

CORS is the outermost middleware so rate-limit (429), trusted-host (400) and
unhandled-error (500) responses remain readable by the browser. The frontend
API client distinguishes network failure from each HTTP status and preserves
the backend `request_id`. See docs/decisions.md, "Admin frontend
integration: cross-origin error surfacing".

## AUTHENTICATION STATE
JWT access tokens, rotated server-backed refresh sessions, replay detection,
logout, and active-user checks are implemented.

## AUTHORIZATION STATE
Exact permission checks, 401/403 semantics, inactive/soft-deleted user and
inactive-role protection, custom delegation limits, protected system roles,
tenant-scope primitives, RBAC administration, and audit records are implemented.
The system retains one role per user; role removal is rejected because the
current schema requires a role.

## KNOWN ISSUES
Role ownership is global because the existing schema has no role merchant ID.
Mypy reports baseline errors in shared pre-M004 modules and third-party
packages without stubs.
Ruff reports baseline errors in pre-existing modules (models, auth service,
older tests, migrations).
Branch managers can still `PATCH` a till `is_active: false` with only
`tills:update`, which bypasses `tills:delete` (reported, not fixed in this
slice).

## KNOWN TEST LIMITATIONS
Docker-backed tests are the acceptance environment; run them in-container per
docs/testing.md Option A. The backend container bind-mounts `app/`, `tests/`,
`migrations/` and `scripts/`, so in-container runs reflect the working tree
rather than the image build.

Host execution (Option B) fails on this machine: a locally installed
PostgreSQL owns host port 5432 and shadows the container's published port, so
host runs authenticate against the wrong database
(`asyncpg.exceptions.InvalidPasswordError`). This is the conflict documented in
docs/testing.md, "Diagnosing connection failures", item 2. Use Option A.

Ruff is a development dependency and is not installed in the backend image;
run it from the host virtualenv.

## IMPORTANT ARCHITECTURAL DECISIONS
Permissions are immutable catalog contracts. No wildcard permissions or
multi-role user table was introduced. RBAC mutation policy is enforced in the
service layer and recorded through the existing AuditLog model.
Provider catalog identifiers must match `ProviderCode`. Stub adapters are not
live rails. Sandbox provider seeding must never run in production.
Financial idempotency is PostgreSQL, not Redis.

## NEXT MILESTONE
Do not start another bank or M019 from M018.

Also outstanding:
- `transactions:refund` permission exists with no refund route or service method.
- `PaymentService.create_attempt()` and the `PaymentTransition` schema have no
  HTTP endpoint.
- `/auth/me` still omits effective permission codes; the admin loads them from
  `GET /rbac/roles/{role_id}` instead.
- SMS OTP and push notification vendors are not configured.
- Provider retries are operator/client re-invocations of `POST .../process`,
  not a Celery worker for payment processing.
