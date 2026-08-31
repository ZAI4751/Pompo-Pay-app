"""Middleware ordering and cross-origin error-surfacing tests.

These guard a specific production defect: middleware registered *outside* the
CORS layer produced responses with no CORS headers, so a browser blocked them
and the admin frontend reported every such failure as "could not reach the
backend" regardless of the real status. Any response a browser is expected to
read must carry `access-control-allow-origin`.
"""

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient

from app.middleware.exception_handler import (
    UnhandledExceptionMiddleware,
    register_exception_handlers,
)
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware

ALLOWED_ORIGIN = "http://localhost:3000"


class _StubRedis:
    """Minimal stand-in for RedisService covering the limiter's usage."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    async def increment(self, key: str, amount: int = 1) -> int:
        self._counters[key] = self._counters.get(key, 0) + amount
        return self._counters[key]

    async def expire(self, key: str, seconds: int) -> bool:
        return True


def test_cors_is_the_outermost_middleware(app: FastAPI) -> None:
    """CORS must wrap every other layer.

    Starlette treats ``user_middleware[0]`` as the outermost layer, so CORS
    sitting at index 0 is what guarantees rate-limit, trusted-host and
    unhandled-exception responses still carry CORS headers.
    """
    classes = [middleware.cls for middleware in app.user_middleware]

    assert classes[0] is CORSMiddleware, (
        f"CORSMiddleware must be outermost, found order: {[c.__name__ for c in classes]}"
    )
    assert classes.index(CORSMiddleware) < classes.index(RateLimitMiddleware)
    assert classes.index(CORSMiddleware) < classes.index(UnhandledExceptionMiddleware)


@pytest.mark.asyncio
async def test_unauthorized_response_carries_cors_headers(client: AsyncClient) -> None:
    """A 401 must be readable by the browser, not blocked as a CORS failure."""
    response = await client.post(
        "/api/v1/auth/login",
        headers={"Origin": ALLOWED_ORIGIN},
        json={"email": "nobody@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


@pytest.mark.asyncio
async def test_unhandled_exception_returns_500_with_cors_headers(
    app: FastAPI,
) -> None:
    """An unhandled exception must surface as a readable 500, not a dead socket.

    Registering an ``Exception`` handler on FastAPI installs it on Starlette's
    ServerErrorMiddleware, which wraps the CORS layer — hence
    UnhandledExceptionMiddleware handling it from inside instead.
    """

    @app.get("/api/v1/_test/boom")
    async def _boom() -> None:
        raise RuntimeError("intentional failure for test")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://localhost",
        headers={"Host": "localhost"},
    ) as ac:
        response = await ac.get("/api/v1/_test/boom", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    body = response.json()
    assert body["detail"] == "Internal server error"
    # The correlation ID lets a UI failure be matched to a server log entry.
    assert body["request_id"] != "unknown"


@pytest.mark.asyncio
async def test_rate_limited_response_carries_cors_headers() -> None:
    """A 429 must reach the browser so the client can back off deliberately.

    Mirrors main.py's registration order with a limit of 1 so the second
    request is rejected.
    """
    app = FastAPI()
    register_exception_handlers(app)

    class _Settings:
        rate_limit_requests = 1
        rate_limit_window_seconds = 60

    app.add_middleware(UnhandledExceptionMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        settings=_Settings(),
        redis_service=_StubRedis(),
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ALLOWED_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )

    @app.get("/ping")
    async def _ping() -> dict[str, bool]:
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        first = await ac.get("/ping", headers={"Origin": ALLOWED_ORIGIN})
        second = await ac.get("/ping", headers={"Origin": ALLOWED_ORIGIN})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert second.headers["retry-after"] == "60"
    # RequestID sits outside the limiter, so the 429 is traceable.
    assert second.json()["request_id"] != "unknown"


@pytest.mark.asyncio
async def test_disallowed_origin_is_not_granted_access(client: AsyncClient) -> None:
    """Widening development origins must not turn into allow-all."""
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://attacker.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.headers.get("access-control-allow-origin") != "http://attacker.example"


@pytest.mark.asyncio
async def test_rate_limit_headers_are_exposed_cross_origin(client: AsyncClient) -> None:
    """Cross-origin JS can only read these headers if they are exposed."""
    response = await client.get(
        "/api/v1/health/live",
        headers={"Origin": ALLOWED_ORIGIN},
    )

    exposed = response.headers.get("access-control-expose-headers", "")
    assert "X-Request-ID" in exposed
    assert "Retry-After" in exposed
