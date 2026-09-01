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

Both Railway services build from the monorepo root `Dockerfile` for GitHub
autodeploy (repository root is the Railway build context). The canonical
backend image for local compose remains `pompo-backend/docker/Dockerfile`.

Both services use `pompo-backend/docker/entrypoint.sh` inside the image.

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
