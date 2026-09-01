# POMPO Production Security Audit Checklist

**Date:** 2026-09-01  
**Deployment Phase:** K - Security Gate  
**Status:** MANDATORY VERIFICATION BEFORE GO-LIVE

---

## Pre-Deployment: Code Repository Audit

### K.1.1: Secret Detection in Git

**Objective:** Ensure NO production secrets are committed to version control.

**Action:**

```bash
cd /path/to/pompo

# Check entire git history for common secret patterns
git log --all --full-history -p | grep -i \
  -e "secret_key" \
  -e "jwt_secret" \
  -e "password" \
  -e "api_key" \
  -e "token" \
  -e "credential" | head -50
```

**Expected Result:**
- ✅ NO output (no secrets in Git)
- ❌ If output appears: Do NOT deploy. Secrets must be rotated immediately.

**If Secrets Found:**
1. Stop deployment immediately
2. Rotate all compromised credentials
3. Consider git history rewrite (requires team coordination)
4. Re-audit before retrying

### K.1.2: .env Files in Git

**Objective:** Ensure development .env files are NOT tracked.

**Action:**

```bash
cd /path/to/pompo

# Check for .env files in Git
git ls-files | grep "\.env"
```

**Expected Result:**
- ✅ No output (no .env files tracked)
- ✅ .gitignore contains: `.env`, `.env.local`, `.env.*.local`

**Verify .gitignore:**

```bash
cat .gitignore | grep -E "^\.env"
```

Expected entries:
```
.env
.env.local
.env.*.local
```

---

## Pre-Deployment: Frontend Bundle Audit

### K.2.1: Secrets in Frontend Build

**Objective:** Ensure NO secrets are embedded in Next.js production bundle.

**Action (Local Verification):**

```bash
cd pompo-frontend

# Build production bundle
npm run build

# Search for secrets in build output
find .next -type f -name "*.js" -o -name "*.json" | xargs grep -l \
  -E "secret|password|token|api.?key" 2>/dev/null

# Specific checks
grep -r "SECRET_KEY\|JWT_SECRET\|password" .next/ 2>/dev/null
```

**Expected Result:**
- ✅ No output (no secrets in bundle)
- ❌ If found: Investigate and ensure only public env vars are in bundle

### K.2.2: Environment Variables in Frontend

**Objective:** Verify ONLY public variables (NEXT_PUBLIC_*) are in bundle.

**Action (Vercel Dashboard Verification):**

1. Go to **Vercel Project Settings → Environment Variables**
2. Verify the following:

```
NEXT_PUBLIC_API_BASE_URL=https://<backend-url>/api/v1
NEXT_PUBLIC_USE_MOCKS=false
```

3. ✅ Confirm NO other variables are exposed to client
4. ✅ Confirm NO secrets in Vercel dashboard environment

**Note:** Vercel automatically hides non-NEXT_PUBLIC_ variables from the bundle.

---

## Post-Deployment: Configuration Audit

### K.3.1: FastAPI Production Configuration

**Objective:** Verify critical production settings are correct.

**Action (Railway Dashboard Verification):**

1. Select **pompo-api-prod** service
2. Go to **Settings → Variables**
3. Verify each setting:

| Setting | Expected | Action |
|---------|----------|--------|
| `APP_ENV` | `production` | If NOT `production`: ❌ FAIL |
| `DEBUG` | `false` | If NOT `false`: ❌ FAIL |
| `LOG_JSON` | `true` | If NOT `true`: ⚠️ WARNING |
| `ALLOWED_HOSTS` | `api.yourdomain.com,*.railway.app` | Should be restrictive, no wildcards |
| `CORS_ORIGINS` | Specific domain (e.g., `https://admin.yourdomain.com`) | ❌ FAIL if wildcard (*) |

**Required Outcome:**
- ✅ APP_ENV=production
- ✅ DEBUG=false
- ✅ CORS_ORIGINS is specific (no wildcards)
- ✅ ALLOWED_HOSTS is restrictive

### K.3.2: Celery Worker Configuration

**Action (Railway Dashboard Verification):**

1. Select **pompo-worker-prod** service
2. Verify inherits same environment as pompo-api-prod
3. Verify `APP_ENV=production` is set

**Required Outcome:**
- ✅ Worker uses production config
- ✅ No hardcoded credentials in environment

### K.3.3: Database Security (PostgreSQL)

**Action (Railway Dashboard Verification):**

1. Select **pompo-postgres-prod** service
2. Go to **Settings → Network**

| Setting | Expected | Check |
|---------|----------|-------|
| Public Network Access | OFF (disabled) | If ON: ❌ CRITICAL FAIL |
| Private VPC | Enabled | Verify database is VPC-only |

3. Verify credentials:
   - Username is NOT default (`postgres`)
   - Password is Railway-generated (strong)
   - Password NOT visible in code/Git

**Required Outcome:**
- ✅ Database is PRIVATE (not publicly accessible)
- ✅ Strong password used
- ✅ Password stored in Railway Secrets only

