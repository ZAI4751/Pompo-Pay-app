"""Database connectivity tests."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.asyncio
async def test_database_connection(db_engine: AsyncEngine) -> None:
    """Verify database engine can execute a simple query."""
    async with db_engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_database_health_check(db_engine: AsyncEngine) -> None:
    """Verify database health check utility."""
    from app.database.health import check_database_health

    result = await check_database_health(db_engine)
    assert "healthy" in result
    assert "status" in result


@pytest.mark.asyncio
async def test_session_factory_creates_sessions(db_session) -> None:
    """Verify async session can execute queries."""
    result = await db_session.execute(text("SELECT 1 AS value"))
    row = result.one()
    assert row.value == 1
