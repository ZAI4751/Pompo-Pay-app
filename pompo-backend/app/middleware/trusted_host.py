"""Trusted host middleware configuration."""

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config.base import BaseAppSettings


def configure_trusted_hosts(app: FastAPI, settings: BaseAppSettings) -> None:
    """Restrict incoming requests to trusted host headers."""
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts_list,
    )
