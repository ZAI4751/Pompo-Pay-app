"""Outbound HTTP client for live payment-provider adapters.

This is transport infrastructure. It does not define Airtel, TNM, or bank
payloads. Unsafe methods are never retried at this layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

import httpx
from structlog.contextvars import get_contextvars

from app.core.logging import get_logger
from app.payments.providers import (
    ProviderAuthenticationError,
    ProviderDuplicate,
    ProviderError,
    ProviderInvalidRequest,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
    ProviderUnknownError,
)

logger = get_logger(__name__)

SENSITIVE_HEADER_NAMES = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "x-api-key",
        "x-auth-token",
        "api-key",
        "cookie",
        "set-cookie",
    }
)
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class ProviderTimeouts:
    connect: float = 3.0
    read: float = 10.0
    write: float = 10.0
    pool: float = 3.0

    @property
    def total(self) -> float:
        return self.connect + self.read + self.write


@dataclass(frozen=True)
class ProviderHttpResponse:
    status_code: int
    headers: dict[str, str]
    text: str
    json_body: dict[str, Any] | list[Any] | None
    elapsed_ms: int


@dataclass(frozen=True)
class ProviderHttpRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    retry_safe: bool = False


def _host_and_path(url: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    return parsed.hostname or "", parsed.path or "/"


def _safe_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADER_NAMES:
            redacted[key] = "redacted"
        else:
            redacted[key] = value
    return redacted


def translate_http_status(status_code: int) -> ProviderError:
    if status_code in {401, 403}:
        return ProviderAuthenticationError()
    if status_code in {408, 504}:
        return ProviderTimeout()
    if status_code == 429:
        return ProviderRateLimited()
    if status_code == 409:
        return ProviderDuplicate()
    if status_code in {400, 404, 422}:
        return ProviderInvalidRequest()
    if status_code >= 500:
        return ProviderUnavailable()
    return ProviderUnknownError(f"Provider returned HTTP {status_code}")


class ProviderHttpClient:
    def __init__(
        self,
        *,
        timeouts: ProviderTimeouts | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        max_connections: int = 20,
        max_keepalive: int = 10,
    ) -> None:
        self._timeouts = timeouts or ProviderTimeouts()
        timeout = httpx.Timeout(
            connect=self._timeouts.connect,
            read=self._timeouts.read,
            write=self._timeouts.write,
            pool=self._timeouts.pool,
        )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive,
            ),
            transport=transport,
            follow_redirects=False,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def send(self, request: ProviderHttpRequest) -> ProviderHttpResponse:
        method = request.method.upper()
        if method in UNSAFE_METHODS and request.retry_safe:
            raise ProviderInvalidRequest("Unsafe provider methods cannot be marked retry-safe")
        headers = dict(request.headers)
        correlation_id = get_contextvars().get("request_id")
        if correlation_id and "X-Request-ID" not in headers:
            headers["X-Request-ID"] = str(correlation_id)
        host, path = _host_and_path(request.url)
        logger.info(
            "provider_http_request",
            method=method,
            host=host,
            path=path,
            correlation_id=headers.get("X-Request-ID"),
            retry_safe=request.retry_safe,
            headers=_safe_headers(headers),
        )
        try:
            response = await self._client.request(
                method,
                request.url,
                headers=headers,
                json=request.json_body,
            )
        except httpx.TimeoutException as exc:
            logger.warning("provider_http_timeout", method=method, host=host, path=path)
            raise ProviderTimeout() from exc
        except httpx.ConnectError as exc:
            logger.warning("provider_http_unavailable", method=method, host=host, path=path)
            raise ProviderUnavailable("Provider connection failed") from exc
        except httpx.HTTPError as exc:
            logger.warning("provider_http_error", method=method, host=host, path=path)
            raise ProviderUnavailable("Provider HTTP transport failed") from exc

        json_body: dict[str, Any] | list[Any] | None
        try:
            json_body = response.json() if response.content else None
        except ValueError:
            json_body = None
            if response.content:
                logger.warning(
                    "provider_http_malformed_response",
                    method=method,
                    host=host,
                    path=path,
                    status_code=response.status_code,
                )
                raise ProviderInvalidRequest("Provider returned a malformed response") from None

        elapsed = getattr(response, "_elapsed", None)
        elapsed_ms = int(elapsed.total_seconds() * 1000) if elapsed is not None else 0
        logger.info(
            "provider_http_response",
            method=method,
            host=host,
            path=path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
            correlation_id=headers.get("X-Request-ID"),
        )
        return ProviderHttpResponse(
            status_code=response.status_code,
            headers={key: value for key, value in response.headers.items()},
            text=response.text,
            json_body=json_body,
            elapsed_ms=elapsed_ms,
        )

    async def send_or_raise(self, request: ProviderHttpRequest) -> ProviderHttpResponse:
        response = await self.send(request)
        if response.status_code >= 400:
            raise translate_http_status(response.status_code)
        return response
