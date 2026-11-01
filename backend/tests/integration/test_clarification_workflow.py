import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserRole, create_access_token
from app.db.models.audit import AuditEvent
from app.db.models.evaluation import CriterionEvidence, Evaluation
from app.db.models.review import CorrectionRequest, ReviewDecision
from tests.helpers import generate_sample_pdf


@pytest.mark.asyncio
async def test_complete_candidate_employer_clarification_workflow(
    client: AsyncClient, test_session: AsyncSession
):
    """
    Comprehensive integration test covering tests A through H:
    - Test A — Employer request: Employer requests clarification for one criterion; candidate retrieves exact question.
    - Test B — Candidate response: Candidate submits response; persisted in correction_requests; employer retrieves it.
    - Test C — Refresh persistence: Submitting a response survives page refreshes and refetches for both sides.
    - Test D — Authorization: Candidate A cannot submit on Candidate B's application; Employer B cannot view Employer A's application.
    - Test E — Decision: Employer accepts response; candidate sees accepted decision; audit event is recorded.
    - Test F — Rejection: Employer rejects response with rationale; candidate sees rejection; original Q&A is preserved.
    - Test G — Further clarification: Employer requests round 2 clarification; previous Q&A remain visible; candidate submits round 2 response.
    - Test H — Duplicate submissions: Rapid repeated submissions are handled idempotently.
    """
    # ── Setup accounts ──────────────────────────────────────────
    employer_a_id = str(uuid.uuid4())
    employer_b_id = str(uuid.uuid4())
    candidate_a_id = str(uuid.uuid4())
    candidate_b_id = str(uuid.uuid4())

    emp_a_token = create_access_token(subject=employer_a_id, role=UserRole.EMPLOYER_ADMIN)
    emp_b_token = create_access_token(subject=employer_b_id, role=UserRole.EMPLOYER_ADMIN)
    cand_a_token = create_access_token(subject=candidate_a_id, role=UserRole.CANDIDATE)
    cand_b_token = create_access_token(subject=candidate_b_id, role=UserRole.CANDIDATE)

    emp_a_headers = {"Authorization": f"Bearer {emp_a_token}"}
    emp_b_headers = {"Authorization": f"Bearer {emp_b_token}"}
    cand_a_headers = {"Authorization": f"Bearer {cand_a_token}"}
    cand_b_headers = {"Authorization": f"Bearer {cand_b_token}"}

    # ── Create Job Requisition by Employer A ────────────────────
    job_payload = {
        "title": "Full Stack API Engineer",
        "department": "Platform",
        "criteria": [
            {
                "name": "FastAPI",
                "category": "required",
                "description": "Production experience with FastAPI REST framework",
            },
            {
                "name": "PostgreSQL",
                "category": "required",
                "description": "Relational table modeling and SQL optimization",
            },
        ],
    }
    job_res = await client.post("/api/v1/jobs", json=job_payload, headers=emp_a_headers)
    assert job_res.status_code == 201
    job_data = job_res.json()
    job_id = job_data["id"]

    # ── Candidate A uploads resume & applies ─────────────────────
    resume_bytes = generate_sample_pdf(
        [
            "Candidate A Resume\nSkills: Python, REST APIs, PostgreSQL\nProjects: Library Inventory API (Python, SQLite)\nTable modeling with PostgreSQL."
        ]
    )
    doc_res = await client.post(
        "/api/v1/documents",
        files={"file": ("resume_a.pdf", resume_bytes, "application/pdf")},
        headers=cand_a_headers,
    )
    assert doc_res.status_code in (201, 202)
    doc_id = doc_res.json()["id"]

    app_res = await client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "primary_document_id": doc_id},
        headers=cand_a_headers,
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    # ── Trigger extraction and evaluation ────────────────────────
    ext_res = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=emp_a_headers)
    assert ext_res.status_code in (200, 202)

    eval_res = await client.post(
        "/api/v1/evaluations",
        json={"application_id": app_id},
        headers=emp_a_headers,
    )
    assert eval_res.status_code == 201
    eval_data = eval_res.json()
    crit_evals = eval_data["criteria_evaluations"]
    fastapi_crit = next(c for c in crit_evals if c["criterion_name"] == "FastAPI")
    fastapi_ce_id = fastapi_crit["criterion_evidence_id"]
    assert fastapi_ce_id is not None

    # ────────────────────────────────────────────────────────────
    # TEST A: Employer requests clarification
    # ────────────────────────────────────────────────────────────
    emp_question_1 = (
        "Your resume mentions that you created a REST API using Python. "
        "Could you clarify whether you used FastAPI or another framework? "
        "If possible, explain which parts of the project you implemented."
    )
    clar_res = await client.post(
        f"/api/v1/reviews/{fastapi_ce_id}/decision",
        json={
            "decision": "requested_clarification",
            "mandatory_rationale": emp_question_1,
        },
        headers=emp_a_headers,
    )
    assert clar_res.status_code in (200, 201)
    clar_data = clar_res.json()
    assert clar_data["decision"] == "requested_clarification"
    assert clar_data["mandatory_rationale"] == emp_question_1

    # Candidate A retrieves evaluation and sees the exact clarification question
    cand_eval_res = await client.get(
        f"/api/v1/evaluations/application/{app_id}",
        headers=cand_a_headers,
    )
    assert cand_eval_res.status_code == 200
    cand_eval = cand_eval_res.json()
    fastapi_item = next(c for c in cand_eval["criteria_evaluations"] if c["criterion_name"] == "FastAPI")
    assert fastapi_item["human_decision"] == "requested_clarification"
    assert fastapi_item["decision_rationale"] == emp_question_1
    assert len(fastapi_item["decisions"]) >= 1
    assert fastapi_item["decisions"][0]["decision"] == "requested_clarification"
    assert fastapi_item["decisions"][0]["mandatory_rationale"] == emp_question_1

    # ────────────────────────────────────────────────────────────
    # TEST D (Part 1): Authorization Checks
    # ────────────────────────────────────────────────────────────
    # Candidate B cannot submit clarification for Candidate A's application (403)
    cand_b_submit_res = await client.post(
        f"/api/v1/applications/{app_id}/clarifications",
        json={
            "criterion_evidence_id": fastapi_ce_id,
            "candidate_statement": "I am an imposter trying to clarify Candidate A's application.",
        },
        headers=cand_b_headers,
    )
    assert cand_b_submit_res.status_code == 403

    # Employer B cannot view Employer A's candidate evaluation (403)
    emp_b_get_res = await client.get(
        f"/api/v1/evaluations/application/{app_id}",
        headers=emp_b_headers,
    )
    assert emp_b_get_res.status_code == 403

    # ────────────────────────────────────────────────────────────
    # TEST B: Candidate submits clarification response
    # ────────────────────────────────────────────────────────────
    cand_answer_1 = (
        "I used Flask to develop the Library Inventory API. I have not used FastAPI in that project, "
        "but I have recently started learning it."
    )
    cand_submit_res = await client.post(
        f"/api/v1/applications/{app_id}/clarifications",
        json={
            "criterion_evidence_id": fastapi_ce_id,
            "candidate_statement": cand_answer_1,
        },
        headers=cand_a_headers,
    )
    assert cand_submit_res.status_code == 201
    submit_data = cand_submit_res.json()
    assert submit_data["candidate_statement"] == cand_answer_1
    assert submit_data["new_verification_state"] == "candidate_clarified"

    # Verify response is persisted in database
    db_cr = (
        await test_session.execute(
            select(CorrectionRequest).where(
                CorrectionRequest.criterion_evidence_id == uuid.UUID(fastapi_ce_id)
            )
        )
    ).scalars().all()
    assert len(db_cr) >= 1
    assert any(c.candidate_statement == cand_answer_1 for c in db_cr)

    # Employer retrieves evaluation and sees candidate's response
    emp_eval_res = await client.get(
        f"/api/v1/evaluations/application/{app_id}",
        headers=emp_a_headers,
    )
    assert emp_eval_res.status_code == 200
    emp_eval = emp_eval_res.json()
    fastapi_emp_item = next(c for c in emp_eval["criteria_evaluations"] if c["criterion_name"] == "FastAPI")
    assert fastapi_emp_item["verification_state"] == "candidate_clarified"
    assert len(fastapi_emp_item["clarifications"]) >= 1
    assert fastapi_emp_item["clarifications"][0]["candidate_statement"] == cand_answer_1

    # ────────────────────────────────────────────────────────────
    # TEST C: Refresh Persistence
    # ────────────────────────────────────────────────────────────
    # Multiple repeated fetches return identical thread history
    for _ in range(3):
        refresh_cand = await client.get(
            f"/api/v1/evaluations/application/{app_id}",
            headers=cand_a_headers,
        )
        refresh_emp = await client.get(
            f"/api/v1/evaluations/application/{app_id}",
            headers=emp_a_headers,
        )
        assert refresh_cand.status_code == 200
        assert refresh_emp.status_code == 200
        c_item = next(c for c in refresh_cand.json()["criteria_evaluations"] if c["criterion_name"] == "FastAPI")
        e_item = next(c for c in refresh_emp.json()["criteria_evaluations"] if c["criterion_name"] == "FastAPI")
        assert len(c_item["decisions"]) == len(e_item["decisions"])
        assert len(c_item["clarifications"]) == len(e_item["clarifications"])
        assert c_item["clarifications"][0]["candidate_statement"] == cand_answer_1
        assert e_item["clarifications"][0]["candidate_statement"] == cand_answer_1

    # ────────────────────────────────────────────────────────────
    # TEST G: Further Clarification (Round 2)
    # ────────────────────────────────────────────────────────────
    emp_question_2 = (
        "Thank you for confirming Flask. Have you deployed any asynchronous Python services, "
        "or worked with Starlette or Pydantic elsewhere?"
    )
    round2_q_res = await client.post(
        f"/api/v1/reviews/{fastapi_ce_id}/decision",
        json={
            "decision": "requested_clarification",
            "mandatory_rationale": emp_question_2,
        },
        headers=emp_a_headers,
    )
    assert round2_q_res.status_code in (200, 201)

    # Candidate sees previous Q&A AND the new question
    cand_round2_eval = (
        await client.get(
            f"/api/v1/evaluations/application/{app_id}",
            headers=cand_a_headers,
        )
    ).json()
    fastapi_r2 = next(c for c in cand_round2_eval["criteria_evaluations"] if c["criterion_name"] == "FastAPI")
    # Decisions now include both question 1 and question 2
    assert len(fastapi_r2["decisions"]) >= 2
    assert fastapi_r2["decisions"][0]["mandatory_rationale"] == emp_question_1
    assert fastapi_r2["decisions"][1]["mandatory_rationale"] == emp_question_2
    # Clarifications still preserves response 1
    assert len(fastapi_r2["clarifications"]) >= 1
    assert fastapi_r2["clarifications"][0]["candidate_statement"] == cand_answer_1

    # Candidate submits Round 2 response
    cand_answer_2 = (
        "I have used Pydantic for data validation in scripts, but have not deployed Starlette "
        "or asynchronous services in production."
    )
    cand_r2_submit = await client.post(
        f"/api/v1/applications/{app_id}/clarifications",
        json={
            "criterion_evidence_id": fastapi_ce_id,
            "candidate_statement": cand_answer_2,
        },
        headers=cand_a_headers,
    )
    assert cand_r2_submit.status_code == 201

    # Both questions and both answers are preserved in order
    cand_r2_eval_after = (
        await client.get(
            f"/api/v1/evaluations/application/{app_id}",
            headers=cand_a_headers,
        )
    ).json()
    fastapi_r2_after = next(c for c in cand_r2_eval_after["criteria_evaluations"] if c["criterion_name"] == "FastAPI")
    assert len(fastapi_r2_after["clarifications"]) == 2
    assert fastapi_r2_after["clarifications"][0]["candidate_statement"] == cand_answer_1
    assert fastapi_r2_after["clarifications"][1]["candidate_statement"] == cand_answer_2

    # ────────────────────────────────────────────────────────────
    # TEST H: Duplicate Submissions / Rapid Retries
    # ────────────────────────────────────────────────────────────
    # Rapid submission of duplicate decision
    dup_dec_1 = await client.post(
        f"/api/v1/reviews/{fastapi_ce_id}/decision",
        json={
            "decision": "rejected",
            "mandatory_rationale": "Candidate has no FastAPI or asynchronous framework experience.",
        },
        headers=emp_a_headers,
    )
    assert dup_dec_1.status_code in (200, 201)

    dup_dec_2 = await client.post(
        f"/api/v1/reviews/{fastapi_ce_id}/decision",
        json={
            "decision": "rejected",
            "mandatory_rationale": "Candidate has no FastAPI or asynchronous framework experience.",
        },
        headers=emp_a_headers,
    )
    assert dup_dec_2.status_code in (200, 201)
    assert dup_dec_1.json()["id"] == dup_dec_2.json()["id"]

    # ────────────────────────────────────────────────────────────
    # TEST F: Rejection preserves complete conversation
    # ────────────────────────────────────────────────────────────
    final_eval = (
        await client.get(
            f"/api/v1/evaluations/application/{app_id}",
            headers=cand_a_headers,
        )
    ).json()
    fastapi_final = next(c for c in final_eval["criteria_evaluations"] if c["criterion_name"] == "FastAPI")
    assert fastapi_final["verification_state"] == "human_rejected"
    assert fastapi_final["human_decision"] == "rejected"
    # All conversation history remains intact!
    assert len(fastapi_final["decisions"]) >= 3
    assert len(fastapi_final["clarifications"]) == 2
    assert fastapi_final["clarifications"][0]["candidate_statement"] == cand_answer_1
    assert fastapi_final["clarifications"][1]["candidate_statement"] == cand_answer_2

    # ────────────────────────────────────────────────────────────
    # TEST E: Acceptance & Audit Recording on Criterion 2 (PostgreSQL)
    # ────────────────────────────────────────────────────────────
    postgres_crit = next(c for c in crit_evals if c["criterion_name"] == "PostgreSQL")
    postgres_ce_id = postgres_crit["criterion_evidence_id"]

    # Employer accepts PostgreSQL
    accept_rationale = "Candidate demonstrated solid PostgreSQL table modeling in application and resume."
    accept_res = await client.post(
        f"/api/v1/reviews/{postgres_ce_id}/decision",
        json={
            "decision": "accepted",
            "mandatory_rationale": accept_rationale,
        },
        headers=emp_a_headers,
    )
    assert accept_res.status_code in (200, 201)

    # Verify candidate sees accepted status
    cand_post_eval = (
        await client.get(
            f"/api/v1/evaluations/application/{app_id}",
            headers=cand_a_headers,
        )
    ).json()
    postgres_item = next(c for c in cand_post_eval["criteria_evaluations"] if c["criterion_name"] == "PostgreSQL")
    assert postgres_item["verification_state"] == "human_verified"
    assert postgres_item["human_decision"] == "accepted"
    assert postgres_item["decision_rationale"] == accept_rationale

    # Verify AuditEvent was logged
    audit_events = (
        await test_session.execute(
            select(AuditEvent).where(
                AuditEvent.action == "REVIEW_DECISION_RECORDED",
                AuditEvent.resource_type == "review_decision",
            )
        )
    ).scalars().all()
    assert len(audit_events) >= 1
