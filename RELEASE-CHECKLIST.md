# POMPO Release Checklist

Machine-readable status uses `PASS | FAIL | UNVERIFIED | WAIVER`.
Fill the **Evidence** column with the command, URL, or test name that produced the result.

Last updated: 2026-09-03  
Commit: see `PHYSICAL-DEMO-REPORT.md` (stamped after certification commit)

Classification:

- **AUTOMATED** — executed this session
- **BROWSER** — requires a real browser click-through
- **PHYSICAL** — requires an Android device / camera / Google Lens

---

## BACKEND

| ID | Check | Status | Evidence |
| :--- | :--- | :--- | :--- |
| B-01 | `/api/v1/health` healthy | PASS | Local `GET http://localhost:8000/api/v1/health` → `status=healthy`; components application/database/redis/celery healthy |
| B-02 | `/api/v1/health/live` 200 | PASS | Local + production `{"alive":true}` |
| B-03 | `/api/v1/health/ready` 200 (database + redis) | PASS | Local via `scripts/verify_demo_lab.py` ready 200; production `{"ready":true,"checks":{"database":true,"redis":true}}` |
| B-04 | Alembic migrations at head | PASS | Local Docker `alembic current` → `0020_account_security (head)` |
| B-05 | Authentication (login / refresh / logout / me) | PASS | `verify_demo_lab.py` login + `/auth/me` for admin/merchant/customer |
| B-06 | Authorization (customer vs merchant vs admin) | PASS | `verify_demo_lab.py` + `tests/test_demo_environment_security.py` + `tests/test_account_security_and_authorization.py` (15 passed) |
| B-07 | QR create / inspect / revoke | PASS | Merchant static QR 201; public inspect; reset script revokes demo-merchant QRs; `tests/test_universal_qr.py` |
| B-08 | Payment from QR + process | PASS | `verify_demo_lab.py` pay-from-qr 201 → process SUCCESS; same reference on customer/merchant/admin |
| B-09 | Simulated SUCCESS / FAILED / PENDING / TIMEOUT | PASS | SUCCESS + FAILED in `verify_demo_lab.py`; PENDING/TIMEOUT in `tests/test_demo_environment_security.py` |
| B-10 | Webhooks (simulated) | PASS | `tests/test_webhooks.py` (part of 39 passed with settlement + universal QR) |
| B-11 | Settlement / reconciliation (simulated ingest) | PASS | `tests/test_settlement.py` |
| B-12 | pytest suite | WAIVER | Targeted suites this sprint: 15 + 39 passed. Full backend suite (~301) not re-run (out of scope per “do not rerun expensive unrelated suites”) |

## MOBILE

| ID | Check | Status | Evidence |
| :--- | :--- | :--- | :--- |
| M-01 | Authentication / customer-first login | PASS | Automated: mobile Jest + backend `defaultMode=customer`. Physical login: UNVERIFIED (see H-01) |
| M-02 | Universal QR scan + inspect | PASS | `__tests__/qrPayload.test.ts` + `tests/test_universal_qr.py`. Device scanner: UNVERIFIED (H-02) |
| M-03 | Customer Home + checkout | PASS | Jest payment-screen coverage. Device checkout: UNVERIFIED |
| M-04 | Merchant Mode (backend-gated) + QR generate | PASS | `GET /organization/my-access` merchant `allowed=true`, `can_generate_qr=true`; admin/customer `allowed=false` |
| M-05 | Profile / security / support (real endpoints) | PASS | Existing mobile tests/routes; no new endpoints this sprint |
| M-06 | Payment result from backend state | PASS | `verify_demo_lab.py` process status `success`/`failed` from API, not client mock |
| M-07 | Understandable error states | PASS | Invalid QR 404; failed simulated payment; see DEMO-TESTING-GUIDE §5. Device copy: UNVERIFIED |
| M-08 | TypeScript `tsc --noEmit` | PASS | `pompo-mobile` `npx tsc --noEmit` exit 0 |
| M-09 | ESLint | PASS | `pompo-mobile` `npx eslint .` exit 0 |
| M-10 | Jest | PASS | 16 suites, 55 tests passed (act() warnings on MerchantHome; not failures) |
| M-11 | Standalone signed APK `mw.pompo.mobile` | PASS | `node ./scripts/assemble-android-apk.js` BUILD SUCCESSFUL; package `mw.pompo.mobile` version `1.0.0` |
| M-12 | Production HTTPS API only (no localhost) | PASS | Assembler printed `api=https://pompo-api-production.up.railway.app/api/v1`; script rejects localhost |

## WEB (public checkout)

