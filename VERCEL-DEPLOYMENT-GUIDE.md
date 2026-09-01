# POMPO Master Admin Frontend - Vercel Deployment Guide

**Deployment Target:** Master Admin Dashboard  
**Platform:** Vercel (Automatic HTTPS, Global CDN)  
**Framework:** Next.js  
**Environment:** Production  
**Date:** 2026-09-01

---

## Prerequisites

- GitHub repository connected to Vercel (OAuth authentication)
- Backend API deployed and stable (`https://<backend-url>`)
- Vercel account with deployment permissions
- Custom domain available (optional but recommended)

---

## Phase I: Vercel Project Configuration

### I.1: Create Vercel Project

**Action Required (Manual - Vercel Dashboard)**

1. **Log into Vercel:** https://vercel.com/dashboard
2. **Click "Add New..." → "Project"**
3. **Select Repository:** pompo-pay-app (or authorize if needed)
4. **Select Root Directory:** `pompo-frontend`
5. **Framework:** Next.js (should auto-detect)
6. **Project Name:** `pompo-admin-prod`
7. **Click "Create"**

### Expected Result

- Project created
- Default domain assigned: `pompo-admin-prod.vercel.app`
- Auto-deployment enabled (pushes to main branch trigger builds)

### I.2: Build & Deployment Settings

**Vercel auto-detects Next.js:**

| Setting | Value |
|---------|-------|
| Framework Preset | Next.js |
| Build Command | `npm run build` |
| Output Directory | `.next` |
| Install Command | `npm install` |

**Verify these in Vercel Dashboard → Settings → Build & Development:**

- Build Command should be: `npm run build`
- Install Command should be: `npm install`
- Output Directory should be: `.next`

### I.3: Environment Variables Configuration

**CRITICAL: All variables must be in Vercel, NOT hardcoded in code.**

1. **Go to Vercel Dashboard → Settings → Environment Variables**
2. **Add these variables:**

#### Production Environment Variables

**For Production Deployments (main branch):**

```
NEXT_PUBLIC_API_BASE_URL=https://<backend-production-url>/api/v1
NEXT_PUBLIC_USE_MOCKS=false
```

**Replace `<backend-production-url>` with actual Railway backend URL, e.g.:**
```
NEXT_PUBLIC_API_BASE_URL=https://pompo-api-prod.railway.app/api/v1
```

**CRITICAL Settings:**
- ✅ `NEXT_PUBLIC_` prefix (makes public in bundle)
- ✅ `NEXT_PUBLIC_USE_MOCKS=false` (disable mocks in production)
- ✅ Full HTTPS backend URL

#### Preview/Staging Environment Variables (Optional)

**For Preview Deployments (non-main branches):**

If you want to test staging builds against staging API:

```
NEXT_PUBLIC_API_BASE_URL=https://<backend-staging-url>/api/v1
NEXT_PUBLIC_USE_MOCKS=false
```

### I.4: Add Custom Domain (Optional but Recommended)

1. **In Vercel Dashboard → Domains**
2. **Click "Add Domain"**
3. **Enter:** `admin.yourdomain.com` (or your chosen domain)
4. **Vercel provides CNAME target** (e.g., `cname.vercel-dns.com`)

5. **In your DNS provider (Route53, Cloudflare, etc.):**
   - Add CNAME record: `admin` → `cname.vercel-dns.com`
   - Wait for DNS propagation (5-30 minutes)

