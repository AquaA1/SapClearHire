import asyncio

import pytest

from app.workers.base import JobStatus
from app.workers.local import LocalAsyncWorker


@pytest.mark.asyncio
async def test_worker_job_execution_lifecycle():
    worker = LocalAsyncWorker(concurrency=1)

    async def sample_handler(payload: dict) -> dict:
        return {"processed": True, "received_id": payload.get("id")}

    worker.register_handler("test_job", sample_handler)
    await worker.start()

    try:
        job = await worker.submit_job("test_job", {"id": "doc_123"})
        assert job.status in [JobStatus.QUEUED, JobStatus.PROCESSING]

        # Allow worker loop to execute
        await asyncio.sleep(0.1)

        updated_job = await worker.get_job(job.job_id)
        assert updated_job is not None
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.result == {"processed": True, "received_id": "doc_123"}
        assert updated_job.attempts == 1
    finally:
        await worker.stop()


@pytest.mark.asyncio
async def test_worker_error_recording():
    worker = LocalAsyncWorker(concurrency=1)

    async def failing_handler(_: dict) -> dict:
        raise ValueError("Simulated parsing failure: corrupted PDF stream")

    worker.register_handler("failing_job", failing_handler)
    await worker.start()

    try:
        job = await worker.submit_job("failing_job", {"file": "corrupted.pdf"})
        await asyncio.sleep(0.1)

        updated_job = await worker.get_job(job.job_id)
        assert updated_job is not None
        assert updated_job.status == JobStatus.FAILED
        assert "Simulated parsing failure" in (updated_job.error_message or "")
    finally:
        await worker.stop()


@pytest.mark.asyncio
async def test_worker_job_cancellation():
    worker = LocalAsyncWorker(concurrency=1)
    # Do not start worker so the job remains queued
    job = await worker.submit_job("unprocessed_job", {})
    assert job.status == JobStatus.QUEUED

    cancelled = await worker.cancel_job(job.job_id)
    assert cancelled is True

    updated_job = await worker.get_job(job.job_id)
    assert updated_job is not None
    assert updated_job.status == JobStatus.FAILED
    assert "Cancelled" in (updated_job.error_message or "")
