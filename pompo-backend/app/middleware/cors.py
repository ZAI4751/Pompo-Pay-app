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
        # Cross-origin JS can only read these if they are explicitly exposed;
        # the rate-limit trio is what lets a client back off instead of
        # misreporting a 429 as an unreachable backend.
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "Retry-After",
        ],
    )
