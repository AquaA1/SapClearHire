import asyncio
import json
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.core.logging import logger
from app.workers.base import BaseBackgroundWorker, JobRecord, JobStatus

JobHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]


class RedisAsyncWorker(BaseBackgroundWorker):
    """
    Distributed Redis-backed asynchronous worker for multi-instance cloud deployments.
    Uses Redis Hashes for job records and Redis Lists for the FIFO work queue.
    """

    def __init__(self, redis_url: str | None = None, concurrency: int = 2):
        settings = get_settings()

        # Check SAP BTP Redis credentials
        from app.core.sap import get_sap_redis_url

        self.redis_url = redis_url or get_sap_redis_url() or settings.REDIS_URL
        self.concurrency = concurrency
        self.queue_key = "clearhire:jobs:queue"
        self.job_prefix = "clearhire:job:"
        self._handlers: dict[str, JobHandler] = {}
        self._client: Any = None
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            return self._client
        except ImportError:
            raise RuntimeError(
                "redis package is required for Redis worker support. "
                "Install it via `pip install redis` or set WORKER_BACKEND='local'."
            )

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        """Registers an async task execution function for a given job type."""
        self._handlers[job_type] = handler

    async def start(self) -> None:
        """Starts background worker polling loops."""
        if self._running:
            return
        self._running = True
        for i in range(self.concurrency):
            task = asyncio.create_task(self._worker_loop(i))
            self._tasks.append(task)
        logger.info("Redis background worker started with %d workers on %s", self.concurrency, self.redis_url)

    async def stop(self) -> None:
        """Gracefully stops background worker polling loops."""
        if not self._running:
            return
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        if self._client:
            await self._client.close()
            self._client = None
        logger.info("Redis background worker stopped")

    async def submit_job(self, job_type: str, payload: dict[str, Any]) -> JobRecord:
        """Enqueues a job record into Redis."""
        job = JobRecord(job_type=job_type, payload=payload)
        client = await self._get_client()

        job_key = f"{self.job_prefix}{job.job_id}"
        await client.set(job_key, job.model_dump_json(), ex=86400 * 7)  # 7 days retention
        await client.rpush(self.queue_key, job.job_id)
        return job

    async def get_job(self, job_id: str) -> JobRecord | None:
        """Fetches job state from Redis."""
        client = await self._get_client()
        data = await client.get(f"{self.job_prefix}{job_id}")
        if not data:
            return None
        return JobRecord.model_validate_json(data)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancels a job if still queued."""
        client = await self._get_client()
        job = await self.get_job(job_id)
        if not job or job.status != JobStatus.QUEUED:
            return False
        job.status = JobStatus.FAILED
        job.error_message = "Cancelled by user"
        job.updated_at = datetime.now(UTC)
        await client.set(f"{self.job_prefix}{job_id}", job.model_dump_json(), ex=86400 * 7)
        return True

    async def _worker_loop(self, worker_id: int) -> None:
        """Pops job IDs and executes handlers with retries."""
        logger.info("Redis worker loop %d started", worker_id)
        client = await self._get_client()

        while self._running:
            try:
                # Block for 2 seconds waiting for job IDs
                res = await client.blpop([self.queue_key], timeout=2)
                if not res:
                    continue

                _, job_id = res
                job = await self.get_job(job_id)
                if not job or job.status != JobStatus.QUEUED:
                    continue

                handler = self._handlers.get(job.job_type)
                if not handler:
                    job.status = JobStatus.FAILED
                    job.error_message = f"No handler registered for {job.job_type}"
                    job.updated_at = datetime.now(UTC)
                    await client.set(f"{self.job_prefix}{job_id}", job.model_dump_json())
                    continue

                job.status = JobStatus.PROCESSING
                job.attempts += 1
                job.updated_at = datetime.now(UTC)
                await client.set(f"{self.job_prefix}{job_id}", job.model_dump_json())

                try:
                    result = await handler(job.payload)
                    job.status = JobStatus.COMPLETED
                    job.result = result
                    job.updated_at = datetime.now(UTC)
                    await client.set(f"{self.job_prefix}{job_id}", job.model_dump_json())
                except Exception as exc:
                    logger.error("Job %s (%s) failed on attempt %d: %s", job_id, job.job_type, job.attempts, exc)
                    if job.attempts < job.max_retries:
                        job.status = JobStatus.QUEUED
                        job.error_message = str(exc)
                        job.updated_at = datetime.now(UTC)
                        await client.set(f"{self.job_prefix}{job_id}", job.model_dump_json())
                        await client.rpush(self.queue_key, job_id)
                    else:
                        job.status = JobStatus.FAILED
                        job.error_message = f"Max retries exceeded: {str(exc)}"
                        job.updated_at = datetime.now(UTC)
                        await client.set(f"{self.job_prefix}{job_id}", job.model_dump_json())

            except asyncio.CancelledError:
                break
            except Exception as exc:
                if self._running:
                    logger.warning("Redis worker loop error: %s", exc)
                    await asyncio.sleep(1)
