"""Stable machine-readable errors for the integration API."""

from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

INTEGRATION_ERROR_STATUS: dict[str, int] = {
    "invalid_api_key": 401,
    "api_key_revoked": 401,
    "api_key_expired": 401,
    "api_key_inactive": 401,
    "insufficient_scope": 403,
    "invalid_till": 422,
    "invalid_amount": 422,
    "unsupported_currency": 422,
    "invalid_destination": 422,
    "idempotency_conflict": 409,
    "payment_not_found": 404,
    "client_not_found": 404,
    "rate_limited": 429,
    "webhook_not_configured": 422,
}


class IntegrationAPIError(Exception):
    """Raised by integration routes and dependencies."""

    def __init__(self, code: str, message: str, *, status_code: int | None = None) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code or INTEGRATION_ERROR_STATUS.get(code, 400)
        super().__init__(message)


def integration_error_response(
    request: Request, exc: IntegrationAPIError | HTTPException
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    if isinstance(exc, IntegrationAPIError):
        status_code = exc.status_code
        code = exc.code
        detail = exc.message
        headers = None
        if status_code == 401:
            headers = {"WWW-Authenticate": "ApiKey"}
        elif status_code == 429:
            headers = {"Retry-After": "60"}
    else:
        status_code = exc.status_code
        detail = str(exc.detail)
        code = "http_error"
        headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "code": code, "request_id": request_id},
        headers=headers,
    )
