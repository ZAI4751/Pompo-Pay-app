# POMPO — Safe Physical Demonstration & Testing Guide

This guide details how a human operator can physically demonstrate the entire POMPO payment lifecycle without executing terminal commands during the test.

Developer setup (once, before the demo) uses Docker scripts. The operator then only uses:

- POMPO Android APK
- Phone camera / Google Lens / browser
- Master Admin

---

## 0. Classification of tests

| Kind | What it proves | Who runs it |
| :--- | :--- | :--- |
| **AUTOMATED TEST** | Backend/mobile contracts, authorization, simulated provider outcomes | `pytest`, Jest, `verify_demo_lab.py` |
| **BROWSER TEST** | Public `/p/{id}` checkout against the live API | Operator or engineer in a real browser |
| **PHYSICAL DEVICE TEST** | Native APK, camera, Google Lens, install | Operator with an Android phone |

Never record a native-camera or Google Lens result unless a real device performed the scan.

---

## 1. Test Identities & Credentials

The demonstration environment is pre-configured with distinct, isolated identities respecting strict server-authoritative role isolation:

| Identity | Email / Login | Plaintext Password | Role & Scope | Where to Use |
| :--- | :--- | :--- | :--- | :--- |
| **Platform Admin** | `demo.admin@pompo.mw` | `PompoDemoAdmin2026!` | `platform_admin`<br>*(No merchant mode)* | **Master Admin Web App** (`localhost:3000` or production URL) |
| **Merchant Owner** | `demo.merchant@pompo.mw` | `PompoDemoMerch2026!` | `merchant_owner`<br>*(POMPO Demo Merchant)* | **POMPO Android App**<br>*(Merchant Mode)* |
| **Customer** | `demo.customer@pompo.mw` | `PompoDemoCust2026!` | `customer`<br>*(Pre-enrolled Sandbox Methods)* | **POMPO Android App** & **Web Checkout** |

> **Note on Security**: Platform Admin has full administrative capabilities in Master Admin, but does not automatically imply merchant access. The authorization boundary is enforced server-side.

These passwords are lab identities, not staff credentials. Override with `POMPO_DEMO_*_PASSWORD` if the environment is shared.

---

## 2. Test Organization Context

- **Merchant**: `POMPO Demo Merchant` (Registration: `DEMO-REG-001`)
- **Branch**: `POMPO Demo Branch` (Lilongwe City Centre)
- **Till**: `POMPO Demo Till` (Code: `DEMO-TILL-01`)

QR public identifiers are printed by the seeder after each seed/reset. Do not reuse identifiers from an old document if a reset has run — scan whatever the merchant screen currently displays.

---

## 3. Developer setup (not part of the live demo)

Run once on the local backend (APP_ENV=development):

```bash
docker compose exec backend python scripts/reset_demo_environment.py
```

That script:

1. Revokes active QRs on the demo merchant (no conflicting terminal QR)
2. Re-creates demo identities, branch, till, simulated instruments
3. Issues one static QR and one dynamic QR (MWK 2500.00)

It refuses production unless `POMPO_ALLOW_DEMO_SEED=I_UNDERSTAND_THIS_IS_DEMO_DATA`.

It does **not** globally wipe the database or delete other merchants. Historical demo payments remain as a filterable baseline (settlement rows restrict hard deletes).

Optional API verification (developers only):

```bash
docker compose exec backend python scripts/verify_demo_lab.py
```

The operator should not need these commands during the demonstration.

---

## 4. Physical Test Execution Steps

### Step A: Merchant Generates / Displays QR
1. Open the POMPO APK on an Android device (or Master Admin on a computer).
2. Login as `demo.merchant@pompo.mw` (`PompoDemoMerch2026!`).
3. After login, Customer Home is shown first. Open **Merchant Mode** from Profile (backend eligibility, not a role toggle).
4. Tap the **QR** button in the bottom navigation.
5. The scannable QR plate appears with the merchant name, till name, and status. This is a real backend QR (`payment_url` = `https://pay.pompo.mw/p/<public_identifier>`).
6. (Optional) Enter an amount (e.g. `1,500.00`) and tap **Create dynamic QR** to produce an amount-locked dynamic QR code.
7. Alternatively, in **Master Admin** (`/qr-codes`), click the **Sticker** button on any till row to display or print the till sticker card.

