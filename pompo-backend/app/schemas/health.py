"""Health check response schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    """Health status of an individual subsystem."""

    status: str
    healthy: bool
    details: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    """Comprehensive health check response."""

    status: str
    version: str
    environment: str
    components: dict[str, ComponentHealth]
    response_time_ms: float = Field(description="Total health check duration in milliseconds")


class ReadinessResponse(BaseModel):
    """Readiness probe response."""

    ready: bool
    checks: dict[str, bool]


class LivenessResponse(BaseModel):
    """Liveness probe response."""

    alive: bool
