# POMPO Physical Demonstration Lab — Certification Report

Date: 2026-09-03  
Commit SHA: _stamped after certification commit_  
Prior HEAD: `560a65b`

This report certifies the **demonstration lab and automated path**. It does **not** claim that a human scanned a QR with a phone camera or Google Lens.

---

## 1. What this sprint did (and did not do)

Universal QR, `/p/[publicIdentifier]`, mobile scanner, merchant QR generation, simulated providers, and the standalone APK pipeline already existed. They were **not rebuilt**.

This sprint formalized a safe, reproducible lab:

| Artifact | Role |
| :--- | :--- |
| `pompo-backend/scripts/demo_lab.py` | Shared identities + production confirm gate |
| `pompo-backend/scripts/seed_demo_environment.py` | Idempotent real DB records (merchant/branch/till/users/instruments/QRs) |
| `pompo-backend/scripts/reset_demo_environment.py` | Developer-only reset of **demo merchant QRs**, then re-seed |
| `pompo-backend/scripts/verify_demo_lab.py` | Developer API verification (not used during the live demo) |
| `pompo-backend/tests/test_demo_lab_safety.py` | Production seed/reset refused without token |
| `DEMO-TESTING-GUIDE.md` | Operator procedure (no terminal commands during the demo) |
| `RELEASE-CHECKLIST.md` | Machine-readable PASS/FAIL/UNVERIFIED/WAIVER |

Reset is **not** exposed to customers, merchants, or the mobile UI. It refuses `APP_ENV=production` unless `POMPO_ALLOW_DEMO_SEED=I_UNDERSTAND_THIS_IS_DEMO_DATA`.

---

## 2. Demo / test environment

| Item | Value |
| :--- | :--- |
| Lab target | Local Docker backend (`APP_ENV=development`) |
| API | `http://localhost:8000/api/v1` |
| Production API (APK) | `https://pompo-api-production.up.railway.app/api/v1` |
| Public checkout host (QR URL) | `https://pay.pompo.mw/p/{publicIdentifier}` |
| Local Alembic | `0020_account_security` (head) |
| Local `/health` | `healthy` (application, database, redis, celery) |
| Production `/health/live` | `{"alive":true}` |
| Production `/health/ready` | `ready=true`, database + redis true |

Production Railway was **not** seeded with demo identities this sprint (explicit confirm token required; demo passwords must not be mixed into production without an operator decision).

---

## 3. Test accounts — capability model

Lab passwords live in `DEMO-TESTING-GUIDE.md` and can be overridden with `POMPO_DEMO_*_PASSWORD`. They are demonstration identities, not staff credentials. Do not treat them as production secrets to rotate into real user accounts.

| Identity | Login | Role | What it can do | What it cannot do |
| :--- | :--- | :--- | :--- | :--- |
| Test platform admin | `demo.admin@pompo.mw` | `platform_admin` | Master Admin, payment lookup by reference | Merchant Mode (`organization/my-access.allowed=false`), `merchant_id=None` |
| Test merchant | `demo.merchant@pompo.mw` | `merchant_owner` | Authorized Demo Merchant / Branch / Till; generate QR | Other merchants; platform-admin tools |
| Test customer | `demo.customer@pompo.mw` | `customer` (verified) | Login, Customer Home, pay from a valid QR with sandbox instruments | Create merchant QR, merchant ledger, settlements, foreign branch/till |

`platform_admin` is **not** automatically a merchant. Customer-first login still lands on Customer Home; Merchant Mode is backend-gated.

---

## 4. Demo merchant (real database rows)

| Record | Name / code |
| :--- | :--- |
| Merchant | POMPO Demo Merchant (`DEMO-REG-001`) |
| Branch | POMPO Demo Branch (Lilongwe City Centre) |
| Till | POMPO Demo Till (`DEMO-TILL-01`) |

These are SQLAlchemy-persisted rows, not frontend fixtures.

After `reset_demo_environment.py` the seeder issues one active **static** QR and one **dynamic** QR (MWK 2500.00). Public identifiers change on each reset. Use whatever the merchant screen or seeder printout shows. Do not reuse IDs from an old document.

---

## 5. Simulated provider scenarios

Existing adapters in `app/payments/adapters.py` / catalog (`environment=sandbox`):

| Provider code | Deterministic outcome |
| :--- | :--- |
| `simulated` | SUCCESS |
| `simulated_failure` | FAILED / REJECTED |
| `simulated_pending` | PROCESSING / PENDING |
| `simulated_timeout` | TIMEOUT → FAILED or retryable PROCESSING |

Airtel Money, TNM Mpamba, and Standard Bank catalog rows are `is_active=False`. National Bank is labeled “live contract not implemented”. NBS and First Capital are **not** live catalog rails. No production provider credentials were activated.

---

## 6. Exact physical test procedure

Follow `DEMO-TESTING-GUIDE.md`. Summary for the operator (no terminal):

1. **Merchant** — APK login as demo merchant → Profile → Merchant Mode → QR → display the plate (same URL the camera will open).
2. **Customer with app** — APK login as demo customer → Scan → confirm merchant/branch/till → amount/method → pay → terminal result from the API.
3. **Customer without app** — **same QR** → Android Camera or Google Lens → `https://pay.pompo.mw/p/...` → browser checkout → pay.
4. **Merchant** — Activity shows the same reference.
5. **Master Admin** — look up that reference (admin list endpoint is merchant-scoped; use `GET /payments/{reference}` / Admin transaction lookup).

Developer-only (not during the demo):

```text
docker compose exec backend python scripts/reset_demo_environment.py
docker compose exec backend python scripts/verify_demo_lab.py
```