### Step B: Customer Flow with POMPO App
1. On the customer device (or after logging into POMPO app as `demo.customer@pompo.mw` / `PompoDemoCust2026!`):
2. Tap the **Scan** button in the bottom navigation.
3. Aim the camera at the QR code displayed on the merchant screen or printed till sticker.
4. The scanner extracts the public identifier and automatically routes to `/customer/preview`.
5. The screen displays:
   - Paying: **POMPO Demo Merchant**
   - Location: **POMPO Demo Branch · POMPO Demo Till**
   - Amount: Read-only for dynamic QR, or enter amount for static QR.
6. Tap **Continue** to proceed to payment confirmation.
7. Select a payment method:
   - **Airtel Money Sandbox** (`...0999`, Default)
   - **TNM Mpamba Sandbox** (`...0888`)
8. Tap **Pay with Airtel Money Sandbox** (or TNM).
9. The simulated transaction processes through the backend, transitions state, and renders **Payment Successful** with real transaction reference (`PMP-...`).

### Step C: Customer Zero-Install Web Checkout (No App Required)
Use the **same** QR as Step A. Do not generate a second demo QR.

1. Using any standard Android phone or iPhone **without** opening the POMPO app:
2. Open the native **Phone Camera** or **Google Lens**.
3. Point at the QR code.
4. A notification banner pops up with the link: `https://pay.pompo.mw/p/<public_identifier>`.
5. Tap the link to open the browser.
6. The browser renders the lightweight public web checkout page:
   - Header: POMPO logo & security badge
   - Merchant: **POMPO Demo Merchant**
   - Till: **POMPO Demo Branch · POMPO Demo Till**
   - Amount: Read-only (dynamic QR) or customer-entered (static QR).
7. Select payment method (**Airtel Money** / **TNM Mpamba**).
8. Enter phone number (or login/register inline with minimum friction). Demo customer: `demo.customer@pompo.mw`.
9. Tap **Pay MWK ...**.
10. The browser invokes the real backend payment engine, polls for final settlement status, and displays the authentic green success confirmation with transaction reference.

### Step D: Verifying in Master Admin & Merchant Activity
1. **In Merchant App**: Go to **Activity** in Merchant Mode. The payment immediately appears in real-time transactions.
2. **In Master Admin**: look up the payment **by reference** (`PMP-...`). Platform admin does not use the merchant till ledger; scoped lookup is the supported admin path.

---

## 5. Error tests (operator or automated)

| Case | How | Expected user-facing result |
| :--- | :--- | :--- |
| Invalid QR | Scan garbage / `NOT-A-POMPO-QR` | Not a POMPO QR / not found — no payment |
| Expired dynamic QR | Wait past expiry or inspect with inactive flag | QR has expired |
| Revoked QR | Merchant revokes, customer rescans | QR has been revoked |
| Failed simulated payment | Provider `simulated_failure` | Payment failed — retry available |
| Processing / pending | Provider `simulated_pending` | Processing — poll continues |
| Timeout / retry | Provider `simulated_timeout` | Timeout/failed — retry is safe (idempotency) |
| Network failure | Airplane mode mid-pay | Connection error, no fake success |
| Unavailable method | Disabled catalog rail | Method not available |

---

## 6. Deterministic Simulation Controls

The demonstration environment includes deterministic simulation providers to test edge cases without real money:

- **SUCCESS**: Provider `simulated` (Priority 1) returns guaranteed `SUCCESS`.
- **FAILED**: Provider `simulated_failure` returns deterministic `REJECTED/FAILED`.
- **PENDING**: Provider `simulated_pending` returns `PENDING` (allowing polling verification).
- **TIMEOUT**: Provider `simulated_timeout` tests timeout recovery and retry safety.
- **IDEMPOTENT REPLAY**: Repeating a payment submission with the same idempotency key safely returns the existing transaction without duplicate charges. Modifying the payload with the same key is strictly rejected by the backend.

Simulated rails are labeled sandbox/test. Airtel, TNM, Standard Bank, NBS, National Bank, and First Capital are **not** live production rails.

---

## 7. Security the operator can trust (already enforced by the API)

Customer JWT cannot: create merchant QR, read merchant ledger, read settlements, pick a foreign merchant/branch/till.

Merchant JWT can only generate QR for authorized branch/till.

Public QR inspect cannot change merchant, cannot override a dynamic amount, cannot bypass expiry or revocation.

