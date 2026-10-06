# POMPO Backend

Enterprise-grade backend foundation for **POMPO** — a payment bridge built for Malawi that connects retail POS systems to Airtel Money, TNM Mpamba, and bank payment rails.

POMPO is **not** an e-money platform. It never stores customer funds. It only routes payment requests and monitors settlements.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.12 |
| Framework | FastAPI |
| Database | PostgreSQL + SQLAlchemy 2.0 Async |
| Migrations | Alembic |
| Cache / Broker | Redis |
| Task Queue | Celery |
| Validation | Pydantic V2 |
| Auth (foundation) | JWT + bcrypt |
| Logging | Structlog |
| Testing | Pytest |
| Containers | Docker + Docker Compose |

## Quick Start with Docker Compose

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2)
- Git

### 1. Clone and configure

```bash
git clone <repository-url> pompo-backend
cd pompo-backend
cp .env.example .env
```

Review `.env` and update secrets before deploying to production.

### 2. Start all services

```bash
docker compose up --build
```

This starts:

| Service | URL | Description |
|---------|-----|-------------|
| **Backend API** | http://localhost:8000 | FastAPI application |
| **API Docs** | http://localhost:8000/docs | Swagger UI (development) |
| **Adminer** | http://localhost:8080 | Database admin UI |
| **PostgreSQL** | localhost:5432 | Database |
| **Redis** | localhost:6379 | Cache and Celery broker |

### 3. Verify the stack

```bash
# Liveness probe
curl http://localhost:8000/api/v1/health/live

# Readiness probe
curl http://localhost:8000/api/v1/health/ready

# Full health check (database, Redis, Celery, application)
curl http://localhost:8000/api/v1/health
```

Expected liveness response:

```json
{"alive": true}
```

### 4. Stop services

```bash
docker compose down
```

To remove persistent volumes:

```bash
docker compose down -v
```

## Local Development (without Docker)

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Redis 7+

### Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Update `.env` with local connection strings:

```
DATABASE_URL=postgresql+asyncpg://pompo:pompo_secret@localhost:5432/pompo
REDIS_URL=redis://localhost:6379/0
```

### Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Celery worker

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

### Run tests

```bash
pytest -v
```

With coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

## Project Structure

```
pompo-backend/
├── app/
│   ├── main.py                 # Application entry point
│   ├── api/
│   │   ├── deps.py             # Dependency injection providers
│   │   └── v1/
│   │       ├── router.py       # V1 route aggregation
│   │       ├── health.py       # Health check endpoints
│   │       ├── organization.py # Merchant/branch administration
│   │       └── payments.py     # Payment-core endpoints
│   ├── core/
│   │   ├── config/             # Environment settings (dev/test/prod)
│   │   ├── security/           # JWT, password hashing, secrets
│   │   └── logging.py          # Structlog configuration
│   ├── database/
│   │   ├── engine.py           # Async SQLAlchemy engine
│   │   ├── session.py          # Session factory + DI
│   │   └── health.py           # Database health check
│   ├── middleware/             # Request ID, logging, CORS, rate limit
│   ├── models/                 # SQLAlchemy models (future)
│   ├── repositories/           # Data access layer
│   ├── schemas/                # Pydantic request/response models
│   ├── services/               # Business logic layer
│   ├── payments/               # Payment domain (future)
│   ├── providers/              # Payment provider integrations (future)
│   ├── authentication/         # Auth module (future)
│   ├── permissions/            # Authorization (future)
│   ├── events/                 # Domain events (future)
│   ├── websockets/             # WebSocket handlers (future)
│   ├── tasks/                  # Celery task definitions
│   └── workers/                # Celery application config
├── tests/
│   ├── conftest.py             # Pytest fixtures
│   ├── test_health.py          # Health endpoint tests
│   └── test_database.py        # Database connectivity tests
├── migrations/                 # Alembic migration scripts
├── scripts/                    # Utility scripts
├── docs/                       # Architecture documentation
├── docker/
│   └── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
└── pyproject.toml
```

## Architecture Overview

