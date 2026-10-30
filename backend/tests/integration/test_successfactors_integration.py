import uuid

import pytest
from httpx import AsyncClient

from app.core.security import UserRole, create_access_token


@pytest.mark.asyncio
async def test_get_simulated_successfactors_feed_endpoint(client: AsyncClient):
    """
    Test GET /api/v1/integrations/successfactors/feed returns synthetic feed
    with explicit simulation disclaimer and structured applicants.
    """
    user_id = str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {create_access_token(user_id, UserRole.EMPLOYER_ADMIN)}"}

    res = await client.get("/api/v1/integrations/successfactors/feed", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_simulated"] is True
    assert "SIMULATION" in data["simulation_disclaimer"]
    assert data["requisition"]["job_req_id"] == "REQ-CLOUD-2026"
    assert len(data["applications"]) == 8


@pytest.mark.asyncio
async def test_import_successfactors_feed_endpoint_permissions(client: AsyncClient):
    """
    Test POST /api/v1/integrations/successfactors/import:
    - Employer Admin succeeds (200).
    - Candidate is denied (403).
    - Anonymous is denied (401).
    """
    admin_id = str(uuid.uuid4())
    cand_id = str(uuid.uuid4())

    admin_headers = {
        "Authorization": f"Bearer {create_access_token(admin_id, UserRole.EMPLOYER_ADMIN)}"
    }
    cand_headers = {"Authorization": f"Bearer {create_access_token(cand_id, UserRole.CANDIDATE)}"}

    # 1. Employer Admin imports successfully
    res_admin = await client.post(
        "/api/v1/integrations/successfactors/import", headers=admin_headers
    )
    assert res_admin.status_code == 200
    body = res_admin.json()
    assert body["is_simulated"] is True
    assert body["imported_applications_count"] == 8
    assert len(body["imported_application_ids"]) == 8
    assert body["job_title"] == "Senior Cloud Backend Engineer"

    # 2. Candidate is forbidden
    res_cand = await client.post("/api/v1/integrations/successfactors/import", headers=cand_headers)
    assert res_cand.status_code == 403

    # 3. Unauthenticated request is rejected
    res_anon = await client.post("/api/v1/integrations/successfactors/import")
    assert res_anon.status_code == 401
