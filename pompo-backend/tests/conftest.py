"""Pytest configuration and shared fixtures.

Database/Redis defaults below are for the common case: running `pytest`
directly on the host machine against the Dockerized Postgres/Redis, whose
ports are published to localhost (see docker-compose.yml `ports:`).

These use `os.environ.setdefault`, not a forced assignment, deliberately:
if the invoking environment already exports these (for example, a shell
inside the `backend` container via docker-compose's `.env`, where
`DATABASE_URL` correctly points at `postgres:5432` — the Docker network
hostname, not localhost), that value is respected instead of being
clobbered. Hostnames stay correct that way, but the container `.env` also
points at the development database (`pompo`). HTTP and DB fixtures refuse
to run against `pompo`; in-container pytest still needs:

    DATABASE_URL=postgresql+asyncpg://pompo:pompo_secret@postgres:5432/pompo_test \
        pytest -v

See docs/testing.md for the full explanation and both supported invocation
modes (host vs. in-container).
"""

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("ALLOWED_HOSTS", "*")
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters-long-for-testing")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-characters-long")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://pompo:pompo_secret@localhost:5432/pompo_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

from app.core.config.base import get_settings  # noqa: E402
from app.database.engine import dispose_engine  # noqa: E402
from app.database.session import reset_session_factory  # noqa: E402
from app.main import create_app  # noqa: E402


def _assert_not_development_database(database_url: str) -> None:
    """HTTP and DB fixtures must never write to the live development database."""
    database_name = database_url.rsplit("/", 1)[-1].split("?", 1)[0]
    if database_name == "pompo":
        raise RuntimeError(
            "Refusing to run pytest against the development database 'pompo'. "
            "Point DATABASE_URL at pompo_test (see docs/testing.md Option A)."
        )


@pytest.fixture(scope="session")
def settings():
    """Provide test settings."""
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
async def app(settings):
    """Provide a fresh FastAPI application instance.

    ``create_app()`` calls ``app.database.engine.create_engine()``, which is
    a process-wide singleton guarded by "return the existing engine if one
    exists" — by design, so production doesn't reopen connections on every
    request. The FastAPI ``lifespan`` handler disposes it on shutdown, but
    the test client below uses a bare ``ASGITransport``, which does not
    invoke lifespan events. Without an explicit dispose here, every test
    after the first would silently reuse the previous test's engine — whose
    connection pool is bound to that test's (already-closed) event loop,
    since pytest-asyncio gives each test function its own loop. That
    produces `RuntimeError: ... attached to a different loop` failures.

    ``reset_session_factory()`` must be called alongside it: the session
    factory is a *second*, independently-cached singleton
    (app/database/session.py) that binds to the engine once and never
    re-checks it, so disposing the engine alone still leaves sessions bound
    to the stale one.
    """
    _assert_not_development_database(settings.database_url_str)
    get_settings.cache_clear()
    application = create_app()
    await application.state.redis_service.client.flushdb()
    yield application
    await application.state.redis_service.close()
    await dispose_engine()
    reset_session_factory()


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client with an allowed host header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://localhost",
        headers={"Host": "localhost"},
    ) as ac:
        yield ac


@pytest.fixture
async def db_engine(settings) -> AsyncGenerator[AsyncEngine, None]:
    """Provide a database engine for integration tests."""
    _assert_not_development_database(settings.database_url_str)
    engine = create_async_engine(settings.database_url_str, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for integration tests."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