6. **Vercel auto-provisions SSL/TLS** (Let's Encrypt free certificate)

### Verify Domain Configuration

```bash
# Check DNS propagation
nslookup admin.yourdomain.com

# Should return Vercel's IP addresses
```

---

## Phase I.5: Build Verification (Before Production Push)

### Local Test Build

```bash
cd pompo-frontend

# Install dependencies
npm install

# Build production bundle
npm run build

# Verify no errors
# Expected: "Ready in X seconds" + "Compiled successfully"
```

### Environment Variable Validation

```bash
# During Next.js build, verify environment is used
# Check for build warnings about missing NEXT_PUBLIC_* vars

# Search for any hardcoded API URLs
grep -r "http://localhost:3000\|http://localhost:8000" src/ --include="*.ts" --include="*.tsx"
# Should return ZERO matches (no hardcoded dev URLs)
```

---

## Phase I.6: Pre-Deployment Checklist

Before pushing to production, verify:

- ✅ Backend API is running and healthy
- ✅ Backend CORS configured to allow Vercel domain
- ✅ NEXT_PUBLIC_API_BASE_URL points to production backend
- ✅ NEXT_PUBLIC_USE_MOCKS=false
- ✅ No hardcoded API URLs in source code
- ✅ No secrets in environment variables
- ✅ Build succeeds locally

---

## Phase J: Deploy to Vercel

### J.1: Push to Main Branch

**Action (Local Terminal):**

```bash
cd /path/to/pompo

# Verify clean working directory
git status

# Create deployment commit (optional but recommended)
git add .
git commit -m "deploy: prepare production frontend deployment"

# Push to main
git push origin main
```

### Expected Result

- Vercel automatically detects push
- Deployment starts automatically
- Build begins

### J.2: Monitor Deployment in Vercel Dashboard

1. **Go to Vercel Dashboard → pompo-admin-prod project**
2. **Click "Deployments" tab**
3. **Watch build progress:**
   - ⏳ Building (npm install, npm run build)
   - ⏳ Optimizing
   - ⏳ Deploying
   - ✅ Ready (deployment complete)

4. **Expected build time:** 2-5 minutes

### J.3: Build Failure Troubleshooting

If build fails:

1. **Click the failed deployment**
2. **Check "Build Logs" for errors**
3. **Common issues:**
   - Missing dependencies: Add to `package.json`
   - TypeScript errors: Fix in source code
   - Environment variable not set: Add to Vercel
   - Missing API_BASE_URL: Verify NEXT_PUBLIC_API_BASE_URL is set

**Do NOT retry deployment blindly. Fix the root cause first.**

---

## Phase J: Verification & Smoke Tests

### J.1: Access Production Frontend

**Open in browser:**

```
https://pompo-admin-prod.vercel.app
```

Or if using custom domain:

```
https://admin.yourdomain.com
```

**Expected:** Vercel dashboard shows green checkmark, "Ready for Production"

### J.2: Visual Verification

**Action (Manual browser inspection):**

1. **Page loads** ✅
   - No "502 Bad Gateway"
   - No "Error" page
   - Vercel deployment UI loads

2. **URL bar shows HTTPS** ✅
   - Should show padlock icon
   - No security warnings

3. **No runtime errors** ✅
   - Open DevTools (F12) → Console
   - Should show no red `Error:` messages
   - API requests should show (Network tab)

### J.3: Login Flow Smoke Test

**Action (In browser):**

1. **Navigate to login page**
   - Should show email/password form
   - "Log In" button visible

2. **Enter admin credentials**
   - Email: (from Phase F bootstrap)
   - Password: (from Phase F bootstrap)

3. **Click "Log In"**

**Expected:**
- ✅ Form submission (POST to /api/v1/auth/login)
- ✅ Redirect to dashboard
- ✅ Welcome message visible
- ✅ No errors in browser console

### J.4: Dashboard Navigation Smoke Test

**Action (In browser, after login):**

Test each menu item (should load without errors):

1. **Dashboard (Home)**
   - ✅ Summary widgets load
   - ✅ No "404" or "500" errors

2. **Merchants**
   - ✅ Table loads
   - ✅ Shows merchant list (or empty state)
   - ✅ No API errors in Network tab

3. **Branches**
   - ✅ Table loads
   - ✅ No API errors

4. **Tills**
   - ✅ Table loads
   - ✅ No API errors

5. **Roles & Permissions**
   - ✅ Roles list loads
   - ✅ Shows platform-admin role
   - ✅ Permissions visible

6. **Providers**
   - ✅ Table loads
   - ✅ Empty (expected until providers added)

### J.5: Logout Flow Smoke Test

**Action (In browser):**

1. **Click user menu (top-right)**
2. **Click "Logout"**

**Expected:**
- ✅ Redirected to login page
- ✅ Session cleared (no access token stored)
- ✅ No errors in console

### J.6: Browser Network Verification

**Action (DevTools → Network tab):**

1. **Reload page while Network tab open**
2. **Filter by XHR (API requests)**

**Verify each request:**
- ✅ Uses HTTPS (green padlock)
- ✅ Points to backend URL set in NEXT_PUBLIC_API_BASE_URL
- ✅ Status 200 for successful requests
- ✅ Status 401 for auth endpoints (before login)
- ✅ CORS headers present in response

**Problematic signs:**
- ❌ 404 responses (API endpoint not found)
- ❌ 500 responses (backend error)
- ❌ CORS errors (blocked by backend CORS policy)
- ❌ Mixed HTTP/HTTPS (should all be HTTPS)

### J.7: Vercel Deployment Summary

**In Vercel Dashboard:**

1. **Deployments tab → Latest deployment**
2. **Should show:**
   - ✅ Status: "Ready"
   - ✅ Production deployment
   - ✅ Build time (e.g., "3m 42s")
   - ✅ 0 errors

3. **Click "Visit" button**
   - Should open production URL
   - Should show live dashboard

---

## Backend CORS Configuration for Vercel Frontend

### Update Backend CORS

**Critical:** Backend must allow requests from Vercel frontend domain.

**In Railway Dashboard (pompo-api-prod service):**

1. **Settings → Variables**
2. **Update CORS_ORIGINS:**

```
CORS_ORIGINS=https://pompo-admin-prod.vercel.app,https://admin.yourdomain.com
```

If using custom domain, use that instead:

```
CORS_ORIGINS=https://admin.yourdomain.com
```

**Format:** Comma-separated list of allowed origins.

**Do NOT use wildcard (*)** - Too permissive for production.

### Verify CORS Configuration

```bash
# Make API request from frontend
# DevTools Network tab → API request → Response Headers

# Should include:
Access-Control-Allow-Origin: https://admin.yourdomain.com
Access-Control-Allow-Credentials: true
```

---

## Production URL Summary

| Component | URL |
|-----------|-----|
| Master Admin Frontend | `https://pompo-admin-prod.vercel.app` |
| Custom Domain (if configured) | `https://admin.yourdomain.com` |
| Backend API | `https://pompo-api-prod.railway.app` |
| Backend Custom Domain | `https://api.yourdomain.com` (if configured) |

---

## Post-Deployment Configuration Updates

### If Backend URL Changes

1. **Update Vercel environment:**
   - Dashboard → Settings → Environment Variables
   - Change `NEXT_PUBLIC_API_BASE_URL`
   - Trigger new deployment: Push to main (or manual redeploy)

2. **Ensure backend CORS allows new URL**

### If Domain Changes

1. **Update Vercel domain configuration**
2. **Update backend CORS_ORIGINS**
3. **Ensure DNS records point to Vercel**

---

## Rollback Procedure (Emergency)

If production frontend deployment is broken:

1. **In Vercel Dashboard → Deployments tab**
2. **Find previous successful deployment**
3. **Click "..." menu → "Promote to Production"**

**This immediately redeploys the previous working version.**

Alternative: Revert Git commit and push (slower):

```bash
git revert <broken-commit-hash>
git push origin main
# Vercel redeploys automatically
```

---

## Monitoring & Logs

### View Deployment Logs

1. **Vercel Dashboard → Deployments**
2. **Click deployment → View Logs**
3. **Shows:**
   - Build logs (npm install, npm run build)
   - Deployment logs
   - Runtime errors

### Set Up Deployment Notifications

1. **Vercel Dashboard → Settings → Notifications**
2. **Add email or webhook for:**
   - Deployment success/failure
   - Team invites

---

## Performance Verification (Optional)

### Web Vitals

Vercel automatically tracks Core Web Vitals:

1. **Vercel Dashboard → Analytics**
2. **View performance metrics:**
   - Largest Contentful Paint (LCP)
   - First Input Delay (FID)
   - Cumulative Layout Shift (CLS)

### Expected Performance

- ✅ LCP < 2.5s
- ✅ FID < 100ms
- ✅ CLS < 0.1

---

## Production Frontend Checklist

**MANDATORY - All must be ✅ before declaring deployment successful:**

- ✅ Frontend loads without errors (HTTPS)
- ✅ Login page displays
- ✅ Admin login succeeds
- ✅ Dashboard displays without 404/500 errors
- ✅ Navigation works (all menu items load)
- ✅ API requests point to production backend
- ✅ No console errors (DevTools)
- ✅ CORS headers present in API responses
- ✅ NEXT_PUBLIC_USE_MOCKS=false (verified in bundle)
- ✅ No secrets in environment variables
- ✅ Custom domain resolves (if configured)
- ✅ Logout works (clears session)
- ✅ Production URL stable (page reloads work)

---

## Next Phase

After Vercel deployment verification:

→ **Phase K: Security Gate**  
→ Execute security audit checklist  
→ Verify all critical security gates pass

---

## Troubleshooting

### "502 Bad Gateway" Error

**Cause:** Frontend cannot reach backend API

**Fix:**
1. Verify NEXT_PUBLIC_API_BASE_URL is correct
2. Verify backend is running and healthy
3. Verify backend CORS allows Vercel domain
4. Check Network tab for specific error

### "CORS Policy: Cross-Origin Request Blocked"

**Cause:** Backend CORS configuration missing or wrong

**Fix:**
1. Update backend CORS_ORIGINS in Railway
2. Include Vercel deployment URL
3. Wait 1-2 minutes for change to take effect
4. Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)

### "Cannot find module" Error

**Cause:** Missing dependency in package.json

**Fix:**
1. Check error message for missing module
2. Add to package.json: `npm install <module-name>`
3. Push to main
4. Vercel redeploys with new dependency

### Build Fails Silently

**Check Vercel build logs:**
1. Vercel Dashboard → Deployments
2. Click failed deployment
3. View Build Logs
4. Look for actual error message
5. Fix and retry

---

## Document Version
1.0

## Created
2026-09-01

## Status
🟢 READY FOR DEPLOYMENT

---

**CRITICAL REMINDER:**

- ✅ Test locally before pushing to production
- ✅ Verify backend is stable before deploying frontend
- ✅ Use NEXT_PUBLIC_* prefix for all public env vars
- ✅ Do NOT commit API URLs or secrets to Git
- ✅ Backend CORS must allow Vercel domain
- ✅ Monitor deployment status until "Ready"
