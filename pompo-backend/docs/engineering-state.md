# POMPO Engineering State

## CURRENT MILESTONE
Operational payment chain (Merchant → Branch → Till → Provider catalog →
Payment) is implemented. This is not M008 live rails.

M007 remains the last numbered provider-adapter milestone. This slice adds
till administration, a database-backed sandbox provider catalog, idempotent
non-production seeding, provider admin visibility, and Master Admin wiring
to those live APIs.

## COMPLETED MILESTONES
M001 backend foundation; M002 domain model and database; M003 authentication;
M004 Phase 1 RBAC foundation; M004 Phase 2 authorization engine.
M005 merchant and branch administration vertical slice.
M006 payment core; live migration and Docker acceptance verified.
M007 provider contracts, registry, mock adapters, and payment integration implemented.
Operational till management, provider catalog, and admin integration (this slice).
Docker-backed pytest: 112 passed. Frontend typecheck, lint, and build passed.

## CURRENT ARCHITECTURE
FastAPI routes use dependencies, services, repositories, and async SQLAlchemy.
Authentication resolves identity; authorization resolves catalog permissions.
RBAC administration is under `/api/v1/rbac`; organization administration is under
`/api/v1/organization` (merchants, branches, tills). Payment APIs remain under
`/api/v1/payments`. Provider catalog rows live in `payment_providers`; the
in-process registry currently exposes only the `simulated` sandbox adapter.

## DATABASE STATE
PostgreSQL migration graph head is `0007_operational_tills_providers` (parent
`0006_m007_attempt_metadata`).
`0007` adds provider catalog columns (`environment`, `priority`,
`supported_currencies`, `supported_payment_methods`, `capabilities`) and
inserts `tills:*` / `providers:*` permissions plus role grants. It does not
seed provider rows (that is environment-gated and must not run in production).

## TILL ARCHITECTURE
Tills belong to a branch (and therefore a merchant). Codes are unique per
branch (`uq_till_branch_code`) and are not reassigned after creation.
Soft-delete plus `is_active=False` deactivates a till; historical payments
keep the till foreign key (`ON DELETE RESTRICT` on transactions).

Permissions are dedicated, not reused from branches:

- `tills:read` / `tills:create` / `tills:update` / `tills:delete`

HTTP:

- `GET/POST /organization/branches/{branch_id}/tills`
- `GET/PATCH/DELETE /organization/tills/{till_id}`

Platform administrators may cross tenants. Merchant owners with `branch_id`
unset may manage all tills for their merchant. Branch-assigned users are
limited to their branch. Cross-merchant and cross-branch assignment is
rejected.

## PROVIDER CATALOG ARCHITECTURE
`ProviderCode` enum values, catalog definitions in `app/payments/catalog.py`,
and `payment_providers.code` are the same identifiers. The default
`ProviderRegistry` registers only `simulated`. Placeholder rows for Airtel,
TNM, and banks exist as inactive simulated sandbox metadata and cannot be
enabled until an adapter is registered.

`GET /payments/providers` reads the database catalog (requires `providers:read`
or `transactions:read`). `PATCH /payments/providers/{code}` allows platform
administrators with `providers:update` to change `is_active` and `priority`
only. Secrets are not stored on provider rows and are not returned.

Development seed: `docker compose exec backend python scripts/seed_providers.py`.
It is idempotent, secret-free, and refuses `APP_ENV=production`.

## USER ADMINISTRATION
Deferred. A platform administrator (or any actor with `transactions:create`
in the correct merchant/branch/till scope) can exercise the payment chain.
There is still no user-directory CRUD API. Role assignment remains
`PUT /rbac/users/{user_id}/role` for a known user id.

## PAYMENT API COMPLETENESS
Usable by future POS/mobile clients for create, get-by-reference, cancel, and
process against the simulated adapter once merchant, branch, till, and an
active catalog provider exist.

Deferred: payment/transaction list and search, refunds, QR engine, webhooks,
settlement, reconciliation, live Airtel/TNM/bank adapters, attempt-list as a
standalone resource (attempts already embed on the payment response).

`QR_GENERATED` and `PENDING_USER_PIN` remain enum values for a future QR/PIN
checkout. They are not in `TRANSITIONS` and cannot be applied.

## FRONTEND INTEGRATION STATE
The admin frontend (`pompo-frontend`, Next.js) is a live control plane for
every capability the backend already exposes:

REAL API INTEGRATED: authentication (`/auth/login`, `/refresh`, `/logout`,
`/me`); RBAC roles/permissions/grants; merchant, branch, and till CRUD
(soft-delete); payment get-by-reference plus cancel/process; provider catalog
list/detail/enable-disable; health/readiness/liveness.

Effective permissions are loaded from `GET /rbac/roles/{role_id}`
(`permission_codes`). `/auth/me` still does not return permission codes.

MOCK / NOT YET AVAILABLE: user directory, payment/transaction list,
webhooks, audit logs, API keys, reports, QR, live Airtel/TNM/bank adapters.
Dashboard volume charts remain labeled illustrative series.

`NEXT_PUBLIC_USE_MOCKS=true` is opt-in demo mode. The default is live API.
Local Master Admin sign-in uses a seeded platform administrator; the frontend
does not contain credentials. Simulated providers are labeled as simulated.

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
Provider catalog identifiers must match `ProviderCode`. Mock adapters are not
live rails. Sandbox provider seeding must never run in production.

## NEXT MILESTONE
M008 is intentionally not started.

The next genuinely unimplemented capability is live payment provider
integration: the `ProviderAdapter` protocol, registry and normalized
request/outcome/capability types exist, but every registered adapter is a
deterministic sandbox mock (`app/payments/adapters.py`). No Airtel Money, TNM
Mpamba or bank adapter exists, and `app/providers/__init__.py` is still a stub.
`ProviderAdapter.get_payment_status`, `cancel_payment` and `refund_payment` are
declared but not yet called by `PaymentService` (only `initiate_payment` is).

Also outstanding, for whoever picks up the next slice:
- `transactions:refund` permission exists with no refund route or service method.
- `PaymentService.create_attempt()` and the `PaymentTransition` schema have no
  HTTP endpoint.
- `/auth/me` still omits effective permission codes; the admin loads them from
  `GET /rbac/roles/{role_id}` instead.
- There is no user-directory API and no payment list/search API.
