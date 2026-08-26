"""Request logging middleware with structured output."""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with method, route, status, and execution time."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start = time.perf_counter()
        request_id = getattr(request.state, "request_id", "unknown")

        response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "http_request",
            request_id=request_id,
            method=request.method,
            route=request.url.path,
            status_code=response.status_code,
            execution_time_ms=elapsed_ms,
            client_ip=request.client.host if request.client else None,
        )

        return response
