from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import logger


class ClearHireError(Exception):
    """Base exception class for ClearHire domain errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


ClearHireException = ClearHireError


class NotFoundError(ClearHireException):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "Resource not found", details: Any = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(ClearHireException):
    """Raised when a state conflict occurs."""

    def __init__(self, message: str = "Resource state conflict", details: Any = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ValidationError(ClearHireException):
    """Raised when domain-level business validation fails."""

    def __init__(self, message: str = "Validation failed", details: Any = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class AuthenticationError(ClearHireException):
    """Raised when authentication fails or credentials are missing."""

    def __init__(self, message: str = "Authentication failed", details: Any = None):
        super().__init__(
            message=message,
            code="AUTHENTICATION_FAILED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationError(ClearHireException):
    """Raised when an authenticated actor lacks permissions."""

    def __init__(self, message: str = "Access forbidden", details: Any = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class DatabaseConnectionError(ClearHireException):
    """Raised when database connectivity fails during health check or transactions."""

    def __init__(self, message: str = "Database connection unavailable", details: Any = None):
        super().__init__(
            message=message,
            code="DATABASE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class ExternalServiceError(ClearHireException):
    """Raised when an external integration fails."""

    def __init__(self, message: str = "External integration error", details: Any = None):
        super().__init__(
            message=message,
            code="BAD_GATEWAY",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers standard error response handlers on the FastAPI application."""

    @app.exception_handler(ClearHireException)
    async def clearhire_exception_handler(_: Request, exc: ClearHireException) -> JSONResponse:
        logger.warning("Application domain error [%s]: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning("Request schema validation error: %s", exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "REQUEST_VALIDATION_ERROR",
                    "message": "The request body or parameters failed validation.",
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        # Secure error handling: log stack trace internally, never leak to client
        logger.exception("Unhandled server exception: %s", str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred. Please try again later.",
                    "details": None,
                }
            },
        )
