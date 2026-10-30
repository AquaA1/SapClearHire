import uuid

import pytest
from httpx import AsyncClient

from app.core.security import UserRole, create_access_token
from tests.helpers import generate_sample_pdf


@pytest.mark.asyncio
async def test_uncertain_case_reaches_reviewer_clarification_and_approval_flow(client: AsyncClient):
    """
    End-to-end integration test of the human review workflow:
    1. Employer posts a job with a required criterion that will be evaluated as ambiguous.
    2. Candidate uploads a resume and applies.
    3. Evaluation produces an ambiguous criterion result.
    4. Review flag is raised and assigned to Reviewer A.
    5. Reviewer A lists assigned review cases and views full case details.
    6. Reviewer A requests clarification with mandatory rationale.
    7. Candidate submits clarification statement (remains unverified as 'candidate_clarified').
    8. Reviewer A reviews updated case with clarification and accepts evidence.
    9. Verification state transitions to 'human_verified' and flag resolves.
    """
    employer_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    reviewer_a_id = str(uuid.uuid4())

    emp_token = create_access_token(subject=employer_id, role=UserRole.EMPLOYER_ADMIN)
    cand_token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)
    rev_a_token = create_access_token(subject=reviewer_a_id, role=UserRole.REVIEWER)

    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    cand_headers = {"Authorization": f"Bearer {cand_token}"}
    rev_a_headers = {"Authorization": f"Bearer {rev_a_token}"}

    # 1. Employer creates a job requisition
    job_payload = {
        "title": "Cloud Platform Architect",
        "criteria": [
            {
                "name": "Team Player",
                "category": "required",
                "description": "Collaborative teamwork across engineering teams",
            },
            {
                "name": "Python",
                "category": "required",
                "description": "Production Python development",
            },
        ],
    }
    job_res = await client.post("/api/v1/jobs", json=job_payload, headers=emp_headers)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 2. Candidate uploads resume and applies
    resume_pdf = generate_sample_pdf(
        [
            "Bob Engineer - 6 years Python backend development.",
            "Built distributed microservices in Python and PostgreSQL.",
        ]
    )
    doc_res = await client.post(
        "/api/v1/documents",
        files={"file": ("bob_resume.pdf", resume_pdf, "application/pdf")},
        headers=cand_headers,
    )
    doc_id = doc_res.json()["id"]

    # Trigger extraction
    ext_res = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=cand_headers)
    assert ext_res.status_code == 202

    # Apply
    app_res = await client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "primary_document_id": doc_id},
        headers=cand_headers,
    )
    assert app_res.status_code == 201
    application_id = app_res.json()["id"]

    # 3. Evaluate application -> 'Team Player' will be AMBIGUOUS (vague/subjective)
    eval_res = await client.post(
        "/api/v1/evaluations",
        json={"application_id": application_id},
        headers=emp_headers,
    )
    assert eval_res.status_code == 201
    eval_data = eval_res.json()
    assert eval_data["coverage"]["ambiguous_count"] >= 1

    # 4. Create review flags assigned to Reviewer A
    flag_payload = {
        "application_id": application_id,
        "assigned_to_user_id": reviewer_a_id,
        "priority": "high",
    }
    flag_res = await client.post("/api/v1/review-flags", json=flag_payload, headers=emp_headers)
    assert flag_res.status_code == 201
    flag_batch = flag_res.json()
    assert flag_batch["total_flagged"] >= 1
    flag_id = flag_batch["flags"][0]["id"]

    # 5. Reviewer A lists assigned review cases
    cases_res = await client.get("/api/v1/review-flags", headers=rev_a_headers)
    assert cases_res.status_code == 200
    cases = cases_res.json()
    assert len(cases) >= 1
    assert any(c["id"] == flag_id for c in cases)

    # Reviewer A retrieves full case details
    detail_res = await client.get(f"/api/v1/reviews/{flag_id}", headers=rev_a_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["flag_id"] == flag_id
    assert detail["criterion_name"] == "Team Player"
    assert detail["ai_status"] == "ambiguous"
    assert detail["verification_state"] == "unverified"
    ce_id = detail["criterion_evidence_id"]

    # 6. Reviewer A requests clarification with mandatory rationale
    clar_decision_payload = {
        "decision": "requested_clarification",
        "mandatory_rationale": "Please provide concrete examples of leading cross-functional team initiatives.",
    }
    dec1_res = await client.post(
        f"/api/v1/reviews/{flag_id}/decision",
        json=clar_decision_payload,
        headers=rev_a_headers,
    )
    assert dec1_res.status_code == 201
    dec1_data = dec1_res.json()
    assert dec1_data["decision"] == "requested_clarification"
    assert dec1_data["new_verification_state"] == "unverified"
    assert dec1_data["flag_status"] == "under_review"

    # 7. Candidate submits clarification statement
    clar_submit_payload = {
        "criterion_evidence_id": ce_id,
        "candidate_statement": "I coordinated sprint planning across 3 backend squads and mentored 4 junior engineers.",
    }
    cand_clar_res = await client.post(
        f"/api/v1/applications/{application_id}/clarifications",
        json=clar_submit_payload,
        headers=cand_headers,
    )
    assert cand_clar_res.status_code == 201
    clar_res_data = cand_clar_res.json()
    # Candidate-provided evidence remains unverified as 'candidate_clarified'
    assert clar_res_data["new_verification_state"] == "candidate_clarified"

    # 8. Reviewer A inspects updated case containing the clarification
    updated_detail_res = await client.get(f"/api/v1/reviews/{flag_id}", headers=rev_a_headers)
    assert updated_detail_res.status_code == 200
    updated_detail = updated_detail_res.json()
    assert updated_detail["verification_state"] == "candidate_clarified"
    assert len(updated_detail["clarifications"]) == 1
    assert (
        "coordinated sprint planning" in updated_detail["clarifications"][0]["candidate_statement"]
    )
    assert len(updated_detail["decisions"]) == 1

    # 9. Reviewer A accepts the evidence with non-empty rationale
    accept_payload = {
        "decision": "accepted",
        "mandatory_rationale": "Candidate's leadership statement sufficiently addresses collaborative teamwork benchmark.",
    }
    accept_res = await client.post(
        f"/api/v1/reviews/{flag_id}/decision",
        json=accept_payload,
        headers=rev_a_headers,
    )
    assert accept_res.status_code == 201
    accept_data = accept_res.json()
    assert accept_data["decision"] == "accepted"
    assert accept_data["new_verification_state"] == "human_verified"
    assert accept_data["flag_status"] == "resolved"


@pytest.mark.asyncio
async def test_reviewer_and_candidate_authorization_denials(client: AsyncClient):
    """
    Test permission boundaries:
    - Reviewer B cannot access Reviewer A's assigned case (403).
    - Reviewer B cannot decide on Reviewer A's assigned case (403).
    - Candidate cannot make reviewer decisions (403).
    - Candidate B cannot submit clarification on Candidate A's application (403).
    - Unauthenticated request is rejected (401).
    """
    employer_id = str(uuid.uuid4())
    candidate_a_id = str(uuid.uuid4())
    candidate_b_id = str(uuid.uuid4())
    reviewer_a_id = str(uuid.uuid4())
    reviewer_b_id = str(uuid.uuid4())

    emp_token = create_access_token(subject=employer_id, role=UserRole.EMPLOYER_ADMIN)
    cand_a_token = create_access_token(subject=candidate_a_id, role=UserRole.CANDIDATE)
    cand_b_token = create_access_token(subject=candidate_b_id, role=UserRole.CANDIDATE)
    rev_b_token = create_access_token(subject=reviewer_b_id, role=UserRole.REVIEWER)

    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    cand_a_headers = {"Authorization": f"Bearer {cand_a_token}"}
    cand_b_headers = {"Authorization": f"Bearer {cand_b_token}"}
    rev_b_headers = {"Authorization": f"Bearer {rev_b_token}"}

    # Create job & application for candidate A
    job_res = await client.post(
        "/api/v1/jobs",
        json={
            "title": "Security Analyst",
            "criteria": [{"name": "Auditing", "category": "required"}],
        },
        headers=emp_headers,
    )
    job_id = job_res.json()["id"]

    pdf = generate_sample_pdf(["Security auditing experience."])
    doc_res = await client.post(
        "/api/v1/documents",
        files={"file": ("sec.pdf", pdf, "application/pdf")},
        headers=cand_a_headers,
    )
    doc_id = doc_res.json()["id"]
    await client.post(f"/api/v1/documents/{doc_id}/extract", headers=cand_a_headers)

    app_res = await client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "primary_document_id": doc_id},
        headers=cand_a_headers,
    )
    app_id = app_res.json()["id"]

    await client.post("/api/v1/evaluations", json={"application_id": app_id}, headers=emp_headers)

    # Flag assigned to Reviewer A
    flag_res = await client.post(
        "/api/v1/review-flags",
        json={"application_id": app_id, "assigned_to_user_id": reviewer_a_id},
        headers=emp_headers,
    )
    flag_id = flag_res.json()["flags"][0]["id"]
    ce_id = flag_res.json()["flags"][0]["criterion_evidence_id"]

    # 1. Reviewer B tries to access Reviewer A's case -> 403 Forbidden
    unauth_get = await client.get(f"/api/v1/reviews/{flag_id}", headers=rev_b_headers)
    assert unauth_get.status_code == 403

    # 2. Reviewer B tries to decide on Reviewer A's case -> 403 Forbidden
    unauth_dec = await client.post(
        f"/api/v1/reviews/{flag_id}/decision",
        json={"decision": "accepted", "mandatory_rationale": "I am deciding without assignment"},
        headers=rev_b_headers,
    )
    assert unauth_dec.status_code == 403

    # 3. Candidate A tries to make reviewer decision -> 403 Forbidden
    cand_dec = await client.post(
        f"/api/v1/reviews/{flag_id}/decision",
        json={"decision": "accepted", "mandatory_rationale": "I approve my own skill"},
        headers=cand_a_headers,
    )
    assert cand_dec.status_code == 403

    # 4. Candidate B tries to submit clarification on Candidate A's application -> 403 Forbidden
    cand_b_clar = await client.post(
        f"/api/v1/applications/{app_id}/clarifications",
        json={"criterion_evidence_id": ce_id, "candidate_statement": "Not my application"},
        headers=cand_b_headers,
    )
    assert cand_b_clar.status_code == 403

    # 5. Unauthenticated request -> 401 Unauthorized
    anon_res = await client.get(f"/api/v1/reviews/{flag_id}")
    assert anon_res.status_code == 401
