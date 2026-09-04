# POMPO Master Admin — Vercel Deployment Guide

This document prepares `pompo-frontend/` for deployment on [Vercel](https://vercel.com).
It does **not** deploy the application — follow the steps at the end when ready.

The FastAPI backend (`pompo-backend/`) remains a **separate** service. The frontend
is a static/SSR Next.js app that calls the backend over HTTPS from the browser.

---

## Vercel project layout

| Setting | Value |
|---------|--------|
| **Repository root** | Monorepo root (or connect only the frontend repo) |
| **Root Directory** | `pompo-frontend` |
| **Framework Preset** | Next.js (auto-detected) |
| **Build Command** | `npm run build` (default) |
| **Output Directory** | `.next` (default) |
| **Install Command** | `npm install` (default) |
| **Node.js version** | 20.x (recommended; match local dev) |

No `vercel.json` is required for a standard Next.js 16 App Router project in
`pompo-frontend/`. Vercel detects `next build` automatically.

---

## Environment variables

Only **`NEXT_PUBLIC_*`** variables are available in the browser bundle. Never put
secrets, JWT keys, database passwords, or provider credentials in Vercel env vars
with that prefix.

| Variable | Required | Development | Preview | Production |
|----------|----------|-------------|---------|------------|
| `NEXT_PUBLIC_API_BASE_URL` | Preview + Production | `http://localhost:8000/api/v1` | Staging HTTPS API URL | Production HTTPS API URL |
| `NEXT_PUBLIC_USE_MOCKS` | No | `false` (or `true` for UI-only demo) | `false` (or `true` for demo deploys) | **`false` or unset** (build fails if `true`) |

### Local development

1. Copy `.env.example` → `.env.local`
2. Keep defaults for Docker backend:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_USE_MOCKS=false
```

3. Run `npm run dev` (hot reload) or `npm run build && npm run start` (production parity).

### Vercel Preview (per-PR / staging)

Set in Vercel → **Environment Variables** → scope **Preview**:

```env
NEXT_PUBLIC_API_BASE_URL=https://api-staging.your-domain.example/api/v1
NEXT_PUBLIC_USE_MOCKS=false
```

Point at a **staging** FastAPI instance, not production data, unless intentional.

### Vercel Production

Set in Vercel → **Environment Variables** → scope **Production**:

```env
NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.example/api/v1
```

Do **not** set `NEXT_PUBLIC_USE_MOCKS=true` in Production. The build will fail if
you do — mock mode bypasses real login and must never ship on a public admin URL.

---

## How configuration is resolved

Logic lives in `src/lib/api/config.ts`:

- **`DEPLOY_ENV`**: `local` | `preview` | `production` (from `VERCEL_ENV`)
- **`API_BASE_URL`**: from `NEXT_PUBLIC_API_BASE_URL`, with `http://localhost:8000/api/v1` fallback **only** on local builds
- **`USE_MOCKS`**: `true` only when env is `"true"` **and** deploy is not production

On Vercel Preview/Production, `NEXT_PUBLIC_API_BASE_URL` is **mandatory**.
Production URLs must use **HTTPS** and must not point at `localhost`.

---

## Backend CORS requirement

The browser enforces CORS. The FastAPI backend must explicitly allow the deployed
Master Admin origin. **Do not use `*` in production.**

Set `CORS_ORIGINS` on the backend (see `pompo-backend/.env.example`):

```env
# Example production — replace extra preview hosts as needed
CORS_ORIGINS=https://pay.pompo.mw,https://pompo-pay-app.vercel.app
```

| Frontend origin | When to add |
|-----------------|-------------|
| `http://localhost:3000` | Local dev only |
| `http://127.0.0.1:3000` | Local dev (different browser origin) |
| `https://pompo-pay-app.vercel.app` | Vercel production (canonical; also unioned in backend code) |
| `https://pay.pompo.mw` | Public checkout host (canonical; also unioned in backend code) |
| `https://<branch>-<team>.vercel.app` | Preview deployments (if previews call the production API) |

After changing `CORS_ORIGINS`, redeploy or restart the backend. CORS is enforced
server-side; frontend changes alone cannot fix a blocked origin.

---

## Authentication model (production)

The Master Admin uses **live FastAPI auth** when `NEXT_PUBLIC_USE_MOCKS` is not enabled:

1. `POST /api/v1/auth/login` → access + refresh tokens
2. Access token held in memory (`session.ts`) for API calls
3. Refresh token + access token stored in **`sessionStorage`** (`pompo_admin_session`)
4. `POST /api/v1/auth/refresh` on session restore
5. Permissions loaded from `GET /api/v1/rbac/roles/{role_id}`

### Security considerations

- **No secrets in the bundle** — only public API base URL and mock flag
- **Tokens in sessionStorage** — standard SPA pattern; vulnerable if XSS exists on
  the admin origin. Mitigate with dependency hygiene; long-term consider httpOnly
  cookie + BFF if threat model requires it
- **Mock mode** — disabled in Vercel production builds; demo login never runs there
- **401 handling** — API client clears session and redirects to `/login`; no token
  values logged

---

## Mock mode boundary

| Mode | Auth | Data |
|------|------|------|
| `USE_MOCKS=false` (production default) | Real `/auth/login` | Live `/api/v1` for implemented capabilities |
| `USE_MOCKS=true` (local/preview only) | Demo session, no password check | Fixtures for capabilities marked `live` in mocks; unavailable APIs show empty/coming-soon |

Provider enable/disable and health mutations are blocked in mock mode. Production
authentication always uses the real backend when mocks are off.

---

## Routing and rendering

- App Router with client-heavy authenticated shell (`"use client"` in `(app)/layout.tsx`)
- No `middleware.ts` — auth gating is client-side via `AuthContext`
- Dashboard and admin pages pre-render static shells; user state loads in the browser
- Compatible with Vercel’s Next.js runtime (no custom server required)

Do not force `output: 'export'` — the app uses standard Next.js server features.

---

## Secret management

**Git-ignored (never commit):**

- `.env`
- `.env.local`
- `.env.*.local`
- `.vercel/`

**Safe in Vercel (public):**

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_USE_MOCKS`

**Never in frontend:**

- `JWT_SECRET_KEY`, `SECRET_KEY`, database URLs, provider credentials, admin passwords

---

## Verification before first deploy

From `pompo-frontend/`:

```bash
npm install
npm run typecheck
npm run lint
npm run build
```

For Vercel parity locally (requires env vars set):

```bash
# PowerShell
$env:VERCEL_ENV="production"
$env:NEXT_PUBLIC_API_BASE_URL="https://api-staging.example.com/api/v1"
npm run build
```

Optional (if Vercel CLI is installed):

```bash
npx vercel build
```

Do not claim deployment succeeded until Vercel dashboard shows a green deployment.

---

## Deployment workflow (when ready)

1. **Backend** deployed and reachable over HTTPS with valid TLS
2. **CORS** updated with the Vercel admin origin(s)
3. **Vercel project** created; Root Directory = `pompo-frontend`
4. **Environment variables** set per scope (Preview vs Production)
5. **Platform admin** seeded on the target backend (not via `seed_admin.py` in production)
6. Connect Git branch → deploy Preview → smoke test login and RBAC
7. Assign custom domain (optional) → update backend `CORS_ORIGINS` → deploy Production
8. Smoke test: login, dashboard, merchants, providers, logout

---

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| Blank page then redirect | Normal for unauthenticated `/dashboard` visit |
| “Could not reach the Pompo backend” | Wrong `NEXT_PUBLIC_API_BASE_URL`, backend down, or CORS block |
| CORS error in browser console | Backend `CORS_ORIGINS` missing the Vercel admin URL |
| Build fails on Vercel | Missing `NEXT_PUBLIC_API_BASE_URL` or `USE_MOCKS=true` in Production |
| Login works locally, not on Vercel | Production API URL, CORS, or admin not seeded on that backend |
| Demo mode on production URL | Should be impossible — rebuild failed if `USE_MOCKS=true` in Production |

---

## Related documentation

- `docs/admin-ui-architecture.md` — frontend structure and mock/API boundary
- `pompo-backend/docs/testing.md` — seeding local admin (development only)
- `pompo-backend/.env.example` — backend `CORS_ORIGINS` template