---

## 7. Results by classification

### AUTOMATED TEST

| Check | Result | Evidence |
| :--- | :--- | :--- |
| Demo lab API path (health, 3 logins, isolation, QR, SUCCESS, FAILED, admin visibility, invalid QR) | **PASS** | `scripts/verify_demo_lab.py` → `DEMO LAB API VERIFICATION: PASS` |
| Demo lab production gate | **PASS** | `tests/test_demo_lab_safety.py` |
| Demo + account security | **PASS** | 15 passed (`test_demo_lab_safety`, `test_demo_environment_security`, `test_account_security_and_authorization`) |
| Webhooks + settlement/reconciliation + universal QR | **PASS** | 39 passed |
| Mobile TypeScript | **PASS** | `npx tsc --noEmit` |
| Mobile ESLint | **PASS** | `npx eslint .` |
| Mobile Jest | **PASS** | 16 suites, 55 tests |
| Frontend TypeScript / ESLint / `next build` | **PASS** | includes `ƒ /p/[publicIdentifier]` |
| Signed APK assemble | **PASS** | see §9 |
| Full backend pytest (~301) | **NOT RUN** | Explicitly skipped as unrelated expense |

### BROWSER TEST

| Device | Action | Result |
| :--- | :--- | :--- |
| — | Open `/p/{id}` and complete checkout in a real browser | **NOT PERFORMED** this session |
| — | Master Admin click-through (dashboard, QR, transactions) | **NOT PERFORMED** this session |
| — | Responsive viewport pass | **NOT PERFORMED** |

API-side equivalents (QR inspect, payment, admin lookup) passed. That is not a browser test.

Known host gap: a QR that exists only on **local** Postgres will 404 on production `pay.pompo.mw` until that identifier exists on the API the checkout host calls.

### PHYSICAL DEVICE TEST

| Device | Action | Result | Failure |
| :--- | :--- | :--- | :--- |
| Android phone | Install `POMPO-1.0.0.apk` over existing build | **NOT PERFORMED** | No device attached |
| Android phone | App launch / login | **NOT PERFORMED** | No device attached |
| Android phone | Merchant Mode → generate QR | **NOT PERFORMED** | No device attached |
| Android phone | Customer Scan → pay | **NOT PERFORMED** | No device attached |
| Android native camera | Scan same HTTPS QR | **NOT PERFORMED** | No hardware scan |
| Google Lens | Scan same HTTPS QR | **NOT PERFORMED** | No hardware scan |

Do not treat the APK **build** as an install/launch/login proof.

---

## 8. Security verification (automated)

Customer JWT cannot:

- create merchant QR (403)
- read merchant ledger (403)
- read settlements (403)
- select a foreign merchant / branch / till (security tests)

Merchant JWT can only generate QR for its authorized branch/till.

Public QR inspect cannot change merchant, override a locked dynamic amount, or bypass expiry/revocation.

Platform admin is not granted merchant membership.

---

## 9. Android release artifact

| Field | Value |
| :--- | :--- |
| Path | `pompo-mobile/release/POMPO-1.0.0.apk` (gitignored binary) |
| Package | `mw.pompo.mobile` |
| Version | `1.0.0` |
| API | `https://pompo-api-production.up.railway.app/api/v1` |
| Transport | HTTPS only (assembler rejects localhost) |
| Build | `assembleRelease` BUILD SUCCESSFUL, signed with local upload keystore (not committed) |
| SHA-256 | `b75839a0caf465324051425b26e4955004fc0d0c2e15da325f8c094c358b42c3` |

Installation, launch, and login on a phone are **UNVERIFIED**.

---

## 10. Deployment status

| Surface | Status |
| :--- | :--- |
| Local Docker backend | Live, healthy, migrations at head, demo lab seeded + API-verified |
| Production API (Railway) | Live + ready. Demo identities **not certified** as present |
| Public checkout (`pay.pompo.mw`) | Host/route exist in the frontend build; **not** proven against a production-seeded demo QR |
| Master Admin (Vercel / local Next) | Production build compiles; UI click-through UNVERIFIED |
| Standalone APK | Rebuilt and hashed; talks to **production** API |

---

## 11. Remaining blockers

1. **Physical device loop** — install, merchant QR, customer scan, camera, Google Lens, merchant Activity, Admin UI. Required for the human success condition.
2. **Production demo seed** — the release APK cannot log into local Docker. A physical APK demo needs production identities seeded **only** with `POMPO_ALLOW_DEMO_SEED=I_UNDERSTAND_THIS_IS_DEMO_DATA` after confirming migration `0020_account_security` is applied on Railway.
3. **Same-QR zero-install on production** — checkout host must resolve the identifier the merchant QR actually issued (local IDs are not production IDs).
4. **Full pytest suite** — not re-run; targeted suites only.
5. **Admin UI / responsive web** — routes compiled; no browser session this sprint.

---

## 12. Final success condition

A human operator **can** run the demonstration **after**:

- local lab is reset (already possible), **or** production is explicitly seeded, and
- they follow `DEMO-TESTING-GUIDE.md` on a phone + browser + Master Admin.

What this session proved:

- Real backend identities and authorization boundaries
- Simulated SUCCESS/FAILED (and PENDING/TIMEOUT in tests)
- One payment reference visible to customer, merchant, and platform admin **via the API**
- Signed production-URL APK built
- Release checklist filled with honest UNVERIFIED physical/browser rows

What this session **did not** prove:

- Native camera scan
- Google Lens scan
- APK install / launch / login on hardware
- Browser checkout click-through
- Production-seeded demo accounts
