"""Database initialization script."""

import asyncio

from sqlalchemy import text

from app.core.config.base import get_settings
from app.core.logging import get_logger, setup_logging
from app.database.engine import create_engine, dispose_engine

logger = get_logger(__name__)


async def init_database() -> None:
    """Verify database connectivity on startup."""
    settings = get_settings()
    setup_logging(settings)
    engine = create_engine(settings)

    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT version()"))
            version = result.scalar_one()
            logger.info("database_connected", postgres_version=version)
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(init_database())
