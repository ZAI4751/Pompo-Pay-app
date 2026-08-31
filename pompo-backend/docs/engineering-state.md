# POMPO Engineering State

## CURRENT MILESTONE
M007: payment provider integration and adapter architecture (IMPLEMENTED and
VERIFIED). Full suite green in the Docker-backed environment: 84 passed.
Migration head applied with no Alembic drift.

Admin frontend to backend integration is established and verified end-to-end.

## COMPLETED MILESTONES
M001 backend foundation; M002 domain model and database; M003 authentication;
M004 Phase 1 RBAC foundation; M004 Phase 2 authorization engine.
M005 merchant and branch administration vertical slice.
M006 payment core; live migration and Docker acceptance verified.
M007 provider contracts, registry, mock adapters, and payment integration implemented.

## CURRENT ARCHITECTURE
FastAPI routes use dependencies, services, repositories, and async SQLAlchemy.
Authentication resolves identity; authorization resolves catalog permissions.
RBAC administration is under `/api/v1/rbac`; organization administration is under
`/api/v1/organization`.

## DATABASE STATE
PostgreSQL migration graph head is `0006_m007_attempt_metadata` (parent
`0005_m006_payment_core`).
Live database is at the migration head and Alembic reports no drift.

## M005 IMPLEMENTATION
Merchant and branch CRUD is persisted through repositories and services. Platform
administrators may cross tenant boundaries; merchant users are restricted to
their merchant, and branch-assigned users are restricted to their branch.
Normal reads exclude inactive and soft-deleted resources. Mutations create
organization audit records. The migration installs the new organization
permissions idempotently, while `scripts/seed_rbac.py` remains the full catalog
bootstrap path.

Payment creation, merchant-scoped idempotency, controlled transaction
transitions, payment attempts, provider-neutral contracts, cancellation, and
payment APIs are implemented and verified.

Provider adapters use normalized requests, outcomes, capabilities, and
retryable errors. Provider metadata is persisted on attempts; live Airtel,
TNM, and bank integrations are intentionally deferred.

## AUTHENTICATION STATE
JWT access tokens, rotated server-backed refresh sessions, replay detection,
logout, and active-user checks are implemented.

## AUTHORIZATION STATE
Exact permission checks, 401/403 semantics, inactive/soft-deleted user and
inactive-role protection, custom delegation limits, protected system roles,
tenant-scope primitives, RBAC administration, and audit records are implemented.
The system retains one role per user; role removal is rejected because the
current schema requires a role.

## FRONTEND INTEGRATION STATE
The admin frontend (`pompo-frontend`, Next.js) authenticates against the real
backend: `POST /api/v1/auth/login` then `GET /api/v1/auth/me`. Every other
admin screen still reads from `src/mocks` and is not yet wired to the live
RBAC/organization endpoints, which do exist.

CORS is the outermost middleware so rate-limit (429), trusted-host (400) and
unhandled-error (500) responses remain readable by the browser; previously they
carried no CORS headers and the UI reported them all as an unreachable backend.
The frontend API client now distinguishes network failure from each HTTP status
and preserves the backend `request_id`. See docs/decisions.md, "Admin frontend
integration: cross-origin error surfacing".

## KNOWN ISSUES
Role ownership is global because the existing schema has no role merchant ID.
Mypy reports baseline errors in shared pre-M004 modules and third-party
packages without stubs.
Ruff reports 50 baseline errors and 15 files needing reformatting, all in
pre-existing modules (models, auth service, older tests, migrations); no
newly-touched file is affected.

## KNOWN TEST LIMITATIONS
Docker-backed tests are the acceptance environment; run them in-container per
docs/testing.md Option A. The backend container bind-mounts `app/`, `tests/`
and `migrations/`, so in-container runs reflect the working tree rather than
the image build.

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

## NEXT MILESTONE
M008 is intentionally not started.

The next genuinely unimplemented capability is live payment provider
integration: the `ProviderAdapter` protocol, registry and normalized
request/outcome/capability types exist, but every registered adapter is a
deterministic sandbox mock (`app/payments/adapters.py`). No Airtel Money, TNM
Mpamba or bank adapter exists, and `app/providers/__init__.py` is still a stub.
`ProviderAdapter.get_payment_status`, `cancel_payment` and `refund_payment` are
declared but not yet called by `PaymentService` (only `initiate_payment` is).

Also outstanding within completed milestones, for whoever picks up M008:
- `transactions:refund` permission exists with no refund route or service method.
- `PaymentService.create_attempt()` and the `PaymentTransition` schema have no
  HTTP endpoint.
- Till administration has no API (the model exists from M002).
- `TransactionStatus.QR_GENERATED` and `PENDING_USER_PIN` are defined but absent
  from the state machine transition map.
- Admin frontend screens other than login still use mock data.
