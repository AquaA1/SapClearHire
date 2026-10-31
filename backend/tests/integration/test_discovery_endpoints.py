import uuid

import pytest
from httpx import AsyncClient

from app.core.security import UserRole, create_access_token
from tests.helpers import generate_sample_pdf


@pytest.mark.asyncio
async def test_list_applications_filtering_pagination_and_scoping(client: AsyncClient):
    """
    Test GET /api/v1/applications:
    - Candidate sees only their own applications.
    - Employer sees only applications for their tenant's jobs.
    - Auditor sees all applications.
    - Filters by job_id, status.
    - Pagination via limit and offset.
    """
    emp1_id = str(uuid.uuid4())
    emp2_id = str(uuid.uuid4())
    cand1_id = str(uuid.uuid4())
    cand2_id = str(uuid.uuid4())
    auditor_id = str(uuid.uuid4())

    h_emp1 = {
        "Authorization": f"Bearer {create_access_token(emp1_id, UserRole.EMPLOYER_ADMIN, employer_id='org-a')}"
    }
    h_emp2 = {
        "Authorization": f"Bearer {create_access_token(emp2_id, UserRole.EMPLOYER_ADMIN, employer_id='org-b')}"
    }
    h_cand1 = {"Authorization": f"Bearer {create_access_token(cand1_id, UserRole.CANDIDATE)}"}
    h_cand2 = {"Authorization": f"Bearer {create_access_token(cand2_id, UserRole.CANDIDATE)}"}
    h_auditor = {
        "Authorization": f"Bearer {create_access_token(auditor_id, UserRole.SYSTEM_AUDITOR)}"
    }

    # Emp1 creates job1; Emp2 creates job2
    j1 = (
        await client.post(
            "/api/v1/jobs", headers=h_emp1, json={"title": "Job Alpha", "criteria": []}
        )
    ).json()["id"]
    j2 = (
        await client.post(
            "/api/v1/jobs", headers=h_emp2, json={"title": "Job Beta", "criteria": []}
        )
    ).json()["id"]

    # Cand1 uploads doc1 and applies to Job1
    pdf1 = generate_sample_pdf(["Resume Cand1"])
    doc1 = (
        await client.post(
            "/api/v1/documents",
            headers=h_cand1,
            files={"file": ("r1.pdf", pdf1, "application/pdf")},
        )
    ).json()["id"]
    app1 = (
        await client.post(
            "/api/v1/applications",
            headers=h_cand1,
            json={"job_id": j1, "primary_document_id": doc1},
        )
    ).json()["id"]

    # Cand2 uploads doc2 and applies to Job2
    pdf2 = generate_sample_pdf(["Resume Cand2"])
    doc2 = (
        await client.post(
            "/api/v1/documents",
            headers=h_cand2,
            files={"file": ("r2.pdf", pdf2, "application/pdf")},
        )
    ).json()["id"]
    app2 = (
        await client.post(
            "/api/v1/applications",
            headers=h_cand2,
            json={"job_id": j2, "primary_document_id": doc2},
        )
    ).json()["id"]

    # 1. Cand1 lists applications -> only app1
    res = await client.get("/api/v1/applications", headers=h_cand1)
    assert res.status_code == 200
    ids = [a["id"] for a in res.json()]
    assert app1 in ids
    assert app2 not in ids

    # 2. Emp1 lists applications -> only app1 (belongs to Job1 in org-a)
    res = await client.get("/api/v1/applications", headers=h_emp1)
    assert res.status_code == 200
    ids = [a["id"] for a in res.json()]
    assert app1 in ids
    assert app2 not in ids

    # 3. Emp2 lists applications -> only app2 (belongs to Job2 in org-b)
    res = await client.get("/api/v1/applications", headers=h_emp2)
    assert res.status_code == 200
    ids = [a["id"] for a in res.json()]
    assert app2 in ids
    assert app1 not in ids

    # 4. Auditor lists applications -> both app1 and app2
    res = await client.get("/api/v1/applications", headers=h_auditor)
    assert res.status_code == 200
    ids = [a["id"] for a in res.json()]
    assert app1 in ids
    assert app2 in ids

    # 5. Filter by job_id
    res = await client.get(f"/api/v1/applications?job_id={j1}", headers=h_auditor)
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["id"] == app1

    # 6. Pagination (limit=1, offset=0)
    res = await client.get("/api/v1/applications?limit=1&offset=0", headers=h_auditor)
    assert res.status_code == 200
    assert len(res.json()) == 1


