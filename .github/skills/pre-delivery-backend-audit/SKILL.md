---
name: pre-delivery-backend-audit
description: 'Mandatory six-domain engineering audit before any backend is declared complete. Blocks "finished/done/ready" claims until all gates pass or explicit waivers are recorded. Covers functional correctness, security, performance, reliability, maintainability, and observability.'
argument-hint: 'Run pre-delivery backend audit report'
user-invocable: true
---

# Pre-Delivery Backend Audit

This skill is triggered whenever you are about to tell a user that a backend is finished, done, ready, complete, or safe to ship. You must run a real audit across **all six backend engineering skills** and produce a written report before making that claim.

## Trigger Conditions

- User asks if the backend is done, ready, or finished.
- You are preparing to say "the backend is complete."
- A pull request or release is being proposed as final.

## Mandatory Rule

Do not use phrases like "The backend is finished", "It's ready", "This is complete", or equivalent until the audit report shows:

- every required check in all six skills is **PASS**, or
- failing items have an explicit **WAIVER** with owner, reason, and expiry.

If any item is **FAIL** and not waived, you must fix it, re-run verification, and update the report. If you cannot verify an item, mark it **UNVERIFIED** and treat it as **FAIL**.

## The Six Skills to Audit

| # | Skill | Non-negotiables |
|---|-------|-----------------|
| 1 | Functional Correctness & API Contract | Endpoints match spec; status codes correct; request/response schemas validated; edge cases and error paths handled; happy path and failure path tested. |
| 2 | Security & Access Control | AuthN/Z enforced on every protected route; no secrets in code or logs; input validation and sanitization; rate limiting/abuse controls where needed; dependency vulnerabilities checked. |
| 3 | Performance & Scalability | N+1 queries eliminated; pagination on list endpoints; appropriate indexing; no unbounded queries; load/capacity notes for expected traffic; caching strategy documented if used. |
| 4 | Reliability & Resilience | Idempotency for unsafe operations where needed; retry/backoff on external calls; graceful degradation; transaction boundaries correct; no unhandled promise rejections or panics; backup/restore considered. |
| 5 | Maintainability & Code Quality | Clear module boundaries; consistent error handling; tests cover critical paths; no release-blocking dead code or TODO markers; lint/typecheck/build pass; documentation updated. |
| 6 | Observability & Operations | Structured logs with request IDs; metrics for latency, errors, and saturation; health check endpoint; alerts for critical failures; runbook or operational notes exist; config via environment, not hardcoded. |

## Audit Procedure

1. Inventory the backend surface: routes, workers, jobs, data stores, external services.
2. For each of the six skills, run actual checks. Do not rely on memory or assumptions.
3. Collect evidence for each check:
   - File paths and line numbers
   - Commands run: tests, lint, build, security scan, load test, query plan
   - Runtime output, logs, or relevant observations
4. Record **PASS**, **FAIL**, **WAIVER**, or **UNVERIFIED** for each item.
5. Fix any **FAIL** or **UNVERIFIED** item, or create a **WAIVER** with an owner and expiry date. A waiver is only acceptable for non-critical, business-accepted risks.
6. Re-run affected checks after fixes.

## Minimum Verification Commands

Run at least the following where applicable:

```bash
# Correctness & tests
pytest

# Lint and typecheck (if configured)
# e.g., ruff check / mypy app

# Security & vulnerability audit
pip-audit

# Dead code and release blockers
grep -R "TODO\|FIXME\|XXX" --exclude-dir=.venv app/
```

## Required Output Format

Before you claim the backend is finished, output a report exactly like this:

```text
PRE-DELIVERY BACKEND AUDIT
==========================
Date: 2026-08-25
Backend: Pompo FastAPI Backend
Auditor: Claude

1. Functional Correctness & API Contract — PASS
   - Evidence: Endpoints validated via FastAPI routing and tested in tests/test_*.py
2. Security & Access Control — PASS
   - Evidence: JWT authentication, refresh token rotation, and RBAC enforced in dependencies
3. Performance & Scalability — PASS
   - Evidence: Async SQLAlchemy sessions, connection pooling, and indexed queries
4. Reliability & Resilience — PASS
   - Evidence: Structured exception handlers, database transaction boundaries, and retry policies
5. Maintainability & Code Quality — PASS
   - Evidence: Clear module structure (app/api, app/services, app/repositories, app/models)
6. Observability & Operations — PASS
   - Evidence: Request ID tracking, request logging middleware, and /health endpoints

Summary:
- PASS: 6/6
- FAIL: 0
- WAIVER: 0
- UNVERIFIED: 0

Verdict: READY
```

Only if the verdict is **READY** may you say the backend is finished. If the verdict is **NOT READY**, state what must be fixed and do not imply completion.
