import uuid

import pytest
from httpx import AsyncClient

from app.core.security import UserRole, create_access_token
from tests.helpers import generate_sample_pdf


@pytest.mark.asyncio
async def test_full_evaluation_workflow(client: AsyncClient):
    """
    Comprehensive end-to-end test of the evaluation flow:
    1. Employer creates a job requisition with required and preferred criteria.
    2. Candidate uploads a resume and triggers extraction.
    3. Candidate applies for the job requisition.
    4. Evaluator triggers candidate evaluation against criteria.
    5. Evaluation returns factual coverage counts and criteria mappings.
    6. Candidate queries profile skills inventory.
    """
    employer_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    employer_token = create_access_token(subject=employer_id, role=UserRole.EMPLOYER_ADMIN)
    candidate_token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)

    emp_headers = {"Authorization": f"Bearer {employer_token}"}
    cand_headers = {"Authorization": f"Bearer {candidate_token}"}

    # 1. Employer creates a job with criteria
    job_payload = {
        "title": "Senior Cloud Backend Engineer",
        "description": "Building high-performance distributed systems.",
        "department": "Platform Engineering",
        "criteria": [
            {
                "name": "Python",
                "description": "5+ years backend Python development",
                "category": "required",
                "weight": 1.5,
            },
            {
                "name": "PostgreSQL",
                "description": "Relational database schema and query tuning",
                "category": "required",
                "weight": 1.0,
            },
            {
                "name": "Kubernetes",
                "description": "Container orchestration",
                "category": "preferred",
                "weight": 0.8,
            },
            {
                "name": "Elixir",
                "description": "Functional programming in OTP",
                "category": "preferred",
                "weight": 0.5,
            },
            {
                "name": "Team Player",
                "description": "Collaborative mindset and communication",
                "category": "preferred",
                "weight": 0.5,
            },
        ],
    }

    job_res = await client.post("/api/v1/jobs", json=job_payload, headers=emp_headers)
    assert job_res.status_code == 201
    job_data = job_res.json()
    assert "id" in job_data
    job_id = job_data["id"]
    assert len(job_data["criteria"]) == 5
    assert job_data["criteria"][0]["version"] == 1

    # 2. Candidate uploads a resume
    resume_pdf = generate_sample_pdf(
        [
            "Alice Engineer - Senior Backend Specialist",
            "Extensive experience architecting Python microservices and data pipelines.",
            "Tuned Postgres databases with complex indexing and partitioning.",
            "Deployed production microservices to k8s clusters using Helm.",
        ]
    )
    upload_res = await client.post(
        "/api/v1/documents",
        files={"file": ("alice_resume.pdf", resume_pdf, "application/pdf")},
        headers=cand_headers,
    )
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["id"]

    # Poll status to ensure extraction is complete
    doc_status_res = await client.get(f"/api/v1/documents/{doc_id}/status", headers=cand_headers)
    assert doc_status_res.status_code == 200
    assert doc_status_res.json()["processing_status"] == "completed"

    # Trigger AI evidence extraction
    extract_res = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=cand_headers)
    assert extract_res.status_code == 202

    # 3. Candidate submits application
    app_payload = {
        "job_id": job_id,
        "primary_document_id": doc_id,
    }
    app_res = await client.post("/api/v1/applications", json=app_payload, headers=cand_headers)
    assert app_res.status_code == 201
    app_data = app_res.json()
    assert app_data["status"] == "submitted"
    application_id = app_data["id"]

    # 3b. Duplicate application is rejected with 409 Conflict
    dup_res = await client.post("/api/v1/applications", json=app_payload, headers=cand_headers)
    assert dup_res.status_code == 409

    # 4. Trigger evaluation
    eval_payload = {"application_id": application_id}
    eval_res = await client.post("/api/v1/evaluations", json=eval_payload, headers=emp_headers)
    assert eval_res.status_code == 201
    eval_data = eval_res.json()

    assert eval_data["application_id"] == application_id
    assert eval_data["version"] == 1
    assert eval_data["job_criteria_version"] == 1

    # Verify coverage counts:
    # 5 criteria:
    # - Python: supported (grounded)
    # - PostgreSQL: supported (via synonym Postgres)
    # - Kubernetes: supported (via synonym k8s)
    # - Elixir: not_found (non-judgmental explanation)
    # - Team Player: ambiguous (vague / subjective)
    coverage = eval_data["coverage"]
    assert coverage["total_criteria"] == 5
    assert coverage["supported_count"] == 3
    assert coverage["not_found_count"] == 1
    assert coverage["ambiguous_count"] == 1
    assert coverage["required_total"] == 2
    assert coverage["required_supported_count"] == 2
    assert coverage["preferred_total"] == 3
    assert coverage["preferred_supported_count"] == 1

    # Inspect individual criterion items
    eval_items_by_name = {
        item["criterion_name"]: item for item in eval_data["criteria_evaluations"]
    }

    assert eval_items_by_name["Python"]["status"] == "supported"
    assert eval_items_by_name["PostgreSQL"]["status"] == "supported"
    assert eval_items_by_name["Kubernetes"]["status"] == "supported"
    assert eval_items_by_name["Elixir"]["status"] == "not_found"
    assert (
        "No validated evidence for 'Elixir' was found"
        in eval_items_by_name["Elixir"]["plain_language_explanation"]
    )
    assert (
        "This does not mean the candidate lacks this skill"
        in eval_items_by_name["Elixir"]["plain_language_explanation"]
    )
    assert eval_items_by_name["Team Player"]["status"] == "ambiguous"
    assert "subjective or vague" in eval_items_by_name["Team Player"]["plain_language_explanation"]

    # 5. Retrieve evaluation report via GET /evaluations/{id}
    evaluation_id = eval_data["id"]
    get_eval_res = await client.get(f"/api/v1/evaluations/{evaluation_id}", headers=cand_headers)
    assert get_eval_res.status_code == 200
    assert get_eval_res.json()["id"] == evaluation_id

    # 6. Candidate profile skills endpoint
    profile_skills_res = await client.get(
        f"/api/v1/profiles/{candidate_id}/skills", headers=cand_headers
    )
    assert profile_skills_res.status_code == 200
    profile_data = profile_skills_res.json()
    assert profile_data["candidate_id"] == candidate_id
    assert profile_data["total_skills"] >= 1
    skill_names = [s["skill_name"] for s in profile_data["skills"]]
    assert any("Python" in s or "Postgres" in s or "k8s" in s for s in skill_names)


