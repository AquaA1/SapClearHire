import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_route_registration_and_docs(client: AsyncClient):
    openapi_res = await client.get("/openapi.json")
    assert openapi_res.status_code == 200
    spec = openapi_res.json()
    assert spec["info"]["title"] == "ClearHire API"

    # Verify routes exist in OpenAPI specification
    paths = spec["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/health/live" in paths
    assert "/api/v1/health/ready" in paths


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "ClearHire API"
    assert "0.1.0" in data["version"]
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_liveness_endpoint(client: AsyncClient):
    res = await client.get("/api/v1/health/live")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_endpoint_success(client: AsyncClient, monkeypatch):
    # Mock database check to return True
    async def mock_check_db(timeout_seconds: float = 3.0) -> bool:
        return True

    monkeypatch.setattr("app.services.health.check_database_connection", mock_check_db)

    res = await client.get("/api/v1/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
