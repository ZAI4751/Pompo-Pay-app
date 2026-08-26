# Testing

Two supported ways to run the suite against the real Dockerized stack, plus
a fast in-memory subset that needs neither Docker nor a database.

## Fast path: no external services needed

`tests/test_models.py` and `tests/test_auth_service.py` (34 of the 46
tests) run against an in-memory SQLite database and need nothing running:

```bash
pytest tests/test_models.py tests/test_auth_service.py tests/test_health.py -v
```

Good for tight edit/test loops. They deliberately do **not** prove anything
about PostgreSQL-specific behavior (foreign key enforcement, for one — see
the note at the bottom of this file) — that's what the two paths below are
for.

## Full suite: `tests/test_database.py` and `tests/test_auth_api.py`

These need a real PostgreSQL (and, for the rate-limit middleware exercised
via the `client` fixture, Redis) reachable from wherever `pytest` runs.
Docker Compose does **not** provision this automatically — the two things
you need to set up once per environment are covered below.

### Option A — run inside the `backend` container (recommended)

The container is already on the Compose network and already resolves
`postgres` / `redis` by service name — no host networking, no port
conflicts, no IPv4/IPv6 resolution ambiguity to worry about. This is the
most portable option and works identically on every machine and in CI.

```bash
# one-time per environment: create the isolated test database
docker compose exec backend python scripts/create_test_db.py \
    --url postgresql+asyncpg://pompo:pompo_secret@postgres:5432/postgres \
    --database pompo_test

# apply migrations to it
docker compose exec backend env \
    DATABASE_URL=postgresql+asyncpg://pompo:pompo_secret@postgres:5432/pompo_test \
    alembic upgrade head

# run the suite
docker compose exec backend env \
    DATABASE_URL=postgresql+asyncpg://pompo:pompo_secret@postgres:5432/pompo_test \
    pytest -v
```

Note the explicit `DATABASE_URL` override on each command: the container's
own environment (from `.env` / `docker-compose.yml`) already sets
`DATABASE_URL` to the **development** database (`pompo`) — that's correct
for `backend` serving real traffic, but tests must never point at it, or a
failed test run could leave dev data in a broken state. `env VAR=value cmd`
overrides just for that one command without touching the container's actual
environment.

### Option B — run from the host machine

Works if `docker-compose.yml`'s published ports (`5432:5432`, `6379:6379`)
are actually reachable as `localhost` from your shell. This is usually true
on a native Linux/macOS Docker install; it's the first thing to suspect if
you get connection-refused errors here (see "Diagnosing connection
failures" below) — Option A sidesteps the question entirely.

```bash
# one-time per environment: create the isolated test database
python scripts/create_test_db.py \
    --url postgresql+asyncpg://pompo:pompo_secret@localhost:5432/postgres \
    --database pompo_test

# apply migrations to it
DATABASE_URL=postgresql+asyncpg://pompo:pompo_secret@localhost:5432/pompo_test \
    alembic upgrade head

# run the suite — tests/conftest.py already defaults DATABASE_URL to
# localhost:5432/pompo_test when nothing else is set, so no override needed
pytest -v
```

## How `conftest.py` picks the right DATABASE_URL

`tests/conftest.py` uses `os.environ.setdefault(...)`, not a forced
assignment:

- If nothing has already set `DATABASE_URL` in the shell (the normal case
  for Option B), it defaults to `postgresql+asyncpg://pompo:pompo_secret@
  localhost:5432/pompo_test`.
- If something already has (Option A's `env DATABASE_URL=... pytest`, or
  any other explicit override), that value wins — `setdefault` never
  clobbers an existing value.

This is why Option A's `env DATABASE_URL=...` prefix is required rather
than optional: without it, the container's own `.env`-sourced
`DATABASE_URL` (pointing at `pompo`, not `pompo_test`) is already set when
the shell starts, so `conftest.py`'s default would never even apply — you'd
be running tests against the development database.

## Diagnosing connection failures

`OSError: Multiple exceptions: [Errno 111] Connect call failed
('::1', 5432...) [Errno 111] Connect call failed ('127.0.0.1', 5432...)`
means literally nothing is listening on `localhost:5432` from wherever
`pytest` executed — not a Pompo configuration bug. Common causes, roughly
in order of likelihood:

1. **You're not actually on the Docker host's network namespace** —
   remote/VM Docker, certain WSL2 configurations, or a shell inside a
   *different* container than `backend`. Fix: use Option A.
2. **Another process already owns host port 5432** (a local Postgres
   install is common). `docker compose ps` can show `postgres` as
   `healthy` regardless, since the healthcheck runs inside the container's
   own network namespace — it doesn't prove the host port is actually
   reachable. Fix: use Option A, or stop the conflicting local service.
3. **`pompo_test` doesn't exist yet.** This produces a different error
   (`InvalidCatalogNameError`, not connection-refused) once reachability is
   fixed — run the `create_test_db.py` step above.

## Why PostgreSQL-backed tests matter, not just SQLite

`tests/test_models.py` and `tests/test_auth_service.py` run against SQLite,
which does **not** enforce foreign key constraints by default. A refresh-
token rotation ordering bug in `AuthService.refresh` (writing
`replaced_by_id` before the row it pointed to existed) passed every SQLite
test cleanly and was only caught by `tests/test_auth_api.py` running
against real PostgreSQL, which does enforce
`refresh_sessions_replaced_by_id_fkey`. The SQLite-backed suite is for fast
iteration; treat a green `test_auth_api.py` / `test_database.py` run
against real Postgres as the actual acceptance bar before considering
auth-related work done.
