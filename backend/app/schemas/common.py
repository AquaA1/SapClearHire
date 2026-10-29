from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Structured error payload representation."""

    code: str = Field(..., description="Unique machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Any = Field(
        default=None, description="Optional diagnostic details or validation errors"
    )


class ErrorEnvelope(BaseModel):
    """Standard API error response wrapper."""

    error: ErrorDetail


class SuccessEnvelope(BaseModel, Generic[T]):
    """Standard API success response wrapper."""

    data: T
