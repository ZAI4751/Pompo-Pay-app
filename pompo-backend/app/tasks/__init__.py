"""Celery tasks package."""

from app.tasks.sample import ping_task

__all__ = ["ping_task"]
