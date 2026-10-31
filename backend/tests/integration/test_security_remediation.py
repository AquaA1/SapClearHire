import uuid

import pytest
from httpx import AsyncClient

from app.core.security import UserRole, create_access_token
from tests.helpers import generate_sample_pdf


@pytest.mark.asyncio
async def test_document_cross_tenant_and_ownership_authorization(client: AsyncClient):
    """
    Verify complete tenant isolation and access control on documents:
    - Candidates access only own documents.
    - Auditors have read-only access (403 on extract).
    - Employers/Reviewers access only documents linked to an application in their org.
    - Other tenant employers/reviewers get 403.
    """
    cand1_id = str(uuid.uuid4())
    cand2_id = str(uuid.uuid4())
    emp1_id = str(uuid.uuid4())
    emp2_id = str(uuid.uuid4())
    auditor_id = str(uuid.uuid4())

    cand1_token = create_access_token(subject=cand1_id, role=UserRole.CANDIDATE)
    cand2_token = create_access_token(subject=cand2_id, role=UserRole.CANDIDATE)
    emp1_token = create_access_token(
        subject=emp1_id, role=UserRole.EMPLOYER_ADMIN, employer_id="org-1"
    )
    emp2_token = create_access_token(
        subject=emp2_id, role=UserRole.EMPLOYER_ADMIN, employer_id="org-2"
    )
    auditor_token = create_access_token(subject=auditor_id, role=UserRole.SYSTEM_AUDITOR)

    h_cand1 = {"Authorization": f"Bearer {cand1_token}"}
    h_cand2 = {"Authorization": f"Bearer {cand2_token}"}
    h_emp1 = {"Authorization": f"Bearer {emp1_token}"}
    h_emp2 = {"Authorization": f"Bearer {emp2_token}"}
    h_auditor = {"Authorization": f"Bearer {auditor_token}"}

    # 1. Cand1 uploads resume
    pdf = generate_sample_pdf(["Python developer with AWS experience"])
    upload_res = await client.post(
        "/api/v1/documents",
        headers=h_cand1,
        files={"file": ("resume.pdf", pdf, "application/pdf")},
    )
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["id"]

    # 2. Cand1 can read own status
    assert (
        await client.get(f"/api/v1/documents/{doc_id}/status", headers=h_cand1)
    ).status_code == 200

    # 3. Cand2 CANNOT read Cand1 status or extract
    assert (
        await client.get(f"/api/v1/documents/{doc_id}/status", headers=h_cand2)
    ).status_code == 403
    assert (
        await client.post(f"/api/v1/documents/{doc_id}/extract", headers=h_cand2)
    ).status_code == 403
    assert (
        await client.get(f"/api/v1/documents/{doc_id}/extraction-results", headers=h_cand2)
    ).status_code == 403

    # 4. Emp1 and Emp2 cannot access unlinked document
    assert (
        await client.get(f"/api/v1/documents/{doc_id}/status", headers=h_emp1)
    ).status_code == 403
    assert (
        await client.post(f"/api/v1/documents/{doc_id}/extract", headers=h_emp1)
    ).status_code == 403
    assert (
        await client.get(f"/api/v1/documents/{doc_id}/extraction-results", headers=h_emp1)
    ).status_code == 403

    # 5. Auditor has read-only access (can read status, cannot trigger extract)
    assert (
        await client.get(f"/api/v1/documents/{doc_id}/status", headers=h_auditor)
    ).status_code == 200
    assert (
        await client.post(f"/api/v1/documents/{doc_id}/extract", headers=h_auditor)
    ).status_code == 403

    # 6. Emp1 creates job and Cand1 applies
    job_res = await client.post(
        "/api/v1/jobs",
        headers=h_emp1,
        json={
            "title": "Cloud Dev",
            "criteria": [{"name": "Python", "category": "required", "weight": 1.0}],
        },
    )
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    app_res = await client.post(
        "/api/v1/applications",
        headers=h_cand1,
        json={"job_id": job_id, "primary_document_id": doc_id},
    )
    assert app_res.status_code == 201

    # 7. Emp1 can now access document status
    assert (
        await client.get(f"/api/v1/documents/{doc_id}/status", headers=h_emp1)
    ).status_code == 200

    # 8. Emp2 STILL cannot access document (different organization)
    assert (
        await client.get(f"/api/v1/documents/{doc_id}/status", headers=h_emp2)
    ).status_code == 403
    assert (
        await client.post(f"/api/v1/documents/{doc_id}/extract", headers=h_emp2)
    ).status_code == 403
    assert (
        await client.get(f"/api/v1/documents/{doc_id}/extraction-results", headers=h_emp2)
    ).status_code == 403


