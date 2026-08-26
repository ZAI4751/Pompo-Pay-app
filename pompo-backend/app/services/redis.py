"""Redis service with connection pooling."""

from redis.asyncio import ConnectionPool, Redis

from app.core.config.base import BaseAppSettings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisService:
    """Async Redis client with connection pooling."""

    def __init__(self, settings: BaseAppSettings) -> None:
        self._pool: ConnectionPool = ConnectionPool.from_url(
            settings.redis_url_str,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
        )
        self._client: Redis = Redis(connection_pool=self._pool)

    @property
    def client(self) -> Redis:
        """Return the underlying Redis client."""
        return self._client

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            response = await self._client.ping()
            return response is True
        except Exception as exc:
            logger.error("redis_ping_failed", error=str(exc))
            return False

    async def get(self, key: str) -> str | None:
        """Get a value by key."""
        return await self._client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        expire_seconds: int | None = None,
    ) -> bool:
        """Set a key-value pair with optional expiry."""
        result = await self._client.set(key, value, ex=expire_seconds)
        return result is True

    async def delete(self, key: str) -> int:
        """Delete a key."""
        return await self._client.delete(key)

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        return await self._client.incrby(key, amount)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry on a key."""
        return await self._client.expire(key, seconds)

    async def close(self) -> None:
        """Close the Redis connection pool."""
        await self._client.aclose()
        await self._pool.aclose()
        logger.info("redis_connection_closed")