### K.3.4: Redis Security

**Action (Railway Dashboard Verification):**

1. Select **pompo-redis-prod** service
2. Go to **Settings → Network**

| Setting | Expected | Check |
|---------|----------|-------|
| Public Network Access | OFF (disabled) | If ON: ❌ CRITICAL FAIL |
| Private VPC | Enabled | Verify Redis is VPC-only |

3. Verify credentials:
   - Password is set (Railway-generated)
   - Password NOT visible in code/Git

**Required Outcome:**
- ✅ Redis is PRIVATE (not publicly accessible)
- ✅ Password-protected
- ✅ Password stored in Railway Secrets only

---

## Post-Deployment: Network & HTTPS Audit

### K.4.1: HTTPS Enforcement

**Objective:** Verify all traffic is encrypted.

**Action:**

```bash
# Test HTTPS
curl -I https://<backend-url>/api/v1/health/live
```

**Expected Result:**
- ✅ Returns HTTP/2 200 or HTTP/1.1 200 (with HTTPS)
- ❌ HTTP connection: FAIL - HTTPS required

### K.4.2: Security Headers (Optional but Recommended)

**Action:**

```bash
curl -I https://<backend-url>/api/v1/health/live | grep -i \
  -e "strict-transport-security" \
  -e "x-frame-options" \
  -e "x-content-type-options"
```

**Expected (optional but good):**
- ⚠️ These headers improve security but are not critical for this phase

---

## Post-Deployment: Authentication & Authorization Audit

### K.5.1: Unauthenticated Request Blocking

**Objective:** Verify protected endpoints require authentication.

**Action:**

```bash
# Attempt without token
curl -X GET https://<backend-url>/api/v1/merchants
```

**Expected Result:**
- ✅ Returns 401 Unauthorized
- ❌ Returns 200: FAIL - endpoint exposed without auth

### K.5.2: Invalid Token Rejection

**Action:**

```bash
# Request with invalid token
curl -X GET https://<backend-url>/api/v1/merchants \
  -H "Authorization: Bearer invalid.token.xyz"
```

**Expected Result:**
- ✅ Returns 401 Unauthorized
- ❌ Returns 200: FAIL - invalid tokens accepted

### K.5.3: Valid Token Acceptance

**Action (with valid admin token from login):**

```bash
curl -X GET https://<backend-url>/api/v1/merchants \
  -H "Authorization: Bearer <valid-token>"
```

**Expected Result:**
- ✅ Returns 200 with merchant list (or 200 empty list)
- ❌ Returns 401: FAIL - valid token rejected

### K.5.4: RBAC Enforcement (Non-Admin Blocked)

**Objective:** Verify non-admin users cannot access admin endpoints.

**Prerequisites:**
- Create a non-admin user in database (with limited role)
- Obtain valid token for that user

**Action:**

```bash
# Attempt admin endpoint with non-admin token
curl -X GET https://<backend-url>/api/v1/roles \
  -H "Authorization: Bearer <non-admin-token>"
```

**Expected Result:**
- ✅ Returns 403 Forbidden (insufficient permissions)
- ❌ Returns 200: FAIL - RBAC not enforced

---

## Post-Deployment: Rate Limiting Audit

### K.6.1: Rate Limit Headers

**Objective:** Verify rate limiting is functional.

**Action:**

```bash
# Single request should include rate limit headers
curl -I https://<backend-url>/api/v1/health/live | grep -i "x-ratelimit"
```

**Expected Result:**
- ✅ Headers present: `X-RateLimit-Limit`, `X-RateLimit-Remaining`
- ⚠️ Headers not present: May indicate rate limiting disabled (not critical for health checks)

### K.6.2: Rate Limit Enforcement (Optional but Recommended)

**Action (rapid requests):**

```bash
# Send 150 requests rapidly
for i in {1..150}; do
  curl -s -w "%{http_code}\n" -o /dev/null \
    https://<backend-url>/api/v1/health/live &
done
wait

# After 100 requests in 60s, should see 429 Too Many Requests
```

**Expected Result:**
- ✅ Some requests return 429 Too Many Requests (rate limited)
- ⚠️ All requests return 200: Rate limiting may be disabled (not critical)

---

## Post-Deployment: Data Isolation & Privacy Audit

### K.7.1: No Adminer or Debug Tools

**Objective:** Verify no database admin tools are exposed.

**Action:**

```bash
# Check for Adminer or similar tools
curl -s https://<backend-url>/adminer/ | head -20
curl -s https://<backend-url>/phpmyadmin/ | head -20
curl -s https://<backend-url>/debug/ | head -20
```

**Expected Result:**
- ✅ All return 404 Not Found
- ❌ Any return 200: FAIL - admin tool exposed

### K.7.2: OpenAPI Docs Hidden

**Objective:** Verify API documentation is not exposed in production.

**Action:**

```bash
curl -s https://<backend-url>/docs
curl -s https://<backend-url>/redoc
curl -s https://<backend-url>/openapi.json
```