The project follows **Clean Architecture** mixed with **Domain Driven Design**:

```
Routes → Services → Repositories → Database
```

- **Routes** handle HTTP only — no business logic
- **Services** contain business logic and orchestration
- **Repositories** abstract data access
- **Models** define database entities
- **Schemas** define API contracts

All dependencies are injected via FastAPI's `Depends()` system.

See [docs/architecture.md](docs/architecture.md) for detailed diagrams.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Comprehensive health check |
| GET | `/api/v1/health/ready` | Readiness probe |
| GET | `/api/v1/health/live` | Liveness probe |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment profile | `development` |
| `SECRET_KEY` | Application secret (min 32 chars) | — |
| `DATABASE_URL` | PostgreSQL connection string | — |
| `REDIS_URL` | Redis connection string | — |
| `CELERY_BROKER_URL` | Celery broker URL | — |
| `JWT_SECRET_KEY` | JWT signing key (min 32 chars) | — |
| `SANDBOX_PAYMENTS_ENABLED` | Enable deterministic demo-provider flows | `false`; local `.env.example` opts in |
| `LOG_LEVEL` | Logging level | `INFO` |
| `RATE_LIMIT_REQUESTS` | Max requests per window | `100` |

See `.env.example` for the full list.

## Demo / sandbox payments

The payment sandbox uses the same provider adapter, payment state machine,
attempt records, idempotency handling, and signed webhook processing as other
payment rails. Catalog entries are explicitly named **POMPO Demo/Sandbox**;
they are not Airtel Money, TNM Mpamba, or bank integrations.

`SANDBOX_PAYMENTS_ENABLED` defaults to `false` in every environment except
testing. The local `.env.example` explicitly opts development into simulation;
demo, staging, and production remain disabled unless an operator opts in.
Even when enabled, a sandbox provider must be named on each payment request in
every environment. Automatic provider selection never falls back to a demo
rail. A sandbox rail cannot be relabeled or moved to a live environment.
Airtel/TNM/bank adapters continue to reject payments until their provider
contract and required credentials are actually configured.

For an explicitly approved Render production demo, keep `APP_ENV=production`
and temporarily set `SANDBOX_PAYMENTS_ENABLED=true`; do not switch the public
service to the less restrictive demo profile. Seed provider rows by running
`python scripts/seed_providers.py` in the API service after setting the flag.
That command refuses production seeding unless the flag is true. For signed
pending-payment callbacks, store a random secret in Render as
`POMPO_DEMO_WEBHOOK_SECRET` and set
`PROVIDER_SIMULATED_PENDING_WEBHOOK_SECRET_REF=POMPO_DEMO_WEBHOOK_SECRET`.
Never put the secret value in source control or logs. Sandbox callbacks are
processed inline through the same verified state machine and do not require a
Celery worker; other webhook jobs remain on the existing worker path.

For an end-to-end success demonstration, seed the non-production provider
catalog and demo environment, create or display a POMPO merchant QR, then pay
it using **POMPO Demo Mobile Money (Sandbox)**. The payment is created and
processed by the shared provider adapter and shown as successful with its
normal POMPO payment reference. The adapter outcomes `simulated_pending`,
`simulated_failure`, and `simulated_timeout` provide deterministic lifecycle
tests. A pending payment becomes successful only through the existing
signature-verified provider webhook/status-processing path; it is not marked
paid by directly editing the transaction.

## Middleware

Every request passes through:

1. **Request ID** — unique `X-Request-ID` header for tracing
2. **Request Logging** — structured log with method, route, status, execution time
3. **CORS** — configurable cross-origin policy
4. **Trusted Hosts** — host header validation
5. **Rate Limiting** — Redis-backed sliding window limiter

## Health Checks

The `/api/v1/health` endpoint verifies:

- **Application** — process is running
- **Database** — PostgreSQL connectivity (`SELECT 1`)
- **Redis** — ping response
- **Celery** — worker availability

## Database Migrations

```bash
# Generate a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

## License

Proprietary — POMPO Engineering
