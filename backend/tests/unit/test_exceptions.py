import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseConnectionError,
    NotFoundError,
    ValidationError,
)
from app.main import create_application


@pytest.mark.asyncio
async def test_domain_exception_handling():
    app = create_application()

    @app.get("/test-not-found")
    async def trigger_not_found():
        raise NotFoundError("Application record 123 not found")

    @app.get("/test-conflict")
    async def trigger_conflict():
        raise ConflictError("Job revision already finalized")

    @app.get("/test-validation")
    async def trigger_validation():
        raise ValidationError("Resume file exceeds 15 MB limit")

    @app.get("/test-auth")
    async def trigger_auth():
        raise AuthenticationError("Invalid Bearer token")

    @app.get("/test-forbidden")
    async def trigger_forbidden():
        raise AuthorizationError("Only human reviewers may submit rationale decisions")

    @app.get("/test-db-error")
    async def trigger_db_error():
        raise DatabaseConnectionError("PostgreSQL pool exhausted")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/test-not-found")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"
        assert res.json()["error"]["message"] == "Application record 123 not found"

        res = await client.get("/test-conflict")
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "CONFLICT"

        res = await client.get("/test-validation")
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"

        res = await client.get("/test-auth")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTHENTICATION_FAILED"

        res = await client.get("/test-forbidden")
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"

        res = await client.get("/test-db-error")
        assert res.status_code == 503
        assert res.json()["error"]["code"] == "DATABASE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_unhandled_exception_masks_secrets():
    app = create_application()

    @app.get("/test-unhandled")
    async def trigger_crash():
        raise RuntimeError(
            "Database connection string postgresql://admin:super_secret_pw@db:5432 failed"
        )

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/test-unhandled")
        assert res.status_code == 500
        body = res.json()
        assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
        # Secret password or raw internal traceback must NOT be leaked
        assert "super_secret_pw" not in str(body)
