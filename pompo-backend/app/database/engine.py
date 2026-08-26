"""Async SQLAlchemy engine factory."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config.base import BaseAppSettings
from app.core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None


def create_engine(settings: BaseAppSettings) -> AsyncEngine:
    """Create and cache the async database engine with connection pooling."""
    global _engine
    if _engine is not None:
        return _engine

    _engine = create_async_engine(
        settings.database_url_str,
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_pre_ping=True,
    )
    logger.info(
        "database_engine_created",
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
    return _engine


def get_engine() -> AsyncEngine:
    """Return the cached async engine, raising if not initialized."""
    if _engine is None:
        raise RuntimeError("Database engine has not been initialized")
    return _engine


async def dispose_engine() -> None:
    """Dispose the engine and release all connections."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("database_engine_disposed")
