"""Application middleware package."""

from app.middleware.cors import configure_cors
from app.middleware.exception_handler import register_exception_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.trusted_host import configure_trusted_hosts

__all__ = [
    "RateLimitMiddleware",
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "configure_cors",
    "configure_trusted_hosts",
    "register_exception_handlers",
]
