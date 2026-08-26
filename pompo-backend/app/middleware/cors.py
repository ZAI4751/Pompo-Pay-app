"""CORS middleware configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config.base import BaseAppSettings


def configure_cors(app: FastAPI, settings: BaseAppSettings) -> None:
    """Configure Cross-Origin Resource Sharing."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
