"""Celery application configuration."""

from celery import Celery

from app.core.config.base import BaseAppSettings, get_settings

_celery_app: Celery | None = None


def create_celery_app(settings: BaseAppSettings | None = None) -> Celery:
    """Create and configure the Celery application."""
    global _celery_app
    if _celery_app is not None:
        return _celery_app

    if settings is None:
        settings = get_settings()

    app = Celery(
        "pompo",
        broker=settings.celery_broker_url_str,
        backend=settings.celery_result_backend_str,
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
        imports=["app.tasks.sample"],
    )

    _celery_app = app
    return app


def get_celery_app() -> Celery:
    """Return the cached Celery application instance."""
    if _celery_app is None:
        return create_celery_app()
    return _celery_app


celery_app = create_celery_app()
