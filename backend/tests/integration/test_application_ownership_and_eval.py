import uuid

import pytest
from httpx import AsyncClient

from app.core.security import UserRole, create_access_token
from tests.helpers import generate_sample_pdf


@pytest.mark.asyncio
async def test_application_ownership_and_evaluation_tenant_isolation(client: AsyncClient):
    """
    Verify complete tenant isolation and access control for applications and evaluations:
    1. Owning employer creates job.
    2. Candidate uploads resume, extracts skills, and submits application.
    3. Candidate can view their own application.
    4. Unrelated candidate cannot view application (403).
    5. Owning employer can view application (200).
    6. Unrelated employer cannot view application (403).
    7. Candidate cannot trigger evaluation (403).
    8. Unrelated employer cannot trigger evaluation (403).
    9. Owning employer evaluating non-existent application returns 404.
    10. Owning employer can trigger evaluation on completed extraction (201).
    11. Owning employer can retrieve evaluation (200).
    12. Unrelated employer cannot retrieve evaluation (403).
    """
    owner_employer_id = str(uuid.uuid4())
    other_employer_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    other_candidate_id = str(uuid.uuid4())

    owner_token = create_access_token(
        subject=owner_employer_id,
        role=UserRole.EMPLOYER_ADMIN,
        employer_id="tenant-alpha",
    )
    other_owner_token = create_access_token(
        subject=other_employer_id,
        role=UserRole.EMPLOYER_ADMIN,
        employer_id="tenant-beta",
    )
    candidate_token = create_access_token(
        subject=candidate_id,
        role=UserRole.CANDIDATE,
    )
    other_candidate_token = create_access_token(
        subject=other_candidate_id,
        role=UserRole.CANDIDATE,
    )

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    other_owner_headers = {"Authorization": f"Bearer {other_owner_token}"}
    cand_headers = {"Authorization": f"Bearer {candidate_token}"}
    other_cand_headers = {"Authorization": f"Bearer {other_candidate_token}"}

    # 1. Owning employer creates a job
    job_payload = {
        "title": "Staff Backend Engineer",
        "description": "Distributed systems engineering",
        "department": "Platform",
        "criteria": [
            {
                "name": "Python",
                "description": "5+ years backend Python development",
                "category": "required",
                "weight": 1.0,
            }
        ],
    }
    job_res = await client.post("/api/v1/jobs", json=job_payload, headers=owner_headers)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 2. Candidate uploads resume and triggers extraction
    resume_pdf = generate_sample_pdf(
        ["Senior Python Developer with 8 years of experience building scalable systems."]
    )
    upload_res = await client.post(
        "/api/v1/documents",
        files={"file": ("resume.pdf", resume_pdf, "application/pdf")},
        headers=cand_headers,
    )
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["id"]

    extract_res = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=cand_headers)
    assert extract_res.status_code == 202

    # 3. Candidate submits application
    app_payload = {
        "job_id": job_id,
        "primary_document_id": doc_id,
    }
    app_res = await client.post("/api/v1/applications", json=app_payload, headers=cand_headers)
    assert app_res.status_code == 201
    application_id = app_res.json()["id"]

    # 4. Candidate can view their own application (200)
    cand_get_res = await client.get(f"/api/v1/applications/{application_id}", headers=cand_headers)
    assert cand_get_res.status_code == 200
    assert cand_get_res.json()["id"] == application_id

    # 5. Unrelated candidate cannot view application (403)
    other_cand_get_res = await client.get(
        f"/api/v1/applications/{application_id}", headers=other_cand_headers
    )
    assert other_cand_get_res.status_code == 403

    # 6. Owning employer can retrieve application (200)
    owner_get_res = await client.get(
        f"/api/v1/applications/{application_id}", headers=owner_headers
    )
    assert owner_get_res.status_code == 200
    assert owner_get_res.json()["id"] == application_id

    # 7. Unrelated employer cannot retrieve application (403)
    other_owner_get_res = await client.get(
        f"/api/v1/applications/{application_id}", headers=other_owner_headers
    )
    assert other_owner_get_res.status_code == 403

    # 8. Candidate cannot trigger evaluation (403)
    eval_payload = {"application_id": application_id}
    cand_eval_res = await client.post(
        "/api/v1/evaluations", json=eval_payload, headers=cand_headers
    )
    assert cand_eval_res.status_code == 403

    # 9. Unrelated employer cannot trigger evaluation (403)
    other_eval_res = await client.post(
        "/api/v1/evaluations", json=eval_payload, headers=other_owner_headers
    )
    assert other_eval_res.status_code == 403

    # 10. Owning employer evaluating non-existent application returns 404
    non_existent_app_id = str(uuid.uuid4())
    missing_eval_res = await client.post(
        "/api/v1/evaluations",
        json={"application_id": non_existent_app_id},
        headers=owner_headers,
    )
    assert missing_eval_res.status_code == 404

    # 11. Owning employer triggers evaluation successfully (201)
    eval_res = await client.post("/api/v1/evaluations", json=eval_payload, headers=owner_headers)
    assert eval_res.status_code == 201
    eval_data = eval_res.json()
    evaluation_id = eval_data["id"]
    assert eval_data["application_id"] == application_id
    assert eval_data["coverage"]["supported_count"] == 1

    # 12. Owning employer can get evaluation (200)
    eval_get_res = await client.get(f"/api/v1/evaluations/{evaluation_id}", headers=owner_headers)
    assert eval_get_res.status_code == 200

    # 13. Unrelated employer cannot get evaluation (403)
    other_eval_get_res = await client.get(
        f"/api/v1/evaluations/{evaluation_id}", headers=other_owner_headers
    )
    assert other_eval_get_res.status_code == 403


