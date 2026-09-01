# Railway Git deploy entrypoint for the POMPO monorepo.
#
# GitHub-connected Railway services deploy from the repository root. The
# canonical backend image for local compose and directory-scoped builds lives
# at pompo-backend/docker/Dockerfile — keep both definitions aligned.
#
# Container role (api vs worker) is selected at runtime via POMPO_CONTAINER_ROLE.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pompo-backend/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY pompo-backend/ .

RUN chmod +x /app/docker/entrypoint.sh \
    && sed -i 's/\r$//' /app/docker/entrypoint.sh \
    && adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD sh -c 'curl -f "http://localhost:${PORT:-8000}/api/v1/health/live" || exit 1'

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["api"]
