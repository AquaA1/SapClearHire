import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Lifecycle status of an asynchronous background document processing job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobRecord(BaseModel):
    """State record for a background processing job."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_type: str = Field(..., description="Type of work, e.g. 'extract_resume_evidence'")
    status: JobStatus = Field(default=JobStatus.QUEUED)
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error_message: str | None = None
    attempts: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BaseBackgroundWorker(ABC):
    """
    Abstract interface for background document and claim processing.
    Decouples HTTP requests from expensive PDF parsing and LLM calls.
    """

    @abstractmethod
    async def submit_job(self, job_type: str, payload: dict[str, Any]) -> JobRecord:
        """Enqueue a new processing task."""
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> JobRecord | None:
        """Retrieve the status and results of a job."""
        pass

    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job if not already processing."""
        pass
