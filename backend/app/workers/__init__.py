from app.core.config import get_settings
from app.workers.base import BaseBackgroundWorker, JobRecord, JobStatus
from app.workers.local import LocalAsyncWorker

_worker_instance: LocalAsyncWorker | None = None


def get_background_worker() -> BaseBackgroundWorker:
    """Returns singleton worker instance."""
    global _worker_instance
    if _worker_instance is None:
        settings = get_settings()
        _worker_instance = LocalAsyncWorker(concurrency=settings.WORKER_CONCURRENCY)
    return _worker_instance


__all__ = [
    "BaseBackgroundWorker",
    "JobRecord",
    "JobStatus",
    "LocalAsyncWorker",
    "get_background_worker",
]
