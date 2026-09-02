"""Global exception handling: handlers plus the unhandled-exception middleware."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.core.logging import get_logger
from app.integrations.errors import IntegrationAPIError

logger = get_logger(__name__)

# Starlette renamed HTTP_422_UNPROCESSABLE_ENTITY to ..._UNPROCESSABLE_CONTENT and
# emits a deprecation warning on the old name; the numeric code is stable across
# both versions.
HTTP_422_UNPROCESSABLE = 422


def _request_id(request: Request) -> str:
    """Return the current request ID, or a placeholder if none was assigned yet."""
    return getattr(request.state, "request_id", "unknown")


def _safe_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Summarise validation errors without echoing the submitted values.

    Pydantic includes the offending ``input`` in every error, which for a login
    or credential payload would put the plaintext secret into both the response
    body and the logs. Only the location, message and type are ever exposed.
    """
    return [
        {
            "loc": [str(part) for part in error.get("loc", ())],
            "msg": str(error.get("msg", "")),
            "type": str(error.get("type", "")),
        }
        for error in exc.errors()
    ]


class UnhandledExceptionMiddleware(BaseHTTPMiddleware):
    """Turn unhandled exceptions into JSON responses from inside the middleware stack.

    Registering an ``Exception`` handler on FastAPI installs it on Starlette's
    ``ServerErrorMiddleware``, which wraps the *entire* stack — including the CORS
    layer. A response produced there reaches the browser with no CORS headers, so
    the browser blocks it and a genuine 500 becomes indistinguishable from an
    unreachable server. Handling it here keeps the response inside the CORS layer.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Delegate downstream, converting any escaping exception into a 500."""
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001 - deliberate catch-all boundary
            request_id = _request_id(request)
            logger.error(
                "unhandled_exception",
                request_id=request_id,
                error=str(exc),
                path=request.url.path,
                exc_info=True,
            )
            return JSONResponse(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id,
                },
            )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI application."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        request_id = _request_id(request)
        logger.warning(
            "http_exception",
            request_id=request_id,
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "request_id": request_id,
            },
            # Preserve challenge headers such as WWW-Authenticate / Retry-After.
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = _request_id(request)
        errors = _safe_validation_errors(exc)
        logger.warning(
            "request_validation_error",
            request_id=request_id,
            path=request.url.path,
            errors=errors,
        )
        content: dict[str, Any] = {
            "detail": "Request validation failed",
            "request_id": request_id,
            "errors": errors,
        }
        if request.url.path.startswith("/api/v1/integrations/"):
            joined = " ".join(
                f"{error.get('loc', '')} {error.get('msg', '')} {error.get('type', '')}"
                for error in errors
            ).lower()
            if "currency" in joined:
                content["code"] = "unsupported_currency"
            elif "till" in joined or "merchant" in joined or "branch" in joined:
                content["code"] = "invalid_till"
            else:
                content["code"] = "invalid_amount"
        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE,
            content=content,
        )

    @app.exception_handler(IntegrationAPIError)
    async def integration_exception_handler(
        request: Request,
        exc: IntegrationAPIError,
    ) -> JSONResponse:
        request_id = _request_id(request)
        logger.warning(
            "integration_api_error",
            request_id=request_id,
            status_code=exc.status_code,
            code=exc.code,
            path=request.url.path,
        )
        headers = None
        if exc.status_code == 401:
            headers = {"WWW-Authenticate": "ApiKey"}
        elif exc.status_code == 429:
            headers = {"Retry-After": "60"}
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.message,
                "code": exc.code,
                "request_id": request_id,
            },
            headers=headers,
        )
