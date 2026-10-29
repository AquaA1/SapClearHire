import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_readiness_fails_when_db_down(client: AsyncClient, monkeypatch):
    """
    Verifies that when database connectivity fails:
    - /api/v1/health/ready returns HTTP 503 Service Unavailable
    - response body marks status as 'not_ready' and database as 'disconnected'
    - /api/v1/health/live continues returning HTTP 200 OK
    """

    # Simulate database connection failure
    async def mock_broken_db(timeout_seconds: float = 3.0) -> bool:
        return False

    monkeypatch.setattr("app.services.health.check_database_connection", mock_broken_db)

    # Readiness should return 503
    ready_res = await client.get("/api/v1/health/ready")
    assert ready_res.status_code == 503
    ready_data = ready_res.json()
    assert ready_data["status"] == "not_ready"
    assert ready_data["database"] == "disconnected"
    assert "Unable to connect" in ready_data["error"]

    # Liveness must remain unaffected (200 OK)
    live_res = await client.get("/api/v1/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"
