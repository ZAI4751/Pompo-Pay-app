# POMPO Railway Production Infrastructure

Phase A setup guide for deploying the FastAPI backend on [Railway](https://railway.app).
**This document does not deploy anything** — it defines the approved topology and
human steps required before the first staging deploy.

Master Admin remains on **Vercel** and calls the Railway API over HTTPS.

---

## Approved topology

```text
                    INTERNET
                        │
                     HTTPS
                        │
                 ┌──────▼──────┐
                 │   FastAPI   │  ← Railway service (docker/Dockerfile, role: api)
                 │   API       │
                 └──────┬──────┘
                        │  private network
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
    PostgreSQL       Redis        Celery worker
    (plugin)         (plugin)     (same image, role: worker)
    private          private      no public HTTP
```

| Service | Railway type | Public HTTP |
|---------|--------------|-------------|
| `pompo-api` | Dockerfile (`railway.toml`) | Yes (HTTPS) |
| `pompo-postgres` | PostgreSQL plugin | **No** |
| `pompo-redis` | Redis plugin | **No** |
| `pompo-celery` | Dockerfile (worker CMD) | **No** |

Project name: **`pompo-production`**

---

## Prerequisites (human)

1. Railway account with billing enabled
2. Railway CLI installed and authenticated:
   ```bash
   npm install -g @railway/cli
   railway login
   railway whoami
   ```
3. GitHub repository access authorized in Railway (for deploy-from-Git)
4. Domain planned (optional for first staging):
   - `api.<your-domain>` → Railway API service
   - `admin.<your-domain>` → Vercel Master Admin
5. Production secrets generated offline (never committed):
   - `SECRET_KEY` (≥48 random chars)
   - `JWT_SECRET_KEY` (≥48 random chars)

---

## Step 1 — Create Railway project

**Human action required**

1. Open https://railway.app/dashboard
2. **New Project** → **Deploy from GitHub** → select `Pompo-Pay-app`
3. Name the project `pompo-production`
4. Set **Root Directory** for the API service to `pompo-backend`

Or via CLI (after `railway login`):

```bash
cd pompo-backend
railway init --name pompo-production
```

Do not create duplicate projects if `pompo-production` already exists.

---

## Step 2 — PostgreSQL

**Human action required**

1. In the project: **+ New** → **Database** → **PostgreSQL**
2. Rename service to `pompo-postgres`
3. **Disable public networking** (private only)
4. Note the internal `DATABASE_URL` reference variable Railway exposes

**Application URL format** (set on API + worker services):

```text
postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DATABASE
```

If Railway provides `postgresql://`, change the scheme to `postgresql+asyncpg://`.
Add `?ssl=require` when the host requires TLS.

**Do not** replace or modify the local development database.

---

## Step 3 — Redis

**Human action required**

1. **+ New** → **Database** → **Redis**
2. Rename to `pompo-redis`
3. **Disable public networking**

Map Redis logical databases on the API and worker services:

| Variable | Typical value |
|----------|---------------|
| `REDIS_URL` | `${{Redis.REDIS_URL}}/0` |
| `CELERY_BROKER_URL` | `${{Redis.REDIS_URL}}/1` |
| `CELERY_RESULT_BACKEND` | `${{Redis.REDIS_URL}}/2` |

(Adjust reference syntax to match Railway's variable linking UI.)

---

## Step 4 — FastAPI API service

Uses `docker/Dockerfile` + `docker/entrypoint.sh` with default role **`api`**.

| Setting | Value |
|---------|--------|
| Root directory | `pompo-backend` |
| Dockerfile | `docker/Dockerfile` |
| Start command | *(default ENTRYPOINT)* `/app/docker/entrypoint.sh api` |
| Health check | `GET /api/v1/health/live` |
| `PORT` | Injected by Railway (entrypoint reads it) |
| `RUN_MIGRATIONS` | `true` (runs `alembic upgrade head` before uvicorn) |

Copy all variables from `.env.production.example`. Link Postgres and Redis
reference variables from the plugins.

**Production settings enforced by code:**

- `APP_ENV=production` → `DEBUG=false`, `LOG_JSON=true`
- Placeholder `SECRET_KEY` / `JWT_SECRET_KEY` → startup failure
- Swagger/ReDoc disabled when `DEBUG=false`

---

## Step 5 — Celery worker service

**Human action required**

1. **+ New** → **GitHub Repo** (same repo) or **Empty Service** + Dockerfile
2. Root directory: `pompo-backend`
3. Same Dockerfile as API
4. **Start command:** `/app/docker/entrypoint.sh worker`
5. **No public domain** attached
6. Environment: same as API **except**:
   - `RUN_MIGRATIONS=false`
7. Health: monitored via API `/api/v1/health` Celery component (worker inspect ping)

Current production-critical Celery usage: **health verification only**
(`app.tasks.sample.ping_task`). No payment/webhook async jobs yet.

---

## Step 6 — Migrations

**Strategy:** idempotent `alembic upgrade head` on API container start.

| Role | `RUN_MIGRATIONS` | Behavior |
|------|------------------|----------|
| API | `true` (default) | migrate → uvicorn |
| Worker | `false` | celery only |
| One-off job | `migrate` CMD | migrate only, then exit |

**Current head:** `0008_provider_management`

Manual one-off (if needed):

```bash
railway run --service pompo-api /app/docker/entrypoint.sh migrate
```

Never rewrite historical migrations. Never run destructive downgrades in production.

---

## Step 7 — Environment variables

See `.env.production.example` for the full checklist (names only).

**Never store in Git or `NEXT_PUBLIC_*`:**

- `SECRET_KEY`, `JWT_SECRET_KEY`
- `DATABASE_URL`, `REDIS_URL`, broker URLs
- Provider credential values
- `POMPO_ADMIN_PASSWORD`

---

## Step 8 — CORS and trusted hosts

Set after you know the admin origin(s):

```env
# Example — replace with real values
ALLOWED_HOSTS=api.yourdomain.com,pompo-api-production.up.railway.app
CORS_ORIGINS=https://admin.yourdomain.com,https://your-project.vercel.app
```

No wildcard `*` in production.

---

## Step 9 — Admin bootstrap (one-time, human)

**Do not** auto-create production admins.

Use `scripts/secure_bootstrap_admin.py` via a one-off Railway run:

```bash
railway run \
  -e SECURE_BOOTSTRAP_OVERRIDE=allow-production-bootstrap \
  -e POMPO_ADMIN_EMAIL=admin@yourdomain.com \
  -e POMPO_ADMIN_PASSWORD='<generated-password>' \
  python scripts/secure_bootstrap_admin.py
```

Requirements:

- Migrations applied (`platform_admin` role exists)
- Password ≥12 characters, from a secure generator
- Password never logged or committed
- Run once, then audit the account

`scripts/seed_admin.py` refuses `APP_ENV=production` — development only.

---

## Step 10 — Verification (after staging deploy is authorized)

```bash
python scripts/verify_production_deployment.py https://<railway-api-host>/api/v1
```

Or manually:

```bash
curl https://<host>/api/v1/health/live
curl https://<host>/api/v1/health/ready
curl https://<host>/api/v1/health
```

---

## Step 11 — Vercel (separate, not Railway)

See `pompo-frontend/docs/admin-deployment.md`.

Production frontend variable:

```env
NEXT_PUBLIC_API_BASE_URL=https://api.<your-domain>/api/v1
```

Deploy Vercel **after** Railway API is reachable over HTTPS and CORS is set.

---

## Security checklist (architecture)

| Control | Status when configured per this guide |
|---------|--------------------------------------|
| HTTPS on API | Railway-provided |
| Postgres private | Plugin, no public port |
| Redis private | Plugin, no public port |
| Adminer | Not deployed |
| `DEBUG=false` | `APP_ENV=production` |
| Production mocks disabled | Vercel build guard |
| RBAC | Server-side (unchanged) |
| Rate limiting | Redis-backed |
| Structured logs | `LOG_JSON=true` |
| Request IDs | Middleware (unchanged) |

---

## Stop gate — do not proceed without

- [ ] `railway login` completed
- [ ] Railway project `pompo-production` created
- [ ] PostgreSQL + Redis provisioned (private)
- [ ] API + Celery services configured
- [ ] Production secrets set in Railway (not Git)
- [ ] `ALLOWED_HOSTS` + `CORS_ORIGINS` set for real origins
- [ ] First staging deploy explicitly authorized
- [ ] Domain/DNS (optional for Railway default hostname testing)

---

## Related files

| File | Purpose |
|------|---------|
| `docker/Dockerfile` | Production image |
| `docker/entrypoint.sh` | api / worker / migrate roles |
| `railway.toml` | API service Railway config |
| `.env.production.example` | Variable checklist |
| `scripts/secure_bootstrap_admin.py` | One-time admin bootstrap |
| `scripts/verify_production_deployment.py` | Post-deploy smoke tests |

Local development is unchanged: `docker compose up` in `pompo-backend/`.
