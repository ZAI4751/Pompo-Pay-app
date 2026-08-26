---
name: pre-delivery-backend-audit
description: Mandatory six-domain engineering audit before any backend is declared complete. Blocks "finished/done/ready for review" until all gates pass or waivers are explicitly recorded with owner and expiry.
---

# Pre-Delivery Backend Audit

This skill is triggered whenever you are about to tell a user that a backend is finished, done, ready, complete, or safe to ship. You must run a real audit across **all six backend engineering skills** and produce a written report before making that claim.

## Trigger conditions
- User asks if the backend is done/ready/finished.
- You are preparing to say "the backend is complete".
- A PR/release is being proposed as final.

## Mandatory rule
Do not use phrases like "The backend is finished", "It's ready", "This is complete", or equivalent until the audit report shows:
- every required check in all six skills is PASS, or
- failing items have explicit WAIVER with owner, reason, and expiry.

If any item is FAIL and not waived, you must fix it, re-run verification, and update the report. If you cannot verify an item, mark it UNVERIFIED and treat it as FAIL.

## The six skills to audit

Audit all six. If your project has its own six-skill taxonomy, use that, but you must cover all six domains.

| # | Skill | Non-negotiables |
|---|-------|-----------------|
| 1 | Functional Correctness & API Contract | Endpoints match spec; status codes correct; request/response schemas validated; edge cases and error paths handled; happy path and failure path tested. |
| 2 | Security & Access Control | AuthN/Z enforced on every protected route; no secrets in code/logs; input validation and sanitization; rate limiting/abuse controls where needed; dependency vulnerabilities checked. |
| 3 | Performance & Scalability | N+1 queries eliminated; pagination on list endpoints; appropriate indexing; no unbounded queries; load/capacity notes for expected traffic; caching strategy documented if used. |
| 4 | Reliability & Resilience | Idempotency for unsafe operations where needed; retry/backoff on external calls; graceful degradation; transaction boundaries correct; no unhandled promise rejections/panics; backup/restore considered. |
| 5 | Maintainability & Code Quality | Clear module boundaries; consistent error handling; tests cover critical paths; no dead code/TODO markers for release blockers; lint/typecheck/build pass; documentation updated. |
| 6 | Observability & Operations | Structured logs with request IDs; metrics for latency/errors/saturation; health check endpoint; alerts for critical failures; runbook or operational notes exist; config via environment, not hardcoded. |

## Audit procedure

1. Inventory the backend surface: routes, workers, jobs, data stores, external services.
2. For each of the six skills, run actual checks. Do not rely on memory or assumptions.
3. Collect evidence for each check:
   - File paths and line numbers
   - Commands run: tests, lint, build, security scan, load test, query plan
   - Runtime output, logs, or screenshots where relevant
4. Record PASS, FAIL, WAIVER, or UNVERIFIED for each item.
5. Fix any FAIL/UNVERIFIED item, or create a WAIVER with an owner and expiry date. A waiver is only acceptable for non-critical, business-accepted risks.
6. Re-run affected checks after fixes.

## Minimum verification commands

Run at least these, where applicable:

