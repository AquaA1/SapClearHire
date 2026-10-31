import uuid
from typing import Any

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


def register_default_worker_handlers(worker: BaseBackgroundWorker) -> None:
    """Registers default task handlers for PDF extraction and AI evidence extraction."""
    if not hasattr(worker, "register_handler"):
        return

    async def handle_process_document(payload: dict[str, Any]) -> dict[str, Any]:
        from app.services.document import DocumentService

        doc_id = uuid.UUID(str(payload["document_id"]))
        service = DocumentService()
        await service.process_document_extraction(doc_id)
        return {"document_id": str(doc_id), "status": "processed"}

    async def handle_extract_evidence(payload: dict[str, Any]) -> dict[str, Any]:
        from app.services.extraction import AIExtractionService

        doc_id = uuid.UUID(str(payload["document_id"]))
        run_id = (
            uuid.UUID(str(payload["run_id"]))
            if "run_id" in payload and payload["run_id"]
            else None
        )
        service = AIExtractionService()
        run, _, _ = await service.extract_and_persist(doc_id, run_id)
        return {"document_id": str(doc_id), "run_id": str(run.id), "status": "extracted"}

    worker.register_handler("process_document", handle_process_document)
    worker.register_handler("extract_evidence", handle_extract_evidence)


__all__ = [
    "BaseBackgroundWorker",
    "JobRecord",
    "JobStatus",
    "LocalAsyncWorker",
    "get_background_worker",
    "register_default_worker_handlers",
]

