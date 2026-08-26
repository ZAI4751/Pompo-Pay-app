# POMPO Engineering State

## CURRENT MILESTONE
M007: payment provider integration and adapter architecture (IMPLEMENTED; final verification pending).

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

## KNOWN ISSUES
Role ownership is global because the existing schema has no role merchant ID.
Mypy reports baseline errors in shared pre-M004 modules and third-party
packages without stubs.

## KNOWN TEST LIMITATIONS
Docker-backed tests are the acceptance environment. Host execution may require
matching PostgreSQL credentials, database selection, Redis, and allowed-host
configuration.

## IMPORTANT ARCHITECTURAL DECISIONS
Permissions are immutable catalog contracts. No wildcard permissions or
multi-role user table was introduced. RBAC mutation policy is enforced in the
service layer and recorded through the existing AuditLog model.

## NEXT MILESTONE
M008 is intentionally not started.
