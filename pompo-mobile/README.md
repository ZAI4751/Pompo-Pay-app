# POMPO Mobile (M012)

One Expo / React Native TypeScript app for **Customer Mode** and **Merchant Mode**.
The backend remains authoritative. This client does not process payments, validate
QR signatures, route providers, or grant permissions.

Contract: `pompo-backend/docs/mobile-api-contract.md`

## Why Expo

Android + iOS from one TypeScript codebase, first-class camera/QR (`expo-camera`),
and hardware-backed token storage (`expo-secure-store`). No extra native modules
beyond Expo.

## Configuration

Set `EXPO_PUBLIC_API_BASE_URL` (no trailing slash).

| Environment | Value |
|---|---|
| iOS simulator | `http://localhost:8000/api/v1` |
| Android emulator | `http://10.0.2.2:8000/api/v1` |
| Physical device | your machine LAN URL, e.g. `http://192.168.x.x:8000/api/v1` |
| Production | `https://pompo-api-production.up.railway.app/api/v1` |

Release builds default to the production API. Do not commit secrets. Access and
refresh tokens live in SecureStore, never AsyncStorage.

## Commands

```bash
cd pompo-mobile
npm install
npx expo start
```

Physical device: install Expo Go and scan the QR from the terminal.

```bash
npm run android          # Expo Go / emulator (Windows host)
npm run ios              # macOS only
npm run lint
npm run typecheck
npm test
npm run export:android   # JS bundle export (not an app-store AAB)
```

Native project folders (`ios/`, `android/`) are generated on demand:

```bash
npx expo prebuild
```

iOS archive/signing requires Apple certificates on macOS. This milestone does
not publish to app stores.

## Sandbox journey

1. Sign in as a merchant owner (`merchant_owner`).
2. Merchant Mode → QR → **New dynamic QR**.
3. Switch to Customer Mode (or sign in as a `customer` user).
4. Scan the QR (or paste the payload via a debug device).
5. Confirm → backend `from-qr` + `process` with the simulated provider.
6. Customer history and merchant activity show the real transaction.

Provision a `customer` user from Master Admin (`users:create` + `customer` role).
There is no self-registration in M012.

## Limitations

- Camera integration tests are unit/component tests; they do not open a physical camera.
- iOS release signing is not configured on Windows.
- Customer self-serve signup, push notifications, and live Airtel/TNM rails are out of scope.
