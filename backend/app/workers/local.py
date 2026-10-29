import asyncio
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from app.core.logging import logger
from app.workers.base import BaseBackgroundWorker, JobRecord, JobStatus

JobHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]


class LocalAsyncWorker(BaseBackgroundWorker):
    """
    In-memory async background worker for local development and testing.
    Provides non-blocking job execution with status tracking and error handling.
    """

    def __init__(self, concurrency: int = 2):
        self.concurrency = concurrency
        self._jobs: dict[str, JobRecord] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._handlers: dict[str, JobHandler] = {}
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        """Register a processing function for a given job type."""
        self._handlers[job_type] = handler

    async def start(self) -> None:
        """Start worker loop tasks."""
        if self._running:
            return
        self._running = True
        for i in range(self.concurrency):
            task = asyncio.create_task(self._worker_loop(i))
            self._tasks.append(task)
        logger.info("Local background worker started with %d workers", self.concurrency)

    async def stop(self) -> None:
        """Gracefully stop worker loop tasks."""
        if not self._running:
            return
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Local background worker stopped")

    async def submit_job(self, job_type: str, payload: dict[str, Any]) -> JobRecord:
        """Submits a job to the local queue."""
        job = JobRecord(job_type=job_type, payload=payload)
        self._jobs[job.job_id] = job
        await self._queue.put(job.job_id)
        return job

    async def get_job(self, job_id: str) -> JobRecord | None:
        """Returns the current state of a job."""
        return self._jobs.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancels a job if it is still queued."""
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.QUEUED:
            job.status = JobStatus.FAILED
            job.error_message = "Cancelled by user"
            job.updated_at = datetime.now(UTC)
            return True
        return False

    async def _worker_loop(self, worker_id: int) -> None:
        """Internal consumption loop."""
        while self._running:
            try:
                job_id = await self._queue.get()
                job = self._jobs.get(job_id)
                if not job or job.status != JobStatus.QUEUED:
                    self._queue.task_done()
                    continue

                job.status = JobStatus.PROCESSING
                job.updated_at = datetime.now(UTC)
                job.attempts += 1

                handler = self._handlers.get(job.job_type)
                if not handler:
                    job.status = JobStatus.FAILED
                    job.error_message = f"No handler registered for job type: {job.job_type}"
                    job.updated_at = datetime.now(UTC)
                    self._queue.task_done()
                    continue

                try:
                    result = await handler(job.payload)
                    job.status = JobStatus.COMPLETED
                    job.result = result
                except Exception as exc:
                    logger.exception(
                        "Worker %d failed processing job %s: %s", worker_id, job_id, str(exc)
                    )
                    job.status = JobStatus.FAILED
                    job.error_message = str(exc)
                finally:
                    job.updated_at = datetime.now(UTC)
                    self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Worker %d loop encountered unexpected error: %s", worker_id, str(e))
