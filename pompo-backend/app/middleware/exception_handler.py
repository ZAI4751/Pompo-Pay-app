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

GENERIC_VALIDATION_DETAIL = "Request validation failed"

_FIELD_LABELS = {
    "email": "Email address",
    "password": "Password",
    "full_name": "Full name",
    "phone": "Phone number",
    "new_password": "Password",
    "current_password": "Current password",
}


def _field_name(loc: list[Any] | tuple[Any, ...] | None) -> str:
    if not loc:
        return ""
    parts = [str(part) for part in loc if str(part) not in {"body", "query", "path", "header"}]
    return parts[-1] if parts else ""


def user_facing_validation_message(error: dict[str, Any]) -> str:
    """Map a single safe Pydantic error to a user-correctable reason.

    Does not include submitted values. Unknown fields stay generic so this
    cannot leak internal model structure.
    """
    field = _field_name(error.get("loc"))
    err_type = str(error.get("type") or "")
    msg = str(error.get("msg") or "").lower()
    label = _FIELD_LABELS.get(field, "")

    if err_type == "missing":
        if label:
            return f"{label} is required"
        return "Required field missing"
    if field == "email" or "email" in err_type or "email address" in msg:
        return "Email address is invalid"
    if field in {"password", "new_password"}:
        return "Password does not meet requirements"
    if field == "phone":
        return "Phone number is invalid"
    if field == "full_name" or "full_name is required" in msg:
        return "Full name is required"
    if label:
        return f"{label} is invalid"
    return GENERIC_VALIDATION_DETAIL


def user_facing_validation_detail(errors: list[dict[str, Any]]) -> str:
    """Join unique field-level reasons for the top-level ``detail`` string.

    Clients render ``detail`` directly. The structured ``errors`` array remains
    the machine-readable contract; this only makes the summary human-usable.
    """
    messages: list[str] = []
    seen: set[str] = set()
    for error in errors:
        message = user_facing_validation_message(error)
        if message in seen:
            continue
        seen.add(message)
        messages.append(message)
    return ". ".join(messages) if messages else GENERIC_VALIDATION_DETAIL


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
            "detail": user_facing_validation_detail(errors),
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
            elif "merchant" in joined:
                content["code"] = "invalid_merchant_context"
            elif "branch" in joined:
                content["code"] = "invalid_branch_context"
            elif "till" in joined:
                content["code"] = "invalid_till_context"
            elif "amount" in joined:
                content["code"] = "invalid_amount"
            else:
                content["code"] = "invalid_request"
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
