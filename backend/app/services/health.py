from datetime import UTC, datetime

from app.core.config import get_settings
from app.db.session import check_database_connection
from app.schemas.health import HealthResponse, LivenessResponse, ReadinessResponse


class HealthService:
    """Encapsulates system health and dependency readiness checks."""

    @staticmethod
    def get_health() -> HealthResponse:
        """Returns application metadata and status."""
        settings = get_settings()
        return HealthResponse(
            status="ok",
            service=settings.PROJECT_NAME,
            version=settings.VERSION,
            timestamp=datetime.now(UTC),
            environment=settings.ENVIRONMENT,
        )

    @staticmethod
    def get_liveness() -> LivenessResponse:
        """Returns process liveness without checking external dependencies."""
        return LivenessResponse(status="alive")

    @staticmethod
    async def get_readiness() -> tuple[ReadinessResponse, bool]:
        """
        Validates external dependencies (PostgreSQL).
        Returns tuple of (ReadinessResponse, is_healthy: bool).
        """
        now = datetime.now(UTC)
        db_connected = await check_database_connection(timeout_seconds=2.0)

        if db_connected:
            return (
                ReadinessResponse(
                    status="ready",
                    database="connected",
                    timestamp=now,
                ),
                True,
            )

        return (
            ReadinessResponse(
                status="not_ready",
                database="disconnected",
                timestamp=now,
                error="Unable to connect to primary database",
            ),
            False,
        )
