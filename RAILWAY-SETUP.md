# Railway Infrastructure Configuration

This document provides the step-by-step configuration for deploying POMPO to Railway.

## Prerequisites

- Railway account created (https://railway.app)
- GitHub repository connected to Railway (OAuth)
- Deployment authorization obtained

---

## Step 1: Create Railway Project

### Action Required (Manual)

1. Log into Railway Dashboard: https://railway.app/dashboard
2. Click **"New Project"**
3. Select **"Deploy from GitHub"**
4. Select the Pompo repository
5. Grant Railway access to the repository
6. Name project: `pompo-production`
7. Click **"Create Project"**

### Expected Result

- New project created
- Project ID assigned (note this)
- Blank project (no services yet)

**Status:** ⏸️ Awaiting completion

---

## Step 2: Provision PostgreSQL Database

### Action Required (Manual in Railway Dashboard)

1. Inside `pompo-production` project, click **"+ New Service"**
2. Select **"PostgreSQL"**
3. Wait for PostgreSQL plugin to install

### Configuration

After plugin installs, Railway automatically creates a PostgreSQL service with:

- Image: postgres:latest
- Database name: `postgres`
- User: `postgres`
- Password: Auto-generated (Railway stores securely)

### Customize Settings

**Do NOT use defaults.** Modify these settings in the PostgreSQL service:

**General Tab:**
- Name: `pompo-postgres-prod`

**Variables Tab:**
- `POSTGRES_DB=pompo_production`
- `POSTGRES_USER=pompo_prod_user` (Change from default `postgres`)
- `POSTGRES_PASSWORD=` (Leave empty if Railway auto-generates)

**Network Tab:**
- **CRITICAL:** Disable "Public Network Access" (toggle OFF)
  - This keeps database private to project
  - Only FastAPI and Celery can connect

### Extract Connection Details

After creation, Railway provides:

**In the PostgreSQL service → "Generate Database URL":**

```
postgresql+asyncpg://pompo_prod_user:GENERATED_PASSWORD@postgres:5432/pompo_production
```

Or use individual credentials:

- **Host:** `postgres` (internal Railway network)
- **Port:** `5432`
- **Username:** `pompo_prod_user`
- **Password:** Copy from Railway Secrets tab
- **Database:** `pompo_production`

**Copy this for Phase B.**

**Status:** ⏸️ Awaiting PostgreSQL creation

---

## Step 3: Provision Redis Cache/Broker

### Action Required (Manual in Railway Dashboard)

1. Inside same `pompo-production` project, click **"+ New Service"**
2. Select **"Redis"**
3. Wait for Redis plugin to install

### Configuration

After plugin installs, Railway creates a Redis service with:

- Image: redis:latest
- Password: Auto-generated
- Port: `6379`

### Customize Settings

**General Tab:**
- Name: `pompo-redis-prod`

**Network Tab:**
- **CRITICAL:** Disable "Public Network Access" (toggle OFF)

### Extract Connection Details

**In Redis service → Connection Details:**

```
redis://DEFAULT_USER:GENERATED_PASSWORD@redis:6379/0
```

Or use individual credentials:

- **Host:** `redis` (internal Railway network)
- **Port:** `6379`
- **Password:** Copy from Railway Secrets tab
- **Database:** `0` (for app cache), but we'll override this for Celery

**Copy this for Phase B (modify DB for different services).**

**Status:** ⏸️ Awaiting Redis creation

---

## Step 4: Environment Variables - Railway Secrets

### Action Required (Manual in Railway Dashboard)

**CRITICAL:** Use Railway's Secrets Manager for sensitive values. Do NOT commit to Git.

1. Inside `pompo-production` project → **Settings** → **Variables**
2. Create a **New Variable** (not a secret) for each:

#### Application Configuration (Public)

| Variable | Value |
|----------|-------|
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `LOG_JSON` | `true` |
| `LOG_LEVEL` | `INFO` |
| `RATE_LIMIT_REQUESTS` | `1000` |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` |
| `DATABASE_POOL_SIZE` | `20` |
| `DATABASE_MAX_OVERFLOW` | `40` |
| `DATABASE_POOL_TIMEOUT` | `30` |
| `DATABASE_ECHO` | `false` |
| `REDIS_MAX_CONNECTIONS` | `30` |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` |

#### Database Configuration

**From PostgreSQL service (Phase B, Step 1):**

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://pompo_prod_user:PASSWORD@postgres:5432/pompo_production` |

#### Redis Configuration

**From Redis service (Phase B, Step 2):**

| Variable | Value |
|----------|-------|
| `REDIS_URL` | `redis://default:PASSWORD@redis:6379/0` |
| `CELERY_BROKER_URL` | `redis://default:PASSWORD@redis:6379/1` |
| `CELERY_RESULT_BACKEND` | `redis://default:PASSWORD@redis:6379/2` |

**NOTE:** Different database numbers for different services (0, 1, 2).

#### Host Configuration

| Variable | Value |
|----------|-------|
| `ALLOWED_HOSTS` | `api.yourdomain.com,pompo-api-prod.railway.app` |
| `CORS_ORIGINS` | `https://admin.yourdomain.com,https://youradmin.vercel.app` |

**UPDATE:** Replace with actual domains once known.

#### Secrets (Use Railway Secrets Manager)

3. Click **"Add Secret"** (not Variable) for each:

| Secret | Value | Notes |
|--------|-------|-------|
| `SECRET_KEY` | `<generate: python -c "import secrets; print(secrets.token_urlsafe(32))"` | 32+ chars, no placeholders |
| `JWT_SECRET_KEY` | `<generate same way>` | Different from SECRET_KEY |

**To generate locally (do NOT copy to clipboard permanently):**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy output to Railway Secrets tab, then clear local history.

### Variables vs. Secrets

**Variables Tab (Public, Git-friendly):**
- App configuration (DEBUG, LOG_LEVEL, pool sizes, etc.)
- Not sensitive
- Can be reviewed in Git if needed

**Secrets Tab (Private, NOT in Git):**
- SECRET_KEY, JWT_SECRET_KEY
- Database/Redis passwords
- Never logged
- Not visible in Git diffs

---

## Step 5: FastAPI Service Configuration

### Action Required (Manual in Railway Dashboard)

1. Inside `pompo-production` project, click **"+ New Service"**
2. Select **"GitHub"** → Select `pompo-pay-app` repository
3. Click **"Add Service"**

### Configuration

**General Tab:**

| Setting | Value |
|---------|-------|
| **Service Name** | `pompo-api-prod` |
| **Environment** | Select `pompo-production` |

**Deploy Tab:**

| Setting | Value |
|---------|-------|
| **Branch** | `main` |
| **Auto Deploy** | Enabled (redeploy on main push) |

**Build Tab:**

| Setting | Value |
|---------|-------|
| **Builder** | Docker |
| **Dockerfile Path** | `pompo-backend/docker/Dockerfile` |
| **Context** | `pompo-backend` |

**OR** use Railway auto-detection:
- If Dockerfile exists in root, Railway finds it automatically

**Deploy Tab → Pre-Deploy Script:**

```bash
cd pompo-backend && python -m alembic upgrade head
```

This ensures migrations run BEFORE FastAPI service starts.

**Start Command Override:**

Leave empty (use Dockerfile CMD). Railway will run:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Port Mapping:**

- Internal port: `8000`
- Railway auto-assigns public HTTPS port
- Public URL: `https://pompo-api-prod.railway.app` (auto-generated)

**Health Check:**

| Setting | Value |
|---------|-------|
| **HTTP Path** | `/api/v1/health/live` |
| **Interval** | `30s` |
| **Timeout** | `10s` |
| **Retries** | `3` |
| **Start Period** | `40s` |

**Memory & CPU:**

- Default: 512MB RAM, 0.5 CPU
- If needed (many concurrent requests): Increase to 1GB RAM, 1 CPU

### Verify Deployment

After deployment:

```bash
# Check service status in Railway Dashboard
# Should show "Deployed" status

# Test health endpoint
curl https://pompo-api-prod.railway.app/api/v1/health/live
# Should return: {"status": "alive", "timestamp": "..."}
```

**Status:** 🟢 Ready for deployment

---

## Step 6: Celery Worker Service Configuration

### Action Required (Manual in Railway Dashboard)

1. Inside `pompo-production` project, click **"+ New Service"**
2. Select **"GitHub"** → Select `pompo-pay-app` repository
3. Click **"Add Service"**

### Configuration

**General Tab:**

| Setting | Value |
|---------|-------|
| **Service Name** | `pompo-worker-prod` |
| **Environment** | Select `pompo-production` (same as FastAPI) |

**Deploy Tab:**

| Setting | Value |
|---------|-------|
| **Branch** | `main` |
| **Auto Deploy** | Enabled |

**Build Tab:**

| Setting | Value |
|---------|-------|
| **Builder** | Docker |
| **Dockerfile Path** | `pompo-backend/docker/Dockerfile` |
| **Context** | `pompo-backend` |

**Start Command Override:**

Critical: Override the default start command to run Celery instead of FastAPI:

```bash
cd /app/pompo-backend && celery -A app.workers.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=1000 \
  --time-limit=600 \
  --soft-time-limit=540 \
  --prefetch-multiplier=1
```

**Environment Variables:**

Inherits all from `pompo-production` project:
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `DATABASE_URL`
- `APP_ENV=production`
- All others

No additional configuration needed.

**Health Check:**

Celery workers don't expose HTTP health endpoints. Railway monitors via:
- Memory usage
- CPU usage
- Container restart count
- Exit code (0 = healthy, non-zero = restart)

**Memory & CPU:**

- Minimum: 512MB RAM, 0.5 CPU
- Recommended: 1GB RAM, 1 CPU (for processing longer tasks)

### Verify Deployment

After deployment:

```bash
# Check worker status in Railway Dashboard
# Should show "Deployed" status

# Worker logs should show:
# "celery@<hostname> ready"
# No connection errors to CELERY_BROKER_URL
```

**Status:** 🟢 Ready for deployment

---

## Step 7: Domain Configuration (Optional but Recommended)

### Action Required (Manual)

If using custom domain (e.g., `api.yourdomain.com`):

1. **In Railway:** FastAPI service → Settings → Domains
2. Click **"+ Custom Domain"**
3. Enter: `api.yourdomain.com`
4. Railway provides CNAME target (e.g., `cname.railway.app`)

5. **In your DNS provider:**
   - Add CNAME record: `api.yourdomain.com` → `cname.railway.app`
   - Wait for DNS propagation (5-30 minutes)

6. **Railway auto-provisions SSL/TLS certificate** (Let's Encrypt)

### Update Environment Variables

If using custom domain, update in Railway:

```
ALLOWED_HOSTS=api.yourdomain.com
```

**Status:** ⏸️ Optional, awaiting domain/DNS

---

## Step 8: Monitoring & Logs

### View Service Logs

1. Select service in Railway Dashboard
2. Click **"Logs"** tab
3. Real-time log streaming shows:
   - Application startup
   - API requests (with JSON logging)
   - Worker task execution
   - Errors

### Set Up Alerts (Optional)

1. Project Settings → Notifications
2. Add email or webhook for:
   - Deployment failures
   - Service crashes
   - High memory/CPU usage

---

## Deployment Order

**Execute in this order:**

1. ✅ Step 1: Create project
2. ✅ Step 2: Provision PostgreSQL
3. ✅ Step 3: Provision Redis
4. ✅ Step 4: Configure environment variables
5. ✅ Step 5: Deploy FastAPI service
   - Migration runs automatically (pre-deploy script)
   - Service starts after migration completes
6. ✅ Step 6: Deploy Celery worker
7. ✅ Step 7 (optional): Configure custom domain
8. ✅ Step 8: Verify all services healthy
9. ✅ Continue to production verification checklist

---

## Rollback Procedure (Emergency Only)

If production deployment fails:

### Option 1: Revert to Previous Deployment

```bash
# In Railway Dashboard:
# Select service → Deployments tab
# Click previous successful deployment → "Rollback"
```

### Option 2: Manual Database Downgrade (Dangerous)

Only if migration failed and broke schema:

```bash
# WARNING: This destroys recent data
# Only for true emergencies

cd pompo-backend
python -m alembic downgrade -1  # Downgrade one revision

# OR

python -m alembic downgrade <target-revision>
```

**Do NOT use without understanding data impact.**

---

## Troubleshooting

### FastAPI Service Won't Start

1. Check logs: **Service → Logs**
2. Look for: `ERROR` or `ModuleNotFoundError`
3. Common causes:
   - Missing dependencies (check requirements.txt)
   - Invalid DATABASE_URL or REDIS_URL format
   - Secret key validation failed (placeholder values)

### Database Connection Fails

1. Check DATABASE_URL format:
   ```
   postgresql+asyncpg://user:password@postgres:5432/pompo_production
   ```
2. Verify PostgreSQL service is running:
   - PostgreSQL service → Logs → Should show "ready to accept connections"
3. Verify private network enabled:
   - PostgreSQL → Network → "Public Network Access" should be OFF

### Celery Worker Won't Connect to Broker

1. Check CELERY_BROKER_URL format:
   ```
   redis://default:password@redis:6379/1
   ```
2. Verify Redis service is running
3. Verify REDIS_URL password matches

### Migrations Not Running

1. Check pre-deploy script is set:
   ```
   cd pompo-backend && python -m alembic upgrade head
   ```
2. Check FastAPI service logs for migration errors
3. Manually verify migration status:
   ```bash
   railway run --service pompo-api-prod -- \
     python -m alembic current
   ```

---

## Document Version
1.0

## Created
2026-09-01

## Status
🟢 READY FOR DEPLOYMENT

---

**CRITICAL REMINDER:**

- ✅ Do NOT commit secrets to Git
- ✅ Use Railway Secrets Manager for sensitive values
- ✅ Disable public network access for PostgreSQL and Redis
- ✅ Test health endpoints after deployment
- ✅ Monitor logs for errors during startup
- ✅ Do NOT proceed to frontend deployment until backend verified

