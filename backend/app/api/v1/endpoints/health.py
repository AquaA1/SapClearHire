from fastapi import APIRouter, Response, status

from app.schemas.health import HealthResponse, LivenessResponse, ReadinessResponse
from app.services.health import HealthService

router = APIRouter(prefix="/health", tags=["System Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Application Health Metadata",
    description="Returns high-level system metadata and operational status.",
)
async def get_health() -> HealthResponse:
    return HealthService.get_health()


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Process Liveness Probe",
    description="Returns whether the application process is running. Independent of external dependencies.",
)
async def get_liveness() -> LivenessResponse:
    return HealthService.get_liveness()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Dependency Readiness Probe",
    description="Verifies whether external dependencies (e.g. PostgreSQL) are reachable. Returns 503 if disconnected.",
    responses={
        200: {"model": ReadinessResponse, "description": "System ready to handle traffic"},
        503: {"model": ReadinessResponse, "description": "Database connectivity failed"},
    },
)
async def get_readiness(response: Response) -> ReadinessResponse:
    readiness, is_healthy = await HealthService.get_readiness()
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return readiness