@pytest.mark.asyncio
async def test_evaluation_rejected_when_extraction_not_completed(client: AsyncClient):
    """
    Verify that an application whose document has not completed AI extraction
    is rejected with 422 Unprocessable Entity when evaluated.
    """
    owner_employer_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    owner_token = create_access_token(
        subject=owner_employer_id,
        role=UserRole.EMPLOYER_ADMIN,
        employer_id="tenant-alpha",
    )
    candidate_token = create_access_token(
        subject=candidate_id,
        role=UserRole.CANDIDATE,
    )

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    cand_headers = {"Authorization": f"Bearer {candidate_token}"}

    # Create job
    job_payload = {
        "title": "Junior Python Developer",
        "description": "Python web services",
        "department": "Engineering",
        "criteria": [
            {
                "name": "Python",
                "description": "Python fundamentals",
                "category": "required",
                "weight": 1.0,
            }
        ],
    }
    job_res = await client.post("/api/v1/jobs", json=job_payload, headers=owner_headers)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # Candidate uploads resume without triggering AI extraction
    resume_pdf = generate_sample_pdf(["Python developer"])
    upload_res = await client.post(
        "/api/v1/documents",
        files={"file": ("resume.pdf", resume_pdf, "application/pdf")},
        headers=cand_headers,
    )
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["id"]

    # Candidate submits application
    app_payload = {
        "job_id": job_id,
        "primary_document_id": doc_id,
    }
    app_res = await client.post("/api/v1/applications", json=app_payload, headers=cand_headers)
    assert app_res.status_code == 201
    application_id = app_res.json()["id"]

    # Owning employer triggers evaluation before extraction completes -> 422
    eval_res = await client.post(
        "/api/v1/evaluations",
        json={"application_id": application_id},
        headers=owner_headers,
    )
    assert eval_res.status_code == 422
    assert "has not completed evidence extraction" in eval_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_application_review_flags_creation_and_tenant_isolation(client: AsyncClient):
    """
    Verify that an application retrievable by its authorized employer can be used
    to create review flags, and that tenant isolation is strictly enforced:
    1. Owning employer creates a job with criteria.
    2. Candidate uploads resume, extracts skills, and submits application.
    3. Owning employer retrieves application (GET /api/v1/applications/{id} -> 200).
    4. Owning employer evaluates application (POST /api/v1/evaluations -> 201).
    5. Owning employer creates review flags (POST /api/v1/review-flags -> 201).
    6. Unrelated employer cannot create review flags (POST /api/v1/review-flags -> 403).
    7. Candidate cannot create review flags (POST /api/v1/review-flags -> 403).
    8. Nonexistent application returns 404.
    """
    owner_employer_id = str(uuid.uuid4())
    other_employer_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    owner_token = create_access_token(
        subject=owner_employer_id,
        role=UserRole.EMPLOYER_ADMIN,
        employer_id="tenant-alpha",
    )
    other_owner_token = create_access_token(
        subject=other_employer_id,
        role=UserRole.EMPLOYER_ADMIN,
        employer_id="tenant-beta",
    )
    candidate_token = create_access_token(
        subject=candidate_id,
        role=UserRole.CANDIDATE,
    )

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    other_owner_headers = {"Authorization": f"Bearer {other_owner_token}"}
    cand_headers = {"Authorization": f"Bearer {candidate_token}"}

    # 1. Create job
    job_payload = {
        "title": "Lead Software Engineer",
        "description": "Distributed architecture",
        "department": "Platform",
        "criteria": [
            {
                "name": "Python",
                "description": "Python expertise",
                "category": "required",
                "weight": 1.0,
            },
            {
                "name": "Rust",
                "description": "Systems programming in Rust",
                "category": "required",
                "weight": 1.0,
            },
        ],
    }
    job_res = await client.post("/api/v1/jobs", json=job_payload, headers=owner_headers)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 2. Upload resume and extract
    resume_pdf = generate_sample_pdf(["Python developer with backend focus."])
    upload_res = await client.post(
        "/api/v1/documents",
        files={"file": ("resume.pdf", resume_pdf, "application/pdf")},
        headers=cand_headers,
    )
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["id"]

    extract_res = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=cand_headers)
    assert extract_res.status_code == 202

    # 3. Submit application
    app_payload = {"job_id": job_id, "primary_document_id": doc_id}
    app_res = await client.post("/api/v1/applications", json=app_payload, headers=cand_headers)
    assert app_res.status_code == 201
    application_id = app_res.json()["id"]

    # 4. Owning employer retrieves application (200)
    app_get_res = await client.get(f"/api/v1/applications/{application_id}", headers=owner_headers)
    assert app_get_res.status_code == 200
    assert app_get_res.json()["id"] == application_id

    # 5. Owning employer evaluates application (201)
    eval_res = await client.post(
        "/api/v1/evaluations",
        json={"application_id": application_id},
        headers=owner_headers,
    )
    assert eval_res.status_code == 201

    # 6. Owning employer creates review flags on the retrievable application (201)
    flags_payload = {
        "application_id": application_id,
        "flag_preferred": False,
    }
    flags_res = await client.post("/api/v1/review-flags", json=flags_payload, headers=owner_headers)
    assert flags_res.status_code == 201
    flags_data = flags_res.json()
    assert flags_data["application_id"] == application_id
    assert flags_data["total_flagged"] >= 1

    # 7. Unrelated employer cannot create review flags on this application (403)
    other_flags_res = await client.post(
        "/api/v1/review-flags", json=flags_payload, headers=other_owner_headers
    )
    assert other_flags_res.status_code == 403

    # 8. Candidate cannot create review flags (403)
    cand_flags_res = await client.post(
        "/api/v1/review-flags", json=flags_payload, headers=cand_headers
    )
    assert cand_flags_res.status_code == 403

    # 9. Nonexistent application ID returns 404
    missing_flags_res = await client.post(
        "/api/v1/review-flags",
        json={"application_id": str(uuid.uuid4()), "flag_preferred": False},
        headers=owner_headers,
    )
    assert missing_flags_res.status_code == 404


