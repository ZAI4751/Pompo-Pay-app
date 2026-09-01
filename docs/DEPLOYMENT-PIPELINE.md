# POMPO Deployment Pipeline

GitHub is the source of truth for production deployments.

| Target | Platform | Root directory | Production branch |
|--------|----------|----------------|-------------------|
| Master Admin | Vercel (`pompo-team/pompo-pay-app`) | `pompo-frontend` | `Main-Pompo-branch` |
| API | Railway (`pompo-production` / `pompo-api`) | `pompo-backend` | `Main-Pompo-branch` |
| Worker | Railway (`pompo-production` / `pompo-worker`) | `pompo-backend` | `Main-Pompo-branch` |

## Flow

```text
push/merge to Main-Pompo-branch
        │
        ▼
   GitHub Actions CI
   (backend tests + Docker build, frontend typecheck/lint/build)
        │
        ├──────────────┬──────────────┐
        ▼              ▼              ▼
     Vercel        Railway API    Railway worker
  pompo-frontend   Docker image   Docker image
```

## Backend container roles

Both Railway services build from `pompo-backend/docker/Dockerfile` and
`pompo-backend/docker/entrypoint.sh`.

| Service | `POMPO_CONTAINER_ROLE` | `RUN_MIGRATIONS` |
|---------|------------------------|------------------|
| `pompo-api` | `api` | `true` |
| `pompo-worker` | `worker` | `false` |

Migrations run via `alembic upgrade head` in the API container only. The
worker never applies schema changes.

## Public endpoints

- Frontend: https://pompo-pay-app.vercel.app
- API: https://pompo-api-production.up.railway.app/api/v1

## CI workflow

`.github/workflows/ci.yml` runs on pushes and pull requests to
`Main-Pompo-branch`.
