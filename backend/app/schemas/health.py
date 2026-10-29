from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Application metadata and operational status."""

    status: Literal["ok", "degraded", "error"] = Field("ok", description="Overall system status")
    service: str = Field("ClearHire API", description="Service identifier")
    version: str = Field("0.1.0", description="Service semantic version")
    timestamp: datetime = Field(..., description="UTC server timestamp")
    environment: str = Field("development", description="Runtime environment")


class LivenessResponse(BaseModel):
    """Process liveness probe response."""

    status: Literal["alive"] = "alive"


class ReadinessResponse(BaseModel):
    """External dependency readiness response."""

    status: Literal["ready", "not_ready"]
    database: Literal["connected", "disconnected"]
    timestamp: datetime
    error: str | None = None