@pytest.mark.asyncio
async def test_candidate_clarification_submission_and_ownership(client: AsyncClient):
    """
    Verify candidate clarification submission, ownership isolation, and evidence state:
    1. Correct candidate submits clarification successfully (201).
    2. Different candidate cannot submit clarification (403).
    3. Employer cannot submit candidate clarification (403).
    4. Invalid application ID returns 404.
    5. Candidate-provided evidence remains unverified until reviewer approval.
    """
    owner_employer_id = str(uuid.uuid4())
    candidate_a_id = str(uuid.uuid4())
    candidate_b_id = str(uuid.uuid4())

    owner_token = create_access_token(
        subject=owner_employer_id,
        role=UserRole.EMPLOYER_ADMIN,
        employer_id="tenant-alpha",
    )
    cand_a_token = create_access_token(
        subject=candidate_a_id,
        role=UserRole.CANDIDATE,
    )
    cand_b_token = create_access_token(
        subject=candidate_b_id,
        role=UserRole.CANDIDATE,
    )

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    cand_a_headers = {"Authorization": f"Bearer {cand_a_token}"}
    cand_b_headers = {"Authorization": f"Bearer {cand_b_token}"}

    # 1. Employer creates job
    job_payload = {
        "title": "Principal Distributed Systems Engineer",
        "description": "Distributed storage architecture",
        "department": "Platform",
        "criteria": [
            {
                "name": "Python",
                "description": "Python expertise",
                "category": "required",
                "weight": 1.0,
            },
            {
                "name": "Rust",
                "description": "Systems programming in Rust",
                "category": "required",
                "weight": 1.0,
            },
        ],
    }
    job_res = await client.post("/api/v1/jobs", json=job_payload, headers=owner_headers)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 2. Candidate A uploads resume & applies
    resume_pdf = generate_sample_pdf(["Senior Backend Engineer with Python microservices."])
    upload_res = await client.post(
        "/api/v1/documents",
        files={"file": ("resume.pdf", resume_pdf, "application/pdf")},
        headers=cand_a_headers,
    )
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["id"]

    extract_res = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=cand_a_headers)
    assert extract_res.status_code == 202

    app_res = await client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "primary_document_id": doc_id},
        headers=cand_a_headers,
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    # 3. Employer evaluates application and creates review flags
    eval_res = await client.post(
        "/api/v1/evaluations",
        json={"application_id": app_id},
        headers=owner_headers,
    )
    assert eval_res.status_code == 201

    flags_res = await client.post(
        "/api/v1/review-flags",
        json={"application_id": app_id, "flag_preferred": False},
        headers=owner_headers,
    )
    assert flags_res.status_code == 201
    flags_data = flags_res.json()
    assert len(flags_data["flags"]) >= 1
    flag_id = flags_data["flags"][0]["id"]
    target_ce_id = flags_data["flags"][0]["criterion_evidence_id"]

    # 4. Correct candidate submits clarification successfully (201)
    clarification_payload = {
        "criterion_evidence_id": target_ce_id,
        "candidate_statement": "I contributed to open-source Rust crates and built a Raft consensus prototype.",
    }
    clarify_res = await client.post(
        f"/api/v1/applications/{app_id}/clarifications",
        json=clarification_payload,
        headers=cand_a_headers,
    )
    assert clarify_res.status_code == 201
    clarify_data = clarify_res.json()
    assert clarify_data["application_id"] == app_id
    assert clarify_data["candidate_id"] == candidate_a_id
    assert clarify_data["status"] == "submitted"
    assert clarify_data["new_verification_state"] == "candidate_clarified"

    # 5. Candidate-provided evidence remains unverified until reviewer approval
    flag_detail_res = await client.get(f"/api/v1/reviews/{flag_id}", headers=owner_headers)
    assert flag_detail_res.status_code == 200
    assert flag_detail_res.json()["verification_state"] == "candidate_clarified"
    assert flag_detail_res.json()["verification_state"] != "human_verified"

    # 6. Different candidate cannot submit clarification (403)
    other_cand_res = await client.post(
        f"/api/v1/applications/{app_id}/clarifications",
        json=clarification_payload,
        headers=cand_b_headers,
    )
    assert other_cand_res.status_code == 403

    # 7. Employer cannot submit candidate clarification (403)
    emp_clarify_res = await client.post(
        f"/api/v1/applications/{app_id}/clarifications",
        json=clarification_payload,
        headers=owner_headers,
    )
    assert emp_clarify_res.status_code == 403

    # 8. Invalid application ID returns 404
    missing_app_id = str(uuid.uuid4())
    missing_clarify_res = await client.post(
        f"/api/v1/applications/{missing_app_id}/clarifications",
        json=clarification_payload,
        headers=cand_a_headers,
    )
    assert missing_clarify_res.status_code == 404


