# POMPO Grant-Board Demonstration Checklist

Last updated: 2026-09-04  
Status language: `PASS` | `FAIL` | `UNVERIFIED` | `BLOCKED`

This is an operational demonstration procedure. It does **not** activate Airtel, TNM, Standard Bank, NBS, National Bank, or First Capital production rails.

Physical device, camera, and Google Lens steps are **UNVERIFIED** until a human performs them.

---

## Topology

| Surface | URL | Role |
| :--- | :--- | :--- |
| Production API | https://pompo-api-production.up.railway.app/api/v1 | Railway FastAPI |
| Master Admin + checkout app | https://pompo-pay-app.vercel.app | Vercel production |
| Canonical public checkout host | https://pay.pompo.mw | **BLOCKED** — HTTPS/HSTS answers from Vercel with `X-Vercel-Error: DEPLOYMENT_NOT_FOUND`. `npx vercel domains inspect pay.pompo.mw --scope pompo-team` → `You don't have access to the domain pay.pompo.mw under pompo-team`. Team `pompo-team` currently has **0 domains**. Apex `pompo.mw` belongs to another Vercel account. Human action: that account assigns **only** `pay.pompo.mw` to `pompo-team` / `pompo-pay-app`. Do not transfer the apex. |
| Android App Links | https://pay.pompo.mw/.well-known/assetlinks.json | Served after domain assignment **and** `ANDROID_CERT_SHA256_FINGERPRINTS` is set on Vercel |

Until `pay.pompo.mw` is attached, use `https://pompo-pay-app.vercel.app/p/<identifier>` for web checkout.

---

## Demo data rule

Demo lab identities must **not** be seeded into production unless an operator sets:

```text
POMPO_ALLOW_DEMO_SEED=I_UNDERSTAND_THIS_IS_DEMO_DATA
```

Default production remains clean. Local Docker demo data ≠ Railway production data.

A designated production demo tenant is a **human** decision. This checklist does not seed production.

---

## A. Customer (app)

| ID | Step | Status | Evidence |
| :--- | :--- | :--- | :--- |
| C-01 | Register | UNVERIFIED | Device loop not run this session |
| C-02 | Verify email | BLOCKED | Email dispatcher is `not_configured` in current backend |
| C-03 | Login | UNVERIFIED | API login exists; physical login UNVERIFIED |
| C-04 | Home | UNVERIFIED | |
| C-05 | Scan merchant QR | UNVERIFIED | Camera / device required |
| C-06 | Checkout | UNVERIFIED | |
| C-07 | Pay (simulated adapter) | UNVERIFIED | Do not use live Airtel/TNM/bank rails |
| C-08 | Receipt | UNVERIFIED | |
| C-09 | History | UNVERIFIED | |

Automated support: mobile Jest + backend auth/QR/payment tests. They are not a substitute for the device loop.

---

## B. Merchant (app)

| ID | Step | Status | Evidence |
| :--- | :--- | :--- | :--- |
| M-01 | Login | UNVERIFIED | |
| M-02 | Merchant Mode (backend-gated) | UNVERIFIED | `GET /organization/my-access` is the gate |
| M-03 | Branch / till context | UNVERIFIED | |
| M-04 | Generate QR | UNVERIFIED | Customer JWT must not be able to create merchant QR |
| M-05 | Transaction visibility | UNVERIFIED | Merchant ledger is API-authoritative |

---

## C. Web

| ID | Step | Status | Evidence |
| :--- | :--- | :--- | :--- |
| W-01 | Native camera / Google Lens → HTTPS URL | BLOCKED | Needs `https://pay.pompo.mw/p/<id>` on the correct Vercel project |
| W-02 | Browser checkout `/p/[publicIdentifier]` | PASS (host) / UNVERIFIED (payment) | https://pompo-pay-app.vercel.app/p/does-not-exist returns the checkout app (200 HTML). Unknown QR resolves via live API (`QR code not found`). End-to-end pay+receipt needs a real production QR. |
| W-03 | Payment + receipt | UNVERIFIED | No production QR mutated this session |
| W-04 | `/account` | PASS (host) | https://pompo-pay-app.vercel.app/account returns 200 HTML |
| W-05 | Admin `/login` | PASS (host) | https://pompo-pay-app.vercel.app/login returns 200 HTML |

---

## D. Admin

Use https://pompo-pay-app.vercel.app (not `pay.pompo.mw` until that host is attached).

