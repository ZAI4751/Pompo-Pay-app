# Architectural Decisions

Chronological log of non-obvious engineering decisions and why they were
made. Add a new dated entry rather than editing old ones — history is the
point.

---

## 2026-08-23 — M003: Authentication & Identity

### Password hashing library: bcrypt directly, not passlib

**Decision:** Replace `passlib.context.CryptContext` with the `bcrypt`
library called directly.

**Why:** The inherited M001 foundation used `passlib[bcrypt]`. Building
M003's first password-hashing test immediately failed with
`ValueError: password cannot be longer than 72 bytes` — not because any
test password was actually long, but because passlib's *internal*
self-test (`detect_wrap_bug`) hashes a synthetic 96+ byte secret to probe
for a historical bcrypt bug, and modern `bcrypt` (>=4.1) raises instead of
silently truncating. Passlib has had no release since 2020 and does not
handle this. Pinning `bcrypt` to an older release papers over it but leaves
a fragile, unmaintained dependency in the password path indefinitely.
Calling `bcrypt.hashpw` / `bcrypt.checkpw` directly removes the layer
entirely — fewer moving parts for the single most security-sensitive code
path in the system. We truncate input to 72 bytes ourselves before hashing
(bcrypt's own limit) so a legitimately long password fails safely instead
of crashing.

### Refresh tokens: self-contained JWT + server-side session row (hybrid)

**Decision:** Refresh tokens are still signed JWTs (reusing the existing
`JWTConfig`), but each one's `jti` claim maps to a `refresh_sessions` row
that is the actual source of truth for validity.

**Why:** A pure stateless JWT refresh token can't be revoked before its
natural expiry — logout, replay detection, and "sign out this one device"
are all impossible without server-side state. A pure opaque server-side
token (no JWT) works too, but reusing the existing signed-JWT
infrastructure meant no new token format, and the signature still gives a
cheap first-pass rejection of forged tokens before the DB is even queried.

### Refresh-token rotation with family-based replay detection

**Decision:** Every refresh call revokes the presented session and issues a
new one carrying the same `family_id`. If a session that's already revoked
is presented again, the *entire* family is revoked, not just that one
session.

**Why:** Single-use refresh tokens mean a stolen-but-unused token becomes
worthless the moment the legitimate client rotates it. The harder case is:
what if the attacker rotates it first? Then the legitimate client's next
refresh attempt is the one that gets "replayed" against an already-revoked
session — at that point we can't tell attacker from owner, so the only
safe response is to kill the whole lineage and force a fresh login
everywhere. This is the standard "refresh token family revocation" pattern
(used by e.g. Auth0, IdentityServer).

### Refresh token hashing: SHA-256, not bcrypt

**Decision:** The raw refresh token is never persisted; `refresh_sessions.
token_hash` stores `sha256(raw_token)`, not a bcrypt hash.

**Why:** Bcrypt (and other slow KDFs) exist to defend low-entropy secrets
(human passwords) against offline brute-force. A refresh token is a
256-bit-signature-backed random-looking string with far more entropy than
any password — brute-forcing it isn't the threat model. The threat here is
"don't let a raw, directly-usable credential sit in the database", which a
fast cryptographic hash already solves, without paying bcrypt's
deliberate CPU cost on every single refresh call.

### Login error responses are deliberately generic

**Decision:** Unknown email, wrong password, and disabled account all
return the same `401 Incorrect email or password`, with a constant-ish
timing profile (see `get_dummy_password_hash`).

**Why:** Distinguishing these cases in the API response (or via timing)
lets an attacker enumerate valid merchant/staff emails before ever
guessing a password. The generic response trades a small amount of UX
clarity ("which part did I get wrong?") for closing that enumeration
channel — standard practice for any system handling payments.

### Logout is idempotent and never errors on an invalid token

**Decision:** `POST /auth/logout` always returns `204`, even if the token
is malformed, unknown, or already revoked.

**Why:** Same reasoning as login: logout responses shouldn't reveal
whether a token was valid. It also means a client can safely call logout
defensively (e.g. on every app close) without needing to track whether it
already did.

### Access tokens are not server-side revocable

**Decision:** Access tokens are pure stateless JWTs with no session-table
backing; logout only revokes the *refresh* session.

**Why:** Explicitly scoped this way rather than half-implementing
revocation. Making access tokens revocable would mean a DB round-trip on
every authenticated request (defeating the point of a stateless JWT) or an
in-memory/Redis blocklist synced across instances. Given access tokens are
short-lived (`jwt_access_token_expire_minutes`, default 30 min), the
mitigation is simply keeping that window small — a full access-token
revocation/blocklist is deferred until there's a concrete requirement for
it (e.g. "instantly kill a compromised session" becomes a product
requirement, not just a nice-to-have).

### JWT issuer/audience claims: deferred

**Decision:** Did not add `iss` / `aud` claims in this milestone, despite
the M003 brief listing them as configurable "where appropriate".

**Why:** Issuer/audience matter when multiple trust domains consume the
same tokens (e.g. a separate POS-integration service validating Pompo
tokens independently). Right now there is exactly one token issuer and one
consumer (this API). Adding the claims now would be unused configuration
surface with no current caller to validate it — revisit when M020 (POS
APIs) or M021 (API Keys & Developer Platform) introduces an actual second
consumer.

---

## 2026-08-25 — M004 Phase 3: RBAC Administration

### Administration is service-owned

RBAC routes are intentionally thin. `RBACService` owns mutation rules,
including required actor permissions, protected system roles, delegation
limits, tenant scope checks, and audit records. Route dependencies provide
early 401/403 enforcement, but service checks remain authoritative for any
non-HTTP caller.

### System-defined permissions and protected roles

Permissions remain immutable catalog data. Custom roles can be created,
updated, and deactivated. System roles cannot be modified or deleted, and
reserved system-role codes cannot be created as custom roles. No wildcard
permissions were introduced.

### Single-role assignment semantics

M004 retains the required `users.role_id` relationship. Assignment replaces
the current role. Removal returns a conflict because the current schema does
not permit an unassigned user; multi-role or unassigned-user semantics are
deferred to a future migration.

### Tenant boundary limitation

User merchant/branch scope is enforced for assignments, and platform admins
may operate across tenants. Roles themselves are global in the existing
schema, so merchant-owned custom role management is deferred until the schema
has an explicit role ownership boundary.

---

## 2026-08-26 — M006: Payment Core

Payment idempotency is database-authoritative: transactions carry a
merchant-scoped unique idempotency key and a canonical request fingerprint.
Retries with the same equivalent request return the original transaction;
reusing a key for a different request is rejected. Payment lifecycle changes
are centralized in a state-transition map, and provider integrations remain
behind a protocol rather than being coupled to the orchestration service.

---

## 2026-08-26 — M007: Provider Adapter Architecture

Provider adapters return normalized requests and results through a registry;
provider-specific exceptions are translated into a shared taxonomy with an
explicit retryable flag. Mock adapters are the only implementations in this
milestone. No provider credentials are stored in the database or source, and
the payment service remains responsible for all transaction state transitions.

---

## 2026-08-25 — M005: Merchant and Branch Administration

### Tenant checks belong in the service layer

Organization services verify merchant and branch ownership for every read and
mutation. Platform administrators may cross merchant boundaries; branch-
assigned users remain restricted to their assigned branch. This prevents
IDOR/BOLA exposure when a caller provides a valid UUID outside its tenant,
including for non-HTTP callers.

### Organization deactivation uses soft deletion

Merchant and branch deletion sets both `is_active = false` and `deleted_at`.
Normal repository reads require both active state and no soft-delete timestamp,
while mutations create immutable audit records.

---

## 2026-08-31 — Admin frontend integration: cross-origin error surfacing

### CORS is the outermost middleware

**Decision:** Register `CORSMiddleware` last in `create_app()` so it becomes the
outermost layer, and handle unhandled exceptions in
`UnhandledExceptionMiddleware` from inside the stack rather than through
`@app.exception_handler(Exception)`.

**Why:** The admin frontend reported "Could not reach the Pompo backend" for
failures where the backend had in fact answered. `RateLimitMiddleware` and
`TrustedHostMiddleware` were registered *after* CORS, which — given Starlette
applies middleware in reverse registration order — placed them *outside* the
CORS layer. Their responses carried no `access-control-allow-origin`, so the
browser blocked them and `fetch()` rejected exactly as it does for an
unreachable host. A 429 was therefore indistinguishable from a dead backend.
Reproduced directly: the 101st request in a window returned
`HTTP 429` with no CORS headers.

The same applies to a FastAPI `Exception` handler, which Starlette installs on
`ServerErrorMiddleware` — outside all user middleware, including CORS. Genuine
500s were unreadable to the browser for the same reason.

`tests/test_middleware_cors.py` asserts the ordering invariant and that 429,
500 and trusted-host 400 responses all carry CORS headers. Security is
unchanged: a disallowed origin is still rejected without being granted
`access-control-allow-origin`.

### Validation errors never echo submitted values

**Decision:** Handle `RequestValidationError` explicitly and expose only
`loc`, `msg` and `type` per error.

**Why:** Pydantic includes the offending `input` in every error it raises. On
`/auth/login` a validation failure on the password field would place the
plaintext secret into both the response body and the structured logs. The
handler also replaces FastAPI's default shape, where `detail` is an array of
objects — a client rendering `String(detail)` on that produces
"[object Object]".

### Development CORS origins and rate limit live in docker-compose.yml

**Decision:** Set `CORS_ORIGINS` and `RATE_LIMIT_REQUESTS` in the `backend`
service's `environment:` block rather than relying on `.env` or code defaults.

**Why:** `.env` is untracked, so the values that make local development work
were invisible and drifted from the code defaults — `.env` pinned
`CORS_ORIGINS` to origins that excluded `http://127.0.0.1:3000`, silently
overriding the `DevelopmentSettings` default. Compose `environment:` takes
precedence over `env_file:`, which makes the development contract explicit and
version-controlled. Production inherits the restrictive base defaults and must
set both explicitly.

`http://localhost:3000` and `http://127.0.0.1:3000` are distinct origins to a
browser, so both are allowed in development. The rate limit is raised for
development only: inside Docker every request from the host arrives with the
gateway's IP, so a single bucket covers the whole development session.

### The backend container mounts the working tree

**Decision:** Bind-mount `./app`, `./tests`, `./migrations` and `./alembic.ini`
into the `backend` container.

**Why:** `docker/Dockerfile` bakes source in with `COPY . .`, so
`docker compose exec backend pytest` ran whatever was in the image at build
time. Since the Docker environment is the acceptance environment for
PostgreSQL integration tests, silently testing stale code undermines the whole
point. Specific subtrees are mounted rather than the whole context so the
image's installed dependencies are never shadowed. `./scripts` is also mounted
so seed commands run the working-tree scripts.

---

## 2026-09-01 — Operational payment chain: tills and provider catalog

### Dedicated till permissions, not branch permissions

**Decision:** Till administration uses `tills:read|create|update|delete` rather
than reusing `branches:*`.

**Why:** A branch manager who can update a branch address is not automatically
allowed to deactivate a checkout point. Payment creation already requires a
till; treating tills as a branch sub-field would hide a distinct operational
and audit boundary.

### Till branch and code are immutable after create

**Decision:** Reject `branch_id` and `code` on till update. Deactivate with
soft-delete instead of hard-delete or reassignment.

**Why:** Transactions reference `tills.id` with `ON DELETE RESTRICT`. Moving a
till to another branch or recycling its code would rewrite the operational
history of every payment taken at that checkout.

### Provider catalog is database-backed; registry stays in-process

**Decision:** `GET /payments/providers` reads `payment_providers` rows. The
default `ProviderRegistry` registers only `simulated`. Planned rails have
catalog rows that stay inactive and simulated until an adapter exists.

**Why:** An empty migrated database previously could not create payments
because no provider row existed. Seeding catalog metadata is an operations
concern; pretending mock adapters are live Airtel/TNM/bank rails is not.

### Sandbox provider seed is idempotent and production-refused

**Decision:** `scripts/seed_providers.py` inserts missing catalog rows only,
stores no secrets, and raises if `APP_ENV=production`.

**Why:** Repeatable local/dev provisioning must not be a migration (migrations
run in production) and must not be able to stamp sandbox placeholders onto a
production database by accident.

### User directory CRUD is deferred

**Decision:** Do not add staff user CRUD in this slice.

**Why:** The operational chain is merchant → branch → till → provider →
payment. A platform administrator already exists via `seed_admin.py` and can
exercise that chain. User CRUD is a privilege-escalation surface and belongs
in its own secured slice.

## 2026-09-01 — Provider management and real-rail foundation

### Payment core stays provider-neutral

**Decision:** `PaymentService` selects a provider only through
`select_provider` and talks to rails only through `ProviderAdapter`. Airtel,
TNM, and bank modules are stub adapters that raise unavailable; they do not
invent HTTP contracts.

**Why:** Hardcoding rail branches in the payment core would have to be
rewritten for every institution. Stubs keep the registry, catalog, and
routing honest before credentials exist.

### Secrets are references, never catalog values

**Decision:** Provider rows store environment-variable *names* in
`config_refs`. Runtime resolution checks whether the named secret is present
and returns only booleans to the API. Seed scripts and logs never print
secret values.

**Why:** Encrypting secrets in ordinary PostgreSQL columns without a key
hierarchy is not a justified design. Environment / secret-manager injection
is the supported path for development, sandbox, and production.

### Enablement is not the same as a live contract

**Decision:** An adapter may be registered (`adapter_configured`) while
`live_contract_ready` is false. Platform admins cannot enable those rails.
Simulated adapters are the only rails that can process payments.

**Why:** Registering a stub so the catalog and OpenAPI stay coherent must not
let an operator send money to an invented URL.

### Retry classification is bounded; identity stays in PostgreSQL

**Decision:** Timeout, unavailable, and rate-limited failures are retryable
up to three attempts. Authentication, invalid request, rejected, and
duplicate failures are not. Each attempt reuses the transaction reference as
the provider idempotency key. Redis is not the financial idempotency
authority.

**Why:** HTTP retries are not harmless. A new attempt number with a new
provider idempotency key would create a second payment after a timeout.

---

## 2026-09-01 — M008: Live provider HTTP readiness without invented contracts

### Do not invent provider APIs

**Decision:** `AUTHORITATIVE_CONTRACTS` is empty for TNM Mpamba, Standard Bank
Malawi, and remaining banks. Airtel Money Malawi is registered from
`docs/providers/airtel-money-malawi.md`.
TNM remains a named adapter (`TnmMpambaMalawiAdapter`) that is not
`live_contract_ready` until TNM-owned HTTP is documented in
`docs/providers/tnm-mpamba-malawi.md`.
Standard Bank Malawi remains a named adapter (`StandardBankMalawiAdapter`)
that is not `live_contract_ready` until Standard Bank Malawi HTTP is documented
in `docs/providers/standard-bank-malawi.md`. Public merchant FAQs are not an
API contract; N-Genius hosts must not be invented.

**Why:** Fabricated URLs, payloads, or signatures would be treated as real
money movement. The HTTP client, mapper protocol, and credential resolver exist
so the first real contract can be inserted without changing payment core.

### HTTP retries stay at the payment-attempt layer

**Decision:** `ProviderHttpClient` never retries POST/PUT/PATCH/DELETE. GET
health probes may be marked retry-safe for classification only; the client
still performs a single attempt. Payment retries remain operator/client
re-invocations of `POST .../process` with the same transaction reference as the
idempotency key.

**Why:** A transport retry after a timeout can double-charge if the first
request reached the institution.

### Production rails cannot run in development

**Decision:** Catalog `environment` `live`/`production` and
`PROVIDER_<CODE>_ENVIRONMENT=production` are refused for credential use and
enablement unless `APP_ENV=production`. Simulated adapters remain the
development payment rails.

**Why:** Sharing a `.env` that accidentally points at production credentials
must not send sandbox traffic to a live institution.

### Where a provider has no idempotency API

**Decision:** POMPO always sends the transaction reference as
`idempotency_key`. When a future mapper is added, it may copy that value into
the provider's documented idempotency header. If the institution has no such
mechanism, the limitation must be recorded in the mapper's contract `source`
and operators must not retry after timeout without a status query.

**Why:** POMPO cannot promise exactly-once at a rail that does not support it.
Exactly-once business outcomes still depend on PostgreSQL uniqueness plus
explicit status reconciliation (later).