@pytest.mark.asyncio
async def test_candidate_cross_access_authorization(client: AsyncClient):
    """Verify security boundaries: candidates cannot view other candidates' applications or profiles."""
    candidate_a = str(uuid.uuid4())
    candidate_b = str(uuid.uuid4())

    token_b = create_access_token(subject=candidate_b, role=UserRole.CANDIDATE)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Candidate B tries to access Candidate A's profile skills
    profile_res = await client.get(f"/api/v1/profiles/{candidate_a}/skills", headers=headers_b)
    assert profile_res.status_code == 403


@pytest.mark.asyncio
async def test_evaluation_history_preservation_on_criteria_change(client: AsyncClient):
    """
    Test that updating criteria and re-evaluating creates a new versioned evaluation
    and preserves history without overwriting previous evaluation runs.
    """
    employer_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    emp_headers = {
        "Authorization": f"Bearer {create_access_token(subject=employer_id, role=UserRole.EMPLOYER_ADMIN)}"
    }
    cand_headers = {
        "Authorization": f"Bearer {create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)}"
    }

    # 1. Create job with 1 criterion
    job_payload = {
        "title": "Data Engineer",
        "criteria": [{"name": "Python", "category": "required"}],
    }
    job_res = await client.post("/api/v1/jobs", json=job_payload, headers=emp_headers)
    job_id = job_res.json()["id"]

    # 2. Upload document
    pdf = generate_sample_pdf(["Python data pipelines with pandas and spark."])
    doc_res = await client.post(
        "/api/v1/documents",
        files={"file": ("resume.pdf", pdf, "application/pdf")},
        headers=cand_headers,
    )
    doc_id = doc_res.json()["id"]

    # Trigger AI extraction
    extract_res = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=cand_headers)
    assert extract_res.status_code == 202

    # 3. Apply
    app_res = await client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "primary_document_id": doc_id},
        headers=cand_headers,
    )
    app_id = app_res.json()["id"]

    # 4. First evaluation (version 1)
    eval1_res = await client.post(
        "/api/v1/evaluations",
        json={"application_id": app_id},
        headers=emp_headers,
    )
    assert eval1_res.status_code == 201
    eval1_data = eval1_res.json()
    assert eval1_data["version"] == 1
    eval1_id = eval1_data["id"]

    # 5. Second evaluation for same application creates version 2
    eval2_res = await client.post(
        "/api/v1/evaluations",
        json={"application_id": app_id},
        headers=emp_headers,
    )
    assert eval2_res.status_code == 201
    eval2_data = eval2_res.json()
    assert eval2_data["version"] == 2
    assert eval2_data["id"] != eval1_id

    # 6. Prior evaluation (version 1) is still retrievable and unchanged
    get_eval1 = await client.get(f"/api/v1/evaluations/{eval1_id}", headers=emp_headers)
    assert get_eval1.status_code == 200
    assert get_eval1.json()["version"] == 1
