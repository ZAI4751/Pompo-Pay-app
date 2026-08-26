"""Redis-backed rate limiting middleware."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config.base import BaseAppSettings
from app.core.logging import get_logger
from app.services.redis import RedisService

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter using Redis counters."""

    EXEMPT_PATHS = {"/api/v1/health", "/api/v1/health/live", "/api/v1/health/ready"}

    def __init__(
        self,
        app,
        settings: BaseAppSettings,
        redis_service: RedisService,
    ) -> None:
        super().__init__(app)
        self._max_requests = settings.rate_limit_requests
        self._window_seconds = settings.rate_limit_window_seconds
        self._redis = redis_service

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}"

        try:
            current = await self._redis.increment(key)
            if current == 1:
                await self._redis.expire(key, self._window_seconds)

            if current > self._max_requests:
                request_id = getattr(request.state, "request_id", "unknown")
                logger.warning(
                    "rate_limit_exceeded",
                    request_id=request_id,
                    client_ip=client_ip,
                    count=current,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "request_id": request_id,
                    },
                    headers={
                        "Retry-After": str(self._window_seconds),
                        "X-RateLimit-Limit": str(self._max_requests),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            response = await call_next(request)
            remaining = max(0, self._max_requests - current)
            response.headers["X-RateLimit-Limit"] = str(self._max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response

        except Exception as exc:
            logger.error("rate_limit_check_failed", error=str(exc))
            return await call_next(request)
