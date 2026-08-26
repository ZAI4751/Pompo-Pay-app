"""Async session factory and dependency injection."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.engine import get_engine

_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create and cache the async session factory."""
    global _session_factory
    if _session_factory is not None:
        return _session_factory

    _session_factory = async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    return _session_factory


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the cached session factory."""
    if _session_factory is None:
        return create_session_factory()
    return _session_factory


def reset_session_factory() -> None:
    """Clear the cached session factory.

    Mirrors ``app.database.engine.dispose_engine()`` — the two must be
    reset together. ``create_session_factory()`` binds to whatever
    ``get_engine()`` returns at the moment it's first called and then never
    re-checks it. If the engine is later disposed and replaced (as the test
    suite does between tests, since a bare ASGI test client doesn't trigger
    FastAPI's lifespan shutdown) without also clearing this, every session
    created afterward stays bound to the disposed, stale engine instead of
    the new one — surfacing as "attached to a different loop" errors under
    pytest-asyncio's per-test event loops. In a real running process this
    never comes up: the engine is created once at startup and only disposed
    at shutdown, so there's nothing to go stale.
    """
    global _session_factory
    _session_factory = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
