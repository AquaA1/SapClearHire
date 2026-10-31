from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logging import logger

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Returns or initializes the global AsyncEngine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        uri = settings.SQLALCHEMY_DATABASE_URI

        # Configure pool args based on dialect
        connect_args = {}
        if uri.startswith("sqlite"):
            from sqlalchemy import event

            connect_args["check_same_thread"] = False
            _engine = create_async_engine(
                uri,
                connect_args=connect_args,
                echo=settings.DEBUG,
            )

            @event.listens_for(_engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            _engine = create_async_engine(
                uri,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=settings.DEBUG,
            )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Returns or initializes the session factory."""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
        )
    return _sessionmaker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an AsyncSession per request.
    Rolls back automatically on unhandled exceptions and ensures clean closure.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database_connection(timeout_seconds: float = 3.0) -> bool:
    """
    Executes a simple connectivity query (SELECT 1) against the database.
    Returns True if healthy, False if down or unreachable.
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            # Enforce timeout for readiness probe
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", str(exc))
        return False


async def close_db_engine() -> None:
    """Disposes the async engine during application shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