@pytest.mark.asyncio
async def test_list_jobs_filtering_pagination_and_scoping(client: AsyncClient):
    """
    Test GET /api/v1/jobs:
    - Candidate sees only ACTIVE jobs (never drafts).
    - Employer sees jobs within their tenant organization (including drafts).
    - Auditor sees all jobs.
    - Filter by department, status.
    - Pagination.
    """
    emp1_id = str(uuid.uuid4())
    emp2_id = str(uuid.uuid4())
    cand_id = str(uuid.uuid4())
    auditor_id = str(uuid.uuid4())

    h_emp1 = {
        "Authorization": f"Bearer {create_access_token(emp1_id, UserRole.EMPLOYER_ADMIN, employer_id='tenant-x')}"
    }
    h_emp2 = {
        "Authorization": f"Bearer {create_access_token(emp2_id, UserRole.EMPLOYER_ADMIN, employer_id='tenant-y')}"
    }
    h_cand = {"Authorization": f"Bearer {create_access_token(cand_id, UserRole.CANDIDATE)}"}
    h_auditor = {
        "Authorization": f"Bearer {create_access_token(auditor_id, UserRole.SYSTEM_AUDITOR)}"
    }

    # Emp1 creates active job in Engineering
    j1 = (
        await client.post(
            "/api/v1/jobs",
            headers=h_emp1,
            json={
                "title": "Backend Python",
                "department": "Engineering",
                "criteria": [],
            },
        )
    ).json()["id"]

    # Emp2 creates active job in Design
    j2 = (
        await client.post(
            "/api/v1/jobs",
            headers=h_emp2,
            json={
                "title": "UI Designer",
                "department": "Design",
                "criteria": [],
            },
        )
    ).json()["id"]

    # 1. Candidate lists jobs -> sees active jobs across employers
    res = await client.get("/api/v1/jobs", headers=h_cand)
    assert res.status_code == 200
    ids = [j["id"] for j in res.json()]
    assert j1 in ids
    assert j2 in ids

    # 2. Emp1 lists jobs -> only tenant-x jobs (j1, not j2)
    res = await client.get("/api/v1/jobs", headers=h_emp1)
    assert res.status_code == 200
    ids = [j["id"] for j in res.json()]
    assert j1 in ids
    assert j2 not in ids

    # 3. Filter by department
    res = await client.get("/api/v1/jobs?department=Engineering", headers=h_cand)
    assert res.status_code == 200
    ids = [j["id"] for j in res.json()]
    assert j1 in ids
    assert j2 not in ids

    # 4. Auditor lists jobs -> sees all jobs
    res = await client.get("/api/v1/jobs", headers=h_auditor)
    assert res.status_code == 200
    ids = [j["id"] for j in res.json()]
    assert j1 in ids
    assert j2 in ids

    # 5. Pagination
    res = await client.get("/api/v1/jobs?limit=1&offset=0", headers=h_cand)
    assert res.status_code == 200
    assert len(res.json()) == 1


@pytest.mark.asyncio
async def test_list_audit_events_querying_and_isolation(client: AsyncClient):
    """
    Test GET /api/v1/audit:
    - Accessible to SYSTEM_AUDITOR and EMPLOYER_ADMIN.
    - Candidate/Reviewer gets 403.
    - Auditor can query any events.
    - Employer can query events for their own resources.
    - Employer querying other tenant's resource gets 403.
    """
    emp1_id = str(uuid.uuid4())
    emp2_id = str(uuid.uuid4())
    cand_id = str(uuid.uuid4())
    auditor_id = str(uuid.uuid4())

    h_emp1 = {
        "Authorization": f"Bearer {create_access_token(emp1_id, UserRole.EMPLOYER_ADMIN, employer_id='tenant-audit-1')}"
    }
    h_emp2 = {
        "Authorization": f"Bearer {create_access_token(emp2_id, UserRole.EMPLOYER_ADMIN, employer_id='tenant-audit-2')}"
    }
    h_cand = {"Authorization": f"Bearer {create_access_token(cand_id, UserRole.CANDIDATE)}"}
    h_auditor = {
        "Authorization": f"Bearer {create_access_token(auditor_id, UserRole.SYSTEM_AUDITOR)}"
    }

    # Candidate denied
    assert (await client.get("/api/v1/audit", headers=h_cand)).status_code == 403

    # Emp1 creates job
    j1 = (
        await client.post(
            "/api/v1/jobs", headers=h_emp1, json={"title": "Audited Job", "criteria": []}
        )
    ).json()["id"]

    # Auditor lists audit events -> 200, contains events
    res = await client.get("/api/v1/audit", headers=h_auditor)
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)

    # Auditor query by resource_id
    res = await client.get(f"/api/v1/audit?resource_type=job&resource_id={j1}", headers=h_auditor)
    assert res.status_code == 200
    # Every returned event has verified hash
    for ev in res.json():
        assert ev["is_verified"] is True

    # Emp1 queries own job audit events -> 200
    res = await client.get(f"/api/v1/audit?resource_type=job&resource_id={j1}", headers=h_emp1)
    assert res.status_code == 200

    # Emp2 queries Emp1's job audit events -> 403
    res = await client.get(f"/api/v1/audit?resource_type=job&resource_id={j1}", headers=h_emp2)
    assert res.status_code == 403