**Expected Result:**
- ✅ All return 404 Not Found
- ❌ Any return 200: FAIL - documentation exposed (DEBUG=false should prevent this)

---

## Post-Deployment: Vercel Frontend Security Audit

### K.8.1: No Secrets in Vercel Environment

**Action (Vercel Dashboard):**

1. Go to **Project Settings → Environment Variables**
2. Review all variables:

**✅ Allowed:**
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_USE_MOCKS`
- `NEXT_PUBLIC_*` (any public variable)

**❌ Never:**
- `SECRET_KEY`
- `JWT_SECRET`
- `DATABASE_URL`
- `REDIS_URL`
- API keys or credentials

**Required Outcome:**
- ✅ No sensitive variables in Vercel
- ✅ Only NEXT_PUBLIC_* variables present

### K.8.2: Mocks Disabled in Production

**Action (Frontend code audit):**

```bash
cd pompo-frontend

# Search for mock usage
grep -r "NEXT_PUBLIC_USE_MOCKS" . --include="*.ts" --include="*.tsx" --include="*.js"

# Search for hardcoded mock data
grep -r "mock\|Mock" src/mocks --include="*.ts"
```

**Verify at runtime (browser DevTools):**

1. Open production Vercel URL
2. In DevTools Console:
   ```javascript
   console.log(process.env.NEXT_PUBLIC_USE_MOCKS)
   console.log(process.env.NEXT_PUBLIC_API_BASE_URL)
   ```

**Expected Result:**
- ✅ NEXT_PUBLIC_USE_MOCKS=false or undefined
- ✅ NEXT_PUBLIC_API_BASE_URL=https://<production-url>/api/v1
- ❌ NEXT_PUBLIC_USE_MOCKS=true: FAIL - using mocks in production

### K.8.3: CORS Origin Correct in Frontend

**Action (Browser DevTools Network tab):**

1. Open production Vercel URL (https://admin.yourdomain.com)
2. Make an API request (e.g., login)
3. Inspect Network tab → click API request
4. Check Response Headers:

```
Access-Control-Allow-Origin: https://admin.yourdomain.com
```

**Expected Result:**
- ✅ CORS origin matches your Vercel domain
- ❌ CORS origin is wildcard (*): FAIL - too permissive

---

## Security Audit Checklist (Go/No-Go Decision)

**MANDATORY:** All ✅ items must pass before production deployment.

### Critical (Block if ANY fail)

- ✅ No secrets in Git history
- ✅ No .env files tracked in Git
- ✅ DEBUG=false in production
- ✅ APP_ENV=production in Railway
- ✅ PostgreSQL is PRIVATE (not publicly accessible)
- ✅ Redis is PRIVATE (not publicly accessible)
- ✅ ALLOWED_HOSTS is restrictive (no wildcards)
- ✅ CORS_ORIGINS is restrictive (specific domain, no wildcards)
- ✅ HTTPS enforced on all API endpoints
- ✅ Unauthenticated requests blocked (401)
- ✅ Invalid tokens rejected (401)
- ✅ Valid tokens accepted (200)
- ✅ RBAC enforced (non-admin gets 403)
- ✅ OpenAPI docs hidden (404)
- ✅ No database admin tools exposed
- ✅ NEXT_PUBLIC_USE_MOCKS=false in production
- ✅ No secrets in Vercel environment variables
- ✅ Frontend CORS origin correct

### Warnings (Should fix but deployment possible with justification)

- ⚠️ Rate limiting headers present
- ⚠️ Rate limiting enforced at scale
- ⚠️ Security headers configured (HSTS, X-Frame-Options, etc.)
- ⚠️ Structured JSON logging enabled (LOG_JSON=true)

### Non-Blocking (Nice to have, future improvement)

- Comprehensive API documentation (internal only)
- Advanced monitoring dashboards
- Automated security scanning
- Penetration testing

---

## Go-Live Decision Matrix

| Scenario | Decision | Action |
|----------|----------|--------|
| All critical checks pass | ✅ GO-LIVE | Proceed with Phase L (Git checkpoint) |
| 1-2 critical checks fail | ❌ NO-GO | Fix issues, re-audit, retry |
| 3+ critical checks fail | ❌ NO-GO | Halt deployment, major investigation required |
| Warnings only | ✅ GO-LIVE | Deploy with documented waivers |

---

## Sign-Off

**Audit Date:** _______________

**Auditor Name:** _______________

**Critical Items Pass:** ☐ Yes ☐ No

**Warnings Acceptable:** ☐ Yes ☐ No

**Authorization to Deploy:** ☐ Approved ☐ Denied

**Comments:** _________________________________________________________________

---

## Next Phase

After passing security audit:

→ **Phase L: Git Checkpoint**  
→ Production system is LIVE
→ Production monitoring begins

---

**Document Version:** 1.0  
**Created:** 2026-09-01  
**Status:** DEPLOYMENT GATE (MANDATORY)
