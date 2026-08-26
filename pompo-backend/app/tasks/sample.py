"""Sample Celery task for worker verification."""

from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.sample.ping_task", bind=True)
def ping_task(self) -> dict[str, str]:
    """Simple ping task to verify Celery worker connectivity."""
    logger.info("ping_task_executed", task_id=self.request.id)
    return {"status": "pong", "task_id": self.request.id}
