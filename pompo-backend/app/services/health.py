"""Health check service aggregating all subsystem checks."""

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config.base import BaseAppSettings
from app.core.logging import get_logger
from app.database.health import check_database_health
from app.schemas.health import (
    ComponentHealth,
    HealthResponse,
    LivenessResponse,
    ReadinessResponse,
)
from app.services.redis import RedisService
from app.workers.celery_app import get_celery_app

logger = get_logger(__name__)


class HealthService:
    """Orchestrates health, readiness, and liveness checks."""

    def __init__(
        self,
        settings: BaseAppSettings,
        engine: AsyncEngine,
        redis_service: RedisService,
    ) -> None:
        self._settings = settings
        self._engine = engine
        self._redis = redis_service

    async def check_health(self) -> HealthResponse:
        """Run comprehensive health checks on all subsystems."""
        start = time.perf_counter()

        db_result = await check_database_health(self._engine)
        redis_healthy = await self._redis.ping()
        celery_result = self._check_celery()
        app_healthy = True

        components = {
            "application": ComponentHealth(
                status="healthy" if app_healthy else "unhealthy",
                healthy=app_healthy,
            ),
            "database": ComponentHealth(
                status=str(db_result.get("status", "unknown")),
                healthy=bool(db_result.get("healthy", False)),
                details={"error": db_result.get("error")} if "error" in db_result else None,
            ),
            "redis": ComponentHealth(
                status="healthy" if redis_healthy else "unhealthy",
                healthy=redis_healthy,
            ),
            "celery": ComponentHealth(
                status=str(celery_result.get("status", "unknown")),
                healthy=bool(celery_result.get("healthy", False)),
                details=celery_result.get("details"),
            ),
        }

        all_healthy = all(c.healthy for c in components.values())
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        return HealthResponse(
            status="healthy" if all_healthy else "degraded",
            version=self._settings.app_version,
            environment=self._settings.app_env.value,
            components=components,
            response_time_ms=elapsed_ms,
        )

    async def check_readiness(self) -> ReadinessResponse:
        """Verify the application is ready to accept traffic."""
        db_result = await check_database_health(self._engine)
        redis_healthy = await self._redis.ping()

        db_ready = bool(db_result.get("healthy", False))
        ready = db_ready and redis_healthy

        return ReadinessResponse(
            ready=ready,
            checks={
                "database": db_ready,
                "redis": redis_healthy,
            },
        )

    def check_liveness(self) -> LivenessResponse:
        """Verify the application process is alive."""
        return LivenessResponse(alive=True)

    def _check_celery(self) -> dict[str, Any]:
        """Check Celery broker connectivity."""
        try:
            celery_app = get_celery_app()
            inspect = celery_app.control.inspect(timeout=2.0)
            ping_result = inspect.ping()
            healthy = ping_result is not None and len(ping_result) > 0
            worker_count = len(ping_result) if ping_result else 0
            return {
                "status": "healthy" if healthy else "unhealthy",
                "healthy": healthy,
                "details": {"workers": worker_count},
            }
        except Exception as exc:
            logger.warning("celery_health_check_failed", error=str(exc))
            return {
                "status": "unhealthy",
                "healthy": False,
                "details": {"error": str(exc)},
            }