| ID | Step | Status | Evidence |
| :--- | :--- | :--- | :--- |
| A-01 | Platform-admin login | UNVERIFIED | Non-admin accounts are rejected by the API (`06e7743`). Browser click-through UNVERIFIED |
| A-02 | Dashboard | UNVERIFIED | Route exists; no browser session this session |
| A-03 | Merchants | UNVERIFIED | |
| A-04 | QR | UNVERIFIED | |
| A-05 | Transactions | UNVERIFIED | |
| A-06 | Providers | PASS (catalog policy) | Live rails remain inactive / simulated / contract-not-ready. Do not activate production providers for this demo. |
| A-07 | Settlements | UNVERIFIED | UI; simulated ingest tests exist |
| A-08 | Reconciliation | UNVERIFIED | |
| A-09 | Support | UNVERIFIED | |
| A-10 | Settings | UNVERIFIED | |
| A-11 | Health | PASS (API) | Production `/api/v1/health` returned application, database, redis, celery healthy (1 worker) |

---

## E. Security demonstration

| ID | Check | Status | Evidence |
| :--- | :--- | :--- | :--- |
| S-01 | Customer cannot create merchant QR | PASS (automated) | Demo/security pytest; live mutation not repeated |
| S-02 | Customer cannot read merchant ledger | PASS (automated) | |
| S-03 | Merchant cannot access another merchant | PASS (automated) | |
| S-04 | Normal user cannot access Admin | PASS (API policy) | Non-admin Master Admin login rejected |
| S-05 | Public QR cannot change merchant or locked amount | PASS (automated) | |

---

## F. Operator setup before a grant-board session

1. Confirm Railway `/api/v1/health/live` and `/health/ready` are 200.
2. Confirm Vercel production is Ready for `pompo-pay-app`.
3. Human: attach **only** `pay.pompo.mw` to `pompo-team` / `pompo-pay-app` (apex stays with the other Vercel account).
4. After Railway deploy of the CORS union, confirm OPTIONS `POST /api/v1/auth/login` from `Origin: https://pay.pompo.mw` returns `access-control-allow-origin: https://pay.pompo.mw`.
5. Provision a **designated demo tenant** only with the explicit seed confirm token, or use already-authorized production accounts. Do not wipe production.
6. Merchant generates a QR. Customer scans it or opens the HTTPS URL.
7. Pay with a **simulated** method. Confirm receipt, merchant activity, and Admin transaction lookup.
8. Show providers labeled simulated / unavailable / contract not ready. Do not flip live rails.

---

## G. Backup / recovery (current, not invented)

| Item | Status |
| :--- | :--- |
| Application code | GitHub `ZAI4751/Pompo-Pay-app` branch `Main-Pompo-branch` |
| Production PostgreSQL | Railway managed Postgres. Use the Railway dashboard backup/restore for that plugin. This session did **not** run a restore drill and did **not** add a separate backup product. |
| Redis | Cache/rate-limit/Celery broker. Treat as rebuildable, not a system of record. |
| Not configured here | Off-platform WAL archive, documented RPO/RTO, tested restore |

Restore (human, Railway dashboard): select the Postgres service → Backups → restore into a **new** instance first → point a staging API at it → only then consider production cutover. Never experiment with destructive restores on the live production volume.

---

## H. Android / iOS notes for the demo

### Android

- Package: `mw.pompo.mobile`
- Version: `1.0.0` / `versionCode` 1
- Production API: `https://pompo-api-production.up.railway.app/api/v1`
- HTTPS only (`usesCleartextTraffic: false`)
- App Links host: `pay.pompo.mw` `/p/`
- Release APK is built locally (`npm run android:apk`); keystore is gitignored
- Print the real cert fingerprint (do not invent one): `node ./scripts/print-android-cert-fingerprint.js`
- Set Vercel env `ANDROID_CERT_SHA256_FINGERPRINTS` to that value, then confirm `/.well-known/assetlinks.json` on **pay.pompo.mw**
- This production-readiness track did **not** rebuild the APK (no mobile runtime change)

### iOS (not submitted)

Required before an App Store build, all external to this repo unless already in Apple Developer:

- Apple Developer Program membership
- Bundle ID `mw.pompo.mobile` registered
- Distribution certificate + provisioning profile (or EAS credentials on macOS)
- Associated domain `applinks:pay.pompo.mw` plus `apple-app-site-association` **after** Team ID is known (do not invent a Team ID)
- Camera permission string is already in `app.json`
- Universal links blocked on the same `pay.pompo.mw` domain assignment as Android
- Do not submit to the App Store as part of this track

---

## I. What this session must not claim

- Physical install, scan, camera, or Google Lens success
- `pay.pompo.mw` serving POMPO checkout
- Real provider rails live
- Production database reset or demo seed applied
- iOS TestFlight / App Store submission