```bash
# Correctness
pytest / npm test / go test ./... / cargo test
# Lint & typecheck
npm run lint && npm run typecheck
# Build
npm run build / go build ./... / cargo build --release
# Security scan
npm audit / pip-audit / cargo audit / trivy fs .
# Dependency vulnerabilities
grep -R "TODO\|FIXME\|XXX" --exclude-dir=node_modules .
# Query plan check if SQL is present
# Load test or at least a documented capacity note

Required output format
Before you claim the backend is finished, output a report exactly like this:

PRE-DELIVERY BACKEND AUDIT
==========================
Date: ...
Backend: ...
Auditor: Claude

1. Functional Correctness & API Contract — PASS/FAIL/WAIVER
   - Evidence: ...
2. Security & Access Control — PASS/FAIL/WAIVER
   - Evidence: ...
3. Performance & Scalability — PASS/FAIL/WAIVER
   - Evidence: ...
4. Reliability & Resilience — PASS/FAIL/WAIVER
   - Evidence: ...
5. Maintainability & Code Quality — PASS/FAIL/WAIVER
   - Evidence: ...
6. Observability & Operations — PASS/FAIL/WAIVER
   - Evidence: ...

Summary:
- PASS: n/6
- FAIL: n
- WAIVER: n
- UNVERIFIED: n

Verdict: READY / NOT READY

Only if verdict is READY may you say the backend is finished. If NOT READY, state what must be fixed and do not imply completion.

text

Need maybe include "UNVERIFIED treated as FAIL" already. Need maybe mention "If user asks 'is backend done?' run this first." Good.

Need ensure frontmatter proper YAML. Name lower-case hyphens. Description enough. Could include "allowed-tools" maybe not needed.

Need maybe include "version" in frontmatter? not necessary but can. Need maybe include "metadata": "version: 1.0.0". Could include. But simple.

Need maybe make it more "skill" like maybe include "When to use" "Instructions". Already.

Need maybe include "six skills" maybe could be "Functional correctness, Security, Performance, Reliability, Maintainability, Observability." That's standard. Good.

Could maybe include "If project uses different six, map them." Good.

Need final answer just code block. Let's produce. Ensure not too overlong? Desired oververbosity 5, but user wants actual document. Could be around 100 lines. Fine.

Need maybe mention "Do not use 'backend is finished' unless report exists." Good.

Let's final with markdown code block.
markdown
---
name: pre-delivery-backend-audit
description: Mandatory six-domain engineering audit before any backend is declared complete. Blocks "finished/done/ready" claims until all gates pass or explicit waivers are recorded.
---

# Pre-Delivery Backend Audit

This skill is triggered whenever you are about to tell a user that a backend is finished, done, ready, complete, or safe to ship. You must run a real audit across **all six backend engineering skills** and produce a written report before making that claim.

## Trigger conditions

- User asks if the backend is done, ready, or finished.
- You are preparing to say "the backend is complete."
- A pull request or release is being proposed as final.

## Mandatory rule

Do not use phrases like "The backend is finished", "It's ready", "This is complete", or equivalent until the audit report shows:

- every required check in all six skills is **PASS**, or
- failing items have an explicit **WAIVER** with owner, reason, and expiry.

If any item is **FAIL** and not waived, you must fix it, re-run verification, and update the report. If you cannot verify an item, mark it **UNVERIFIED** and treat it as **FAIL**.

## The six skills to audit

Audit all six. If your project has its own six-skill taxonomy, use that, but all six domains must be covered.

| # | Skill | Non-negotiables |
|---|-------|-----------------|
| 1 | Functional Correctness & API Contract | Endpoints match spec; status codes correct; request/response schemas validated; edge cases and error paths handled; happy path and failure path tested. |
| 2 | Security & Access Control | AuthN/Z enforced on every protected route; no secrets in code or logs; input validation and sanitization; rate limiting/abuse controls where needed; dependency vulnerabilities checked. |
| 3 | Performance & Scalability | N+1 queries eliminated; pagination on list endpoints; appropriate indexing; no unbounded queries; load/capacity notes for expected traffic; caching strategy documented if used. |
| 4 | Reliability & Resilience | Idempotency for unsafe operations where needed; retry/backoff on external calls; graceful degradation; transaction boundaries correct; no unhandled promise rejections or panics; backup/restore considered. |
| 5 | Maintainability & Code Quality | Clear module boundaries; consistent error handling; tests cover critical paths; no release-blocking dead code or TODO markers; lint/typecheck/build pass; documentation updated. |
| 6 | Observability & Operations | Structured logs with request IDs; metrics for latency, errors, and saturation; health check endpoint; alerts for critical failures; runbook or operational notes exist; config via environment, not hardcoded. |

## Audit procedure

1. Inventory the backend surface: routes, workers, jobs, data stores, external services.
2. For each of the six skills, run actual checks. Do not rely on memory or assumptions.
3. Collect evidence for each check:
   - File paths and line numbers
   - Commands run: tests, lint, build, security scan, load test, query plan
   - Runtime output, logs, or relevant observations
4. Record **PASS**, **FAIL**, **WAIVER**, or **UNVERIFIED** for each item.
5. Fix any **FAIL** or **UNVERIFIED** item, or create a **WAIVER** with an owner and expiry date. A waiver is only acceptable for non-critical, business-accepted risks.
6. Re-run affected checks after fixes.

## Minimum verification commands

Run at least the following where applicable:

```bash
# Correctness
pytest / npm test / go test ./... / cargo test

# Lint and typecheck
npm run lint && npm run typecheck

# Build
npm run build / go build ./... / cargo build --release

# Security scan
npm audit / pip-audit / cargo audit / trivy fs .

# Dead code and release blockers
grep -R "TODO\|FIXME\|XXX" --exclude-dir=node_modules .

# Query plan check if SQL is present
# Load test or at least a documented capacity note
Required output format
Before you claim the backend is finished, output a report exactly like this:

text
PRE-DELIVERY BACKEND AUDIT
==========================
Date: ...
Backend: ...
Auditor: Claude

1. Functional Correctness & API Contract — PASS/FAIL/WAIVER
   - Evidence: ...
2. Security & Access Control — PASS/FAIL/WAIVER
   - Evidence: ...
3. Performance & Scalability — PASS/FAIL/WAIVER
   - Evidence: ...
4. Reliability & Resilience — PASS/FAIL/WAIVER
   - Evidence: ...
5. Maintainability & Code Quality — PASS/FAIL/WAIVER
   - Evidence: ...
6. Observability & Operations — PASS/FAIL/WAIVER
   - Evidence: ...

Summary:
- PASS: n/6
- FAIL: n
- WAIVER: n
- UNVERIFIED: n

Verdict: READY / NOT READY
Only if the verdict is READY may you say the backend is finished. If the verdict is NOT READY, state what must be fixed and do not imply completion.