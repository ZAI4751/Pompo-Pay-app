#!/bin/sh
# POMPO container entrypoint — api | worker | migrate
# Used by Railway and other Docker hosts. Development compose may override CMD.
set -eu

ROLE="${POMPO_CONTAINER_ROLE:-${1:-api}}"
PORT="${PORT:-8000}"

normalize_database_url() {
  if [ -z "${DATABASE_URL:-}" ]; then
    return 0
  fi
  case "$DATABASE_URL" in
    postgresql://*)
      export DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgresql://}"
      ;;
    postgres://*)
      export DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgres://}"
      ;;
  esac
}

derive_redis_urls() {
  if [ -z "${REDIS_URL:-}" ]; then
    return 0
  fi
  base="${REDIS_URL%%\?*}"
  case "$base" in
    */[0-9])
      base="${base%/*}"
      ;;
  esac
  if [ -z "${CELERY_BROKER_URL:-}" ]; then
    export CELERY_BROKER_URL="${base}/1"
  fi
  if [ -z "${CELERY_RESULT_BACKEND:-}" ]; then
    export CELERY_RESULT_BACKEND="${base}/2"
  fi
  case "$REDIS_URL" in
    */[0-9]|*\?*)
      ;;
    *)
      export REDIS_URL="${REDIS_URL}/0"
      ;;
  esac
}

run_migrations() {
  if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "[entrypoint] applying Alembic migrations..."
    alembic upgrade head
    echo "[entrypoint] migrations complete"
  else
    echo "[entrypoint] RUN_MIGRATIONS=false — skipping migrations"
  fi
}

run_admin_bootstrap() {
  if [ "${RUN_ADMIN_BOOTSTRAP:-false}" != "true" ]; then
    return 0
  fi
  if [ -z "${POMPO_ADMIN_EMAIL:-}" ] || [ -z "${POMPO_ADMIN_PASSWORD:-}" ]; then
    echo "[entrypoint] RUN_ADMIN_BOOTSTRAP=true but admin credentials missing — skipping" >&2
    return 1
  fi
  echo "[entrypoint] seeding RBAC catalog before admin bootstrap..."
  python scripts/seed_rbac.py
  echo "[entrypoint] running secure admin bootstrap..."
  python scripts/secure_bootstrap_admin.py
  echo "[entrypoint] admin bootstrap complete"
}

case "$ROLE" in
  api)
    normalize_database_url
    derive_redis_urls
    run_migrations
    run_admin_bootstrap
    echo "[entrypoint] starting FastAPI on 0.0.0.0:${PORT}"
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
    ;;
  worker)
    normalize_database_url
    derive_redis_urls
    echo "[entrypoint] starting Celery worker"
    exec celery -A app.workers.celery_app worker \
      --loglevel="${CELERY_LOG_LEVEL:-info}" \
      --concurrency="${CELERY_CONCURRENCY:-2}"
    ;;
  migrate)
    normalize_database_url
    echo "[entrypoint] migration-only job"
    exec alembic upgrade head
    ;;
  *)
    echo "[entrypoint] unknown role: ${ROLE} (expected api, worker, or migrate)" >&2
    exit 1
    ;;
esac
