"""Database health check utilities."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.logging import get_logger

logger = get_logger(__name__)


async def check_database_health(engine: AsyncEngine) -> dict[str, str | bool]:
    """Verify database connectivity by executing a simple query."""
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            value = result.scalar_one()
            healthy = value == 1
            return {"status": "healthy" if healthy else "unhealthy", "healthy": healthy}
    except Exception as exc:
        logger.error("database_health_check_failed", error=str(exc))
        return {"status": "unhealthy", "healthy": False, "error": str(exc)}
