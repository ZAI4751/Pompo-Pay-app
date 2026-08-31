"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.config.base import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.security.secrets import SecretValidator
from app.database.engine import create_engine, dispose_engine
from app.database.session import create_session_factory
from app.middleware.cors import configure_cors
from app.middleware.exception_handler import (
    UnhandledExceptionMiddleware,
    register_exception_handlers,
)
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.trusted_host import configure_trusted_hosts
from app.services.redis import RedisService
from app.workers.celery_app import create_celery_app

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    settings = app.state.settings
    setup_logging(settings)
    SecretValidator(settings).raise_if_invalid()
    create_celery_app(settings)

    logger.info(
        "application_started",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env.value,
    )

    yield

    await app.state.redis_service.close()
    await dispose_engine()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Application factory for FastAPI."""
    settings = get_settings()

    engine = create_engine(settings)
    create_session_factory()
    redis_service = RedisService(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="POMPO — Payment bridge for Malawi POS systems",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.engine = engine
    app.state.redis_service = redis_service

    register_exception_handlers(app)

    # Starlette applies middleware in reverse registration order: the LAST
    # registration becomes the OUTERMOST layer. CORS must therefore be registered
    # last, so that rate-limit (429), trusted-host (400) and unhandled-exception
    # (500) responses still carry CORS headers. Without this a browser blocks
    # those responses outright and the client cannot tell a real HTTP status from
    # an unreachable backend.
    #
    # Resulting stack, outermost first:
    #   CORS -> TrustedHost -> RequestID -> RequestLogging -> RateLimit -> app
    # RequestID sits outside RateLimit so the limiter can stamp its 429 with the
    # same request ID that appears in the logs.
    app.add_middleware(UnhandledExceptionMiddleware)
    app.add_middleware(RateLimitMiddleware, settings=settings, redis_service=redis_service)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    configure_trusted_hosts(app, settings)
    configure_cors(app, settings)

    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
