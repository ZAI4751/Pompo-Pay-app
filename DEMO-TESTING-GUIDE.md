# POMPO — Safe Physical Demonstration & Testing Guide

This guide details how a human operator can physically demonstrate the entire POMPO payment lifecycle without executing terminal commands during the test.

---

## 1. Test Identities & Credentials

The demonstration environment is pre-configured with distinct, isolated identities respecting strict server-authoritative role isolation:

| Identity | Email / Login | Plaintext Password | Role & Scope | Where to Use |
| :--- | :--- | :--- | :--- | :--- |
| **Platform Admin** | `demo.admin@pompo.mw` | `PompoDemoAdmin2026!` | `platform_admin`<br>*(No merchant mode)* | **Master Admin Web App** (`localhost:3000` or production URL) |
| **Merchant Owner** | `demo.merchant@pompo.mw` | `PompoDemoMerch2026!` | `merchant_owner`<br>*(POMPO Demo Merchant)* | **POMPO Android App**<br>*(Merchant Mode)* |
| **Customer** | `demo.customer@pompo.mw` | `PompoDemoCust2026!` | `customer`<br>*(Pre-enrolled Sandbox Methods)* | **POMPO Android App** & **Web Checkout** |

> **Note on Security**: Platform Admin has full administrative capabilities in Master Admin, but does not automatically imply merchant access. The authorization boundary is enforced server-side.

---

## 2. Test Organization Context

- **Merchant**: `POMPO Demo Merchant` (Registration: `DEMO-REG-001`)
- **Branch**: `POMPO Demo Branch` (Lilongwe City Centre)
- **Till**: `POMPO Demo Till` (Code: `DEMO-TILL-01`)
- **Pre-generated Static QR**: `QRBB7ECF8745E7` → [`https://pay.pompo.mw/p/QRBB7ECF8745E7`](https://pay.pompo.mw/p/QRBB7ECF8745E7)
- **Pre-generated Dynamic QR**: `QRA4901DB1AA94` (MWK 2500.00) → [`https://pay.pompo.mw/p/QRA4901DB1AA94`](https://pay.pompo.mw/p/QRA4901DB1AA94)

---

## 3. Physical Test Execution Steps

### Step A: Merchant Generates / Displays QR
1. Open the POMPO APK on an Android device (or Master Admin on a computer).
2. Login as `demo.merchant@pompo.mw` (`PompoDemoMerch2026!`).
3. Tap **Merchant · switch** at the top right to switch to **Merchant Mode**.
4. Tap the **QR** button in the bottom navigation.
5. The scannable QR plate appears with the merchant name, till name, and status.
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
8. Enter phone number (or login/register inline with minimum friction).
9. Tap **Pay MWK ...**.
10. The browser invokes the real backend payment engine, polls for final settlement status, and displays the authentic green success confirmation with transaction reference.

### Step D: Verifying in Master Admin & Merchant Activity
1. **In Merchant App**: Go to **Activity** in Merchant Mode. The payment immediately appears in real-time transactions.
2. **In Master Admin**: Go to `/transactions`. The transaction appears with status `SUCCESS`, method `mobile_money`, provider `simulated`, and full audit trail.

---

## 4. Deterministic Simulation Controls

The demonstration environment includes deterministic simulation providers to test edge cases without real money:

- **SUCCESS**: Provider `simulated` (Priority 1) returns guaranteed `SUCCESS`.
- **FAILED**: Provider `simulated_failure` (Priority 2) returns deterministic `REJECTED/FAILED`.
- **PENDING**: Provider `simulated_pending` (Priority 3) returns `PENDING` (allowing polling verification).
- **TIMEOUT**: Provider `simulated_timeout` (Priority 4) tests timeout recovery and retry safety.
- **IDEMPOTENT REPLAY**: Repeating a payment submission with the same idempotency key safely returns the existing transaction without duplicate charges. Modifying the payload with the same key is strictly rejected by the backend.
