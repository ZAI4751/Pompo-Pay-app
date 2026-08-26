"""Health check endpoints."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.api.deps import HealthServiceDep
from app.schemas.health import HealthResponse, LivenessResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Comprehensive health check",
    description="Checks database, Redis, Celery, and application status.",
)
async def health_check(service: HealthServiceDep) -> HealthResponse | JSONResponse:
    """Return comprehensive health status of all subsystems."""
    result = await service.check_health()
    if result.status != "healthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=result.model_dump(),
        )
    return result


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Returns whether the application is ready to accept traffic.",
)
async def readiness_check(service: HealthServiceDep) -> ReadinessResponse | JSONResponse:
    """Kubernetes-style readiness probe."""
    result = await service.check_readiness()
    if not result.ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=result.model_dump(),
        )
    return result


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description="Returns whether the application process is alive.",
)
async def liveness_check(service: HealthServiceDep) -> LivenessResponse:
    """Kubernetes-style liveness probe."""
    return service.check_liveness()
