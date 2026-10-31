import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger, setup_logging
from app.db.models.document import Document, ExtractionRun
from app.db.models.enums import DocumentProcessingStatus
from app.db.session import close_db_engine, get_session_factory
from app.repositories.domain import DocumentRepository, ExtractionRepository
from app.workers import get_background_worker, register_default_worker_handlers


async def recover_stale_processing_jobs(
    session: AsyncSession | None = None,
    enqueue: bool = True,
) -> dict[str, int]:
    """
    Safely recovers in-flight document processing and extraction runs interrupted by server restart.
    - QUEUED jobs remain queued and are picked up by the worker.
    - PROCESSING jobs interrupted mid-flight are safely recovered to QUEUED and re-enqueued (up to max retries).
    - COMPLETED jobs are untouched and never reprocessed.
    - FAILED jobs remain failed unless explicitly retried.
    - Development reload (uvicorn --reload) does not fail pending jobs.
    """
    recovery_stats = {
        "documents_queued": 0,
        "documents_recovered": 0,
        "documents_failed": 0,
        "runs_queued": 0,
        "runs_recovered": 0,
        "runs_failed": 0,
    }
    docs_to_enqueue: list[uuid.UUID] = []
    runs_to_enqueue: list[tuple[uuid.UUID, uuid.UUID]] = []

    try:

        async def _execute_recovery(s: AsyncSession) -> None:
            now = datetime.now(UTC)

            # 1. Recover Documents
            doc_stmt = select(Document).where(
                Document.processing_status.in_(
                    [DocumentProcessingStatus.QUEUED, DocumentProcessingStatus.PROCESSING]
                )
            )
            doc_res = await s.execute(doc_stmt)
            documents = doc_res.scalars().all()

            for doc in documents:
                file_exists = Path(doc.file_path).exists() if doc.file_path else False

                if not file_exists:
                    doc.processing_status = DocumentProcessingStatus.FAILED
                    doc.processing_error = {
                        "code": "FILE_NOT_FOUND",
                        "message": f"Resume file {doc.file_name} not found on disk.",
                    }
                    recovery_stats["documents_failed"] += 1
                    continue

                if doc.processing_status == DocumentProcessingStatus.QUEUED:
                    # Stays QUEUED, schedule for processing
                    docs_to_enqueue.append(doc.id)
                    recovery_stats["documents_queued"] += 1
                elif doc.processing_status == DocumentProcessingStatus.PROCESSING:
                    # Interrupted mid-extraction
                    err_meta = doc.processing_error or {}
                    attempts = (
                        err_meta.get("recovery_attempts", 0)
                        if isinstance(err_meta, dict)
                        else 0
                    )
                    if attempts < 3:
                        doc.processing_status = DocumentProcessingStatus.QUEUED
                        doc.processing_error = {
                            "recovery_attempts": attempts + 1,
                            "last_recovered_at": now.isoformat(),
                            "message": "Recovered from server interruption; queued for processing.",
                        }
                        docs_to_enqueue.append(doc.id)
                        recovery_stats["documents_recovered"] += 1
                    else:
                        doc.processing_status = DocumentProcessingStatus.FAILED
                        doc.processing_error = {
                            "code": "MAX_RETRIES_EXCEEDED",
                            "message": "Document processing exceeded maximum recovery attempts.",
                        }
                        recovery_stats["documents_failed"] += 1

            # 2. Recover Extraction Runs
            ext_stmt = select(ExtractionRun).where(
                ExtractionRun.status.in_(
                    [DocumentProcessingStatus.QUEUED, DocumentProcessingStatus.PROCESSING]
                )
            )
            ext_res = await s.execute(ext_stmt)
            runs = ext_res.scalars().all()

            ext_repo = ExtractionRepository(s)
            doc_repo = DocumentRepository(s)

            for run in runs:
                parent_doc = await doc_repo.get_by_id(run.document_id)
                if not parent_doc or parent_doc.processing_status == DocumentProcessingStatus.FAILED:
                    run.status = DocumentProcessingStatus.FAILED
                    run.error_message = "Parent document processing failed or document missing."
                    run.completed_at = now
                    recovery_stats["runs_failed"] += 1
                    continue

                if parent_doc.processing_status == DocumentProcessingStatus.COMPLETED:
                    if run.status == DocumentProcessingStatus.QUEUED:
                        runs_to_enqueue.append((run.id, run.document_id))
                        recovery_stats["runs_queued"] += 1
                    elif run.status == DocumentProcessingStatus.PROCESSING:
                        raw_meta = run.raw_output or {}
                        attempts = (
                            raw_meta.get("recovery_attempts", 0)
                            if isinstance(raw_meta, dict)
                            else 0
                        )
                        if attempts < 3:
                            # Purge partial skills and evidence from this interrupted run to avoid duplicates
                            await ext_repo.clear_run_artifacts(run.id)
                            run.status = DocumentProcessingStatus.QUEUED
                            run.error_message = None
                            run.raw_output = {
                                "recovery_attempts": attempts + 1,
                                "last_recovered_at": now.isoformat(),
                            }
                            runs_to_enqueue.append((run.id, run.document_id))
                            recovery_stats["runs_recovered"] += 1
                        else:
                            run.status = DocumentProcessingStatus.FAILED
                            run.error_message = "Extraction run exceeded maximum recovery attempts."
                            run.completed_at = now
                            recovery_stats["runs_failed"] += 1
                else:
                    # Parent document is still QUEUED or recovering; run stays QUEUED
                    recovery_stats["runs_queued"] += 1

            await s.commit()

        if session is not None:
            await _execute_recovery(session)
        else:
            session_factory = get_session_factory()
            async with session_factory() as s:
                await _execute_recovery(s)

        # Enqueue jobs to background worker if requested
        if enqueue and (docs_to_enqueue or runs_to_enqueue):
            worker = get_background_worker()
            for d_id in docs_to_enqueue:
                await worker.submit_job("process_document", {"document_id": str(d_id)})
            for r_id, d_id in runs_to_enqueue:
                await worker.submit_job(
                    "extract_evidence", {"document_id": str(d_id), "run_id": str(r_id)}
                )

        total_active = len(docs_to_enqueue) + len(runs_to_enqueue)
        if (
            total_active > 0
            or recovery_stats["documents_failed"] > 0
            or recovery_stats["runs_failed"] > 0
        ):
            logger.info("Startup recovery completed: %s", recovery_stats)

    except Exception as exc:
        logger.error("Failed to recover stale processing jobs on startup: %s", str(exc))

    return recovery_stats


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifespan manager for initialization and graceful teardown."""
    settings = get_settings()
    setup_logging(environment=settings.ENVIRONMENT)
    logger.info(
        "Starting %s v%s in [%s] mode",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )

    # Start local background worker with default handlers
    worker = get_background_worker()
    register_default_worker_handlers(worker)
    if hasattr(worker, "start"):
        await worker.start()

    # Recover stale processing jobs interrupted by server restart and enqueue them
    await recover_stale_processing_jobs(enqueue=True)

    yield

    # Teardown background worker & database connections
    if hasattr(worker, "stop"):
        await worker.stop()
    await close_db_engine()
    logger.info("Graceful shutdown completed for %s", settings.PROJECT_NAME)



def create_application() -> FastAPI:
    """Factory function to build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "ClearHire — Hiring Evidence Transparency Platform Backend.\n\n"
            "Guarantees that relevant candidate evidence is never silently missed during screening. "
            "Maps structured claims directly to versioned criteria with source grounding and human oversight."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    register_exception_handlers(app)

    # Route Registration
    app.include_router(api_router)

    return app


app = create_application()
