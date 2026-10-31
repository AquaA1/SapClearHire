from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger, setup_logging
from app.db.models.document import Document, ExtractionRun
from app.db.models.enums import DocumentProcessingStatus
from app.db.session import close_db_engine, get_session_factory
from app.workers import get_background_worker


async def recover_stale_processing_jobs(session: AsyncSession | None = None) -> None:
    """
    Recovers in-flight document processing and extraction runs interrupted by server restart.
    Marks stale QUEUED and PROCESSING jobs as FAILED to prevent indefinite hangs.
    """
    try:

        async def _execute_recovery(s: AsyncSession) -> None:
            doc_stmt = (
                update(Document)
                .where(
                    Document.processing_status.in_(
                        [DocumentProcessingStatus.QUEUED, DocumentProcessingStatus.PROCESSING]
                    )
                )
                .values(
                    processing_status=DocumentProcessingStatus.FAILED,
                    processing_error={
                        "code": "SERVER_RESTARTED",
                        "message": "Document processing interrupted by server restart. Please re-upload or retry.",
                    },
                )
            )
            now = datetime.now(UTC)
            ext_stmt = (
                update(ExtractionRun)
                .where(
                    ExtractionRun.status.in_(
                        [DocumentProcessingStatus.QUEUED, DocumentProcessingStatus.PROCESSING]
                    )
                )
                .values(
                    status=DocumentProcessingStatus.FAILED,
                    error_message="Extraction interrupted by server restart. Please re-trigger extraction.",
                    completed_at=now,
                )
            )
            doc_res = await s.execute(doc_stmt)
            ext_res = await s.execute(ext_stmt)
            await s.commit()
            if doc_res.rowcount > 0 or ext_res.rowcount > 0:
                logger.warning(
                    "Recovered %d stale document(s) and %d stale extraction run(s) from server restart.",
                    doc_res.rowcount,
                    ext_res.rowcount,
                )

        if session is not None:
            await _execute_recovery(session)
        else:
            session_factory = get_session_factory()
            async with session_factory() as s:
                await _execute_recovery(s)
    except Exception as exc:
        logger.error("Failed to recover stale processing jobs on startup: %s", str(exc))


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

    # Recover stale processing jobs interrupted by server restart
    await recover_stale_processing_jobs()

    # Start local background worker
    worker = get_background_worker()
    if hasattr(worker, "start"):
        await worker.start()

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
