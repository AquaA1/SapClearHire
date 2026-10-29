from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger, setup_logging
from app.db.session import close_db_engine
from app.workers import get_background_worker


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