| ID | Check | Status | Evidence |
| :--- | :--- | :--- | :--- |
| W-01 | Public route `/p/[publicIdentifier]` | PASS | `next build` emits `ƒ /p/[publicIdentifier]`. Browser payment against a live QR: UNVERIFIED |
| W-02 | QR resolution + merchant identity + amount | PASS | API `GET /qr/{id}` returns POMPO Demo Merchant. Browser render: UNVERIFIED |
| W-03 | Auth (login/register) then payment initiation | PASS | API path in `verify_demo_lab.py`. Browser inline auth: UNVERIFIED |
| W-04 | Processing / terminal states / receipt | PASS | Checkout phases exist in `src/app/p/[publicIdentifier]/page.tsx`. Browser: UNVERIFIED |
| W-05 | Error states (invalid / expired / revoked) | PASS | Page phases `not_found` / `expired` / `revoked`; API invalid QR 404. Browser: UNVERIFIED |
| W-06 | Responsive layout | UNVERIFIED | No viewport browser pass this session |
| W-07 | No `NEXT_PUBLIC_USE_MOCKS` in production | PASS | `src/lib/api/config.ts` throws if mocks enabled on Vercel production |
| W-08 | Typecheck + lint + production build | PASS | `npm run typecheck` + `lint` + `build` exit 0 (Next.js 16.3.3, 32 pages) |

## ADMIN

| ID | Check | Status | Evidence |
| :--- | :--- | :--- | :--- |
| A-01 | Authentication against live API | PASS | `verify_demo_lab.py` admin login + `/auth/me` role `platform_admin`, `merchant_id=None` |
| A-02 | Dashboard | UNVERIFIED | Route `/dashboard` compiled; no browser click-through |
| A-03 | Merchants / branches / tills | UNVERIFIED | Routes compiled (`/merchants`, `/branches`, `/tills`) |
| A-04 | QR codes | UNVERIFIED | Route `/qr-codes` compiled |
| A-05 | Transaction lookup by reference | PASS | Admin `GET /api/v1/payments/{reference}` 200 in `verify_demo_lab.py`. Admin UI page: UNVERIFIED |
| A-06 | Providers (simulated labeled; live rails not operational) | PASS | Catalog: simulated `environment=sandbox`; Airtel/TNM/Standard Bank `is_active=False`; banks labeled “live contract not implemented” |
| A-07 | Settlement | PASS | `tests/test_settlement.py`. Admin UI `/settlements`: UNVERIFIED |
| A-08 | Reconciliation | PASS | Settlement reconciliation tests. Admin UI `/reconciliation`: UNVERIFIED |
| A-09 | Settings | UNVERIFIED | Routes `/settings`, `/settings/[category]` compiled |
| A-10 | Audit / health | UNVERIFIED | Routes `/audit-logs`, `/system/health` compiled; API health PASS (B-01–B-03) |

## SECURITY

| ID | Check | Status | Evidence |
| :--- | :--- | :--- | :--- |
| S-01 | Customer cannot create merchant QR | PASS | `verify_demo_lab.py` POST `/qr/static` → 403 |
| S-02 | Customer cannot read merchant ledger | PASS | GET `/payments` → 403 |
| S-03 | Customer cannot read settlements | PASS | GET `/settlements/summary` → 403 |
| S-04 | Merchant cannot use foreign merchant/branch/till | PASS | `tests/test_demo_environment_security.py` |
| S-05 | Public QR cannot change merchant or dynamic amount | PASS | `tests/test_demo_environment_security.py` |
| S-06 | Expired / revoked QR rejected | PASS | `tests/test_universal_qr.py` expired/revoked cases |
| S-07 | Demo seed/reset refused in production without confirm token | PASS | `tests/test_demo_lab_safety.py` |

## REAL PROVIDER BOUNDARY

| ID | Check | Status | Evidence |
| :--- | :--- | :--- | :--- |
| P-01 | Airtel / TNM / Standard Bank / NBS / National Bank / First Capital **not** presented as live | PASS | `app/payments/catalog.py`: Airtel/TNM/Standard Bank `is_active=False`; National Bank labeled not implemented; NBS/First Capital have no live catalog rail |
| P-02 | Simulated adapters labeled sandbox/test | PASS | Display names “Simulated sandbox/pending/failure”; `environment="sandbox"`; `is_simulated=True` |

## PHYSICAL / BROWSER (must not be claimed without hardware)

| ID | Check | Status | Evidence |
| :--- | :--- | :--- | :--- |
| H-01 | Merchant APK: login → Merchant Mode → generate QR | UNVERIFIED | No Android device attached this session |
| H-02 | Customer APK: scan same QR → pay | UNVERIFIED | No Android device attached this session |
| H-03 | Native camera / Google Lens → HTTPS URL → browser checkout | UNVERIFIED | No hardware camera / Lens pass |
| H-04 | Merchant sees payment | UNVERIFIED | API merchant ledger PASS; APK Activity screen not opened |
| H-05 | Master Admin sees payment | UNVERIFIED | API admin lookup PASS; Admin UI not opened in a browser |