@pytest.mark.asyncio
async def test_candidate_profile_skills_tenant_isolation(client: AsyncClient):
    """
    Verify tenant isolation for GET /api/v1/profiles/{id}/skills:
    - Candidate can only view their own profile.
    - Employer can only view profile if candidate applied to their job.
    - Other tenant employer gets 403.
    - Auditor can view profile.
    """
    cand1_id = str(uuid.uuid4())
    cand2_id = str(uuid.uuid4())
    emp1_id = str(uuid.uuid4())
    emp2_id = str(uuid.uuid4())
    auditor_id = str(uuid.uuid4())

    h_cand1 = {"Authorization": f"Bearer {create_access_token(cand1_id, UserRole.CANDIDATE)}"}
    h_cand2 = {"Authorization": f"Bearer {create_access_token(cand2_id, UserRole.CANDIDATE)}"}
    h_emp1 = {
        "Authorization": f"Bearer {create_access_token(emp1_id, UserRole.EMPLOYER_ADMIN, employer_id='org-alpha')}"
    }
    h_emp2 = {
        "Authorization": f"Bearer {create_access_token(emp2_id, UserRole.EMPLOYER_ADMIN, employer_id='org-beta')}"
    }
    h_auditor = {
        "Authorization": f"Bearer {create_access_token(auditor_id, UserRole.SYSTEM_AUDITOR)}"
    }

    # Candidate 1 views own skills (empty is fine, status 200)
    assert (
        await client.get(f"/api/v1/profiles/{cand1_id}/skills", headers=h_cand1)
    ).status_code == 200

    # Candidate 2 views Candidate 1 skills -> 403
    assert (
        await client.get(f"/api/v1/profiles/{cand1_id}/skills", headers=h_cand2)
    ).status_code == 403

    # Emp1 before application -> 403
    assert (
        await client.get(f"/api/v1/profiles/{cand1_id}/skills", headers=h_emp1)
    ).status_code == 403

    # Auditor -> 200
    assert (
        await client.get(f"/api/v1/profiles/{cand1_id}/skills", headers=h_auditor)
    ).status_code == 200

    # Create job for Emp1 and apply Cand1
    pdf = generate_sample_pdf(["Python developer"])
    doc_res = await client.post(
        "/api/v1/documents", headers=h_cand1, files={"file": ("r.pdf", pdf, "application/pdf")}
    )
    doc_id = doc_res.json()["id"]

    job_res = await client.post(
        "/api/v1/jobs", headers=h_emp1, json={"title": "Engineer", "criteria": []}
    )
    job_id = job_res.json()["id"]

    await client.post(
        "/api/v1/applications",
        headers=h_cand1,
        json={"job_id": job_id, "primary_document_id": doc_id},
    )

    # Now Emp1 can view Cand1 profile
    assert (
        await client.get(f"/api/v1/profiles/{cand1_id}/skills", headers=h_emp1)
    ).status_code == 200

    # Emp2 STILL gets 403
    assert (
        await client.get(f"/api/v1/profiles/{cand1_id}/skills", headers=h_emp2)
    ).status_code == 403
