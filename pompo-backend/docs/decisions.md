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