@pytest.mark.asyncio
async def test_candidate_python_and_sql_clarifications_regression(client: AsyncClient):
    """
    Regression test covering:
    1. Candidate submits Python clarification successfully (201).
    2. Candidate submits SQL clarification successfully on same application (201).
    3. Candidate cannot submit clarification for another candidate's application (403).
    4. Invalid criterion evidence ID is rejected with 404.
    5. Nonexistent application (including typo UUID with 'f' instead of 'd') returns 404.
    """
    employer_id = str(uuid.uuid4())
    candidate_a_id = "613f06ab-dc81-4711-a44f-d49ed6d5ec47"
    candidate_b_id = str(uuid.uuid4())

    employer_token = create_access_token(
        subject=employer_id,
        role=UserRole.EMPLOYER_ADMIN,
        employer_id="clearhire-demo",
    )
    cand_a_token = create_access_token(
        subject=candidate_a_id,
        role=UserRole.CANDIDATE,
        email="anish@gmail.com",
    )
    cand_b_token = create_access_token(
        subject=candidate_b_id,
        role=UserRole.CANDIDATE,
        email="other@gmail.com",
    )

    employer_headers = {"Authorization": f"Bearer {employer_token}"}
    cand_a_headers = {"Authorization": f"Bearer {cand_a_token}"}
    cand_b_headers = {"Authorization": f"Bearer {cand_b_token}"}

    # 1. Employer creates a job requiring both Python and SQL
    job_payload = {
        "title": "Junior Python Developer",
        "description": "Backend services using Python and SQL databases",
        "department": "Engineering",
        "criteria": [
            {
                "name": "Python",
                "description": "Practical experience with Python",
                "category": "required",
                "weight": 1.0,
            },
            {
                "name": "SQL",
                "description": "Relational database querying with SQL",
                "category": "required",
                "weight": 1.0,
            },
        ],
    }
    job_res = await client.post("/api/v1/jobs", json=job_payload, headers=employer_headers)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 2. Candidate A uploads resume & applies
    resume_pdf = generate_sample_pdf(
        ["Programming: Python, SQL, basic Java. Built database-driven web services."]
    )
    upload_res = await client.post(
        "/api/v1/documents",
        files={"file": ("resume.pdf", resume_pdf, "application/pdf")},
        headers=cand_a_headers,
    )
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["id"]

    extract_res = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=cand_a_headers)
    assert extract_res.status_code == 202

    app_res = await client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "primary_document_id": doc_id},
        headers=cand_a_headers,
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    # 3. Employer evaluates application and flags ambiguous criteria
    eval_res = await client.post(
        "/api/v1/evaluations",
        json={"application_id": app_id},
        headers=employer_headers,
    )
    assert eval_res.status_code == 201
    assert eval_res.json()["application_id"] == app_id

    flags_res = await client.post(
        "/api/v1/review-flags",
        json={"application_id": app_id, "flag_preferred": False},
        headers=employer_headers,
    )
    assert flags_res.status_code == 201
    flags = flags_res.json()["flags"]
    assert len(flags) >= 2

    # Map flags to Python and SQL criteria by checking detail or order
    ce_ids = [f["criterion_evidence_id"] for f in flags if f.get("criterion_evidence_id")]
    python_ce_id = ce_ids[0]
    sql_ce_id = ce_ids[1]

    # 4. Candidate A submits Python clarification successfully (201)
    py_payload = {
        "criterion_evidence_id": python_ce_id,
        "candidate_statement": "I have practical experience developing backend microservices in Python.",
    }
    py_clarify_res = await client.post(
        f"/api/v1/applications/{app_id}/clarifications",
        json=py_payload,
        headers=cand_a_headers,
    )
    assert py_clarify_res.status_code == 201
    py_data = py_clarify_res.json()
    assert py_data["application_id"] == app_id
    assert py_data["candidate_id"] == candidate_a_id
    assert py_data["criterion_evidence_id"] == python_ce_id
    assert py_data["status"] == "submitted"
    assert py_data["new_verification_state"] == "candidate_clarified"

    # 5. Candidate A submits SQL clarification successfully on the same application (201)
    sql_payload = {
        "criterion_evidence_id": sql_ce_id,
        "candidate_statement": "I have extensive SQL experience writing complex queries and schema design.",
    }
    sql_clarify_res = await client.post(
        f"/api/v1/applications/{app_id}/clarifications",
        json=sql_payload,
        headers=cand_a_headers,
    )
    assert sql_clarify_res.status_code == 201
    sql_data = sql_clarify_res.json()
    assert sql_data["application_id"] == app_id
    assert sql_data["candidate_id"] == candidate_a_id
    assert sql_data["criterion_evidence_id"] == sql_ce_id
    assert sql_data["status"] == "submitted"
    assert sql_data["new_verification_state"] == "candidate_clarified"

    # 6. Candidate B cannot submit clarification for Candidate A's application (403)
    other_cand_res = await client.post(
        f"/api/v1/applications/{app_id}/clarifications",
        json=sql_payload,
        headers=cand_b_headers,
    )
    assert other_cand_res.status_code == 403
    assert (
        "Candidates may only submit clarifications for their own applications"
        in (other_cand_res.json()["error"]["message"])
    )

    # 7. Invalid criterion evidence ID is rejected (404)
    fake_ce_id = str(uuid.uuid4())
    invalid_ce_payload = {
        "criterion_evidence_id": fake_ce_id,
        "candidate_statement": "Valid statement with fake criterion evidence ID.",
    }
    invalid_ce_res = await client.post(
        f"/api/v1/applications/{app_id}/clarifications",
        json=invalid_ce_payload,
        headers=cand_a_headers,
    )
    assert invalid_ce_res.status_code == 404
    assert f"CriterionEvidence {fake_ce_id} not found." in invalid_ce_res.json()["error"]["message"]

    # 8. Nonexistent application (such as the typo UUID ending with 'f' instead of 'd') returns 404
    typo_app_id = "24f5f19e-075c-4430-8f89-31b7f2f68330"
    typo_res = await client.post(
        f"/api/v1/applications/{typo_app_id}/clarifications",
        json=sql_payload,
        headers=cand_a_headers,
    )
    assert typo_res.status_code == 404
    assert f"Application {typo_app_id} not found." in typo_res.json()["error"]["message"]
