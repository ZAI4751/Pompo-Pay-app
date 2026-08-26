"""Enterprise structured logging with Structlog."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.core.config.base import BaseAppSettings


def setup_logging(settings: BaseAppSettings) -> None:
    """Configure structlog and standard library logging."""
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_json:
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=settings.debug)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger."""
    return structlog.get_logger(name)


def bind_request_context(**kwargs: Any) -> None:
    """Bind request-scoped context variables for logging."""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_request_context() -> None:
    """Clear request-scoped context variables."""
    structlog.contextvars.clear_contextvars()
