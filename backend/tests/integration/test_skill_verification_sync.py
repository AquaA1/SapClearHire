import re
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserRole, create_access_token
from app.db.models.audit import AuditEvent
from app.db.models.evaluation import CriterionEvidence, Evaluation
from app.db.models.review import ReviewDecision
from tests.helpers import generate_sample_pdf


@pytest.mark.asyncio
async def test_skill_verification_lifecycle_and_candidate_synchronization(
    client: AsyncClient, test_session: AsyncSession
):
    """
    Phase 6 Single-Account End-to-End Verification Test:
    1. Candidate uploads resume containing Python, FastAPI, and SQL.
    2. AI extracts all 3 skills.
    3. Confirm each skill has real source excerpt and page reference.
    4. Confirm evidence validation results are persisted.
    5. Employer/admin opens same application.
    6. Employer/admin accepts Python with mandatory rationale.
    7. Backend persists decision against exact Python claim (CriterionEvidence.id).
    8. Candidate application page refetches its data.
    9. Python displays Human Verified (verification_state == 'human_verified', human_decision == 'accepted').
    10. FastAPI and SQL remain in previous review states ('unverified').
    11. Refresh / refetch.
    12. Python still displays Human Verified.
    13. Employer/admin rejects SQL with rationale containing internal notes:
        'Does not meet enterprise criteria. [Internal Notes: candidate lacks distributed db experience]'
    14. Candidate sees rejection status ('human_rejected') and permitted explanation (internal notes excluded).
    15. Verify audit history preserves both decisions and audit trail entries.
    """
    employer_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    emp_token = create_access_token(subject=employer_id, role=UserRole.EMPLOYER_ADMIN)
    cand_token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)

    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    cand_headers = {"Authorization": f"Bearer {cand_token}"}

    # Step 0: Employer creates job with 3 criteria: Python, FastAPI, SQL
    job_payload = {
        "title": "Backend Systems Engineer",
        "department": "Core Platform",
        "criteria": [
            {
                "name": "Python",
                "category": "required",
                "description": "Production Python development experience",
            },
            {
                "name": "FastAPI",
                "category": "required",
                "description": "High performance REST APIs with FastAPI",
            },
            {
                "name": "SQL",
                "category": "required",
                "description": "Relational schema design and SQL query optimization",
            },
        ],
    }
    job_res = await client.post("/api/v1/jobs", json=job_payload, headers=emp_headers)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # Step 1: Candidate uploads resume containing Python, FastAPI, SQL
    resume_pdf = generate_sample_pdf(
        [
            "Jane Developer - Senior Software Engineer",
            "5+ years developing robust backend services using Python 3.12.",
            "Designed and deployed async microservices using FastAPI framework.",
            "Handled database migrations, indexing and complex SQL queries on enterprise systems.",
        ]
    )
    doc_res = await client.post(
        "/api/v1/documents",
        files={"file": ("jane_resume.pdf", resume_pdf, "application/pdf")},
        headers=cand_headers,
    )
    assert doc_res.status_code == 202
    doc_id = doc_res.json()["id"]

    # Trigger extraction run
    ext_res = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=cand_headers)
    assert ext_res.status_code == 202

    # Verify structured profile skills extraction
    profile_res = await client.get(f"/api/v1/documents/{doc_id}/extraction-results", headers=cand_headers)
    assert profile_res.status_code == 200
    skills_profile = profile_res.json()["skills"]
    extracted_names = [s["skill_name"].lower() for s in skills_profile]
    assert "python" in extracted_names
    assert "fastapi" in extracted_names
    assert "sql" in extracted_names

    # Candidate submits application
    app_res = await client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "primary_document_id": doc_id},
        headers=cand_headers,
    )
    assert app_res.status_code == 201
    application_id = app_res.json()["id"]

    # Trigger evaluation against job criteria
    eval_res = await client.post(
        "/api/v1/evaluations",
        json={"application_id": application_id},
        headers=emp_headers,
    )
    assert eval_res.status_code == 201
    eval_data = eval_res.json()
    eval_id = eval_data["id"]

    # Step 2 & 3: Confirm each skill has real source excerpt and page reference
    crit_evals = {ce["criterion_name"]: ce for ce in eval_data["criteria_evaluations"]}
    assert "Python" in crit_evals
    assert "FastAPI" in crit_evals
    assert "SQL" in crit_evals

    for skill_name in ["Python", "FastAPI", "SQL"]:
        ce = crit_evals[skill_name]
        assert ce["status"] == "supported"
        assert ce["source_excerpt"] is not None and len(ce["source_excerpt"]) > 0
        assert ce["source_page"] is not None and ce["source_page"] >= 1
        assert ce["criterion_evidence_id"] is not None
        # Initially, none have been human verified
        assert ce["verification_state"] == "unverified"
        assert ce["human_decision"] is None

    # Step 4: Confirm evidence validation results are persisted in DB
    python_ce_id = crit_evals["Python"]["criterion_evidence_id"]
    fastapi_ce_id = crit_evals["FastAPI"]["criterion_evidence_id"]
    sql_ce_id = crit_evals["SQL"]["criterion_evidence_id"]

    async with test_session.begin():
        db_ev = await test_session.execute(
            select(CriterionEvidence).where(CriterionEvidence.evaluation_id == uuid.UUID(eval_id))
        )
        persisted_items = db_ev.scalars().all()
        assert len(persisted_items) == 3

    # Step 5 & 6: Employer/admin accepts Python with rationale
    python_accept_rationale = (
        "Candidate demonstrates 5+ years verified production experience in Python."
    )
    decision_res1 = await client.post(
        f"/api/v1/reviews/{python_ce_id}/decision",
        json={
            "decision": "accepted",
            "mandatory_rationale": python_accept_rationale,
        },
        headers=emp_headers,
    )
    assert decision_res1.status_code == 201
    decision_data1 = decision_res1.json()
    assert decision_data1["decision"] == "accepted"
    assert decision_data1["new_verification_state"] == "human_verified"

    # Step 7: Backend persists decision against exact Python claim (CriterionEvidence.id)
    test_session.expire_all()
    async with test_session.begin():
        py_db = await test_session.execute(
            select(CriterionEvidence).where(CriterionEvidence.id == uuid.UUID(python_ce_id))
        )
        py_record = py_db.scalar_one()
        assert py_record.verification_state.value == "human_verified"

    # Step 8 & 9: Candidate application page refetches its data
    cand_eval_res1 = await client.get(
        f"/api/v1/evaluations/application/{application_id}",
        headers=cand_headers,
    )
    assert cand_eval_res1.status_code == 200
    cand_eval_data1 = cand_eval_res1.json()
    cand_crit1 = {ce["criterion_name"]: ce for ce in cand_eval_data1["criteria_evaluations"]}

    # Python displays Human Verified
    assert cand_crit1["Python"]["verification_state"] == "human_verified"
    assert cand_crit1["Python"]["human_decision"] == "accepted"
    assert cand_crit1["Python"]["decision_rationale"] == python_accept_rationale
    assert cand_crit1["Python"]["decided_at"] is not None

    # Step 10: FastAPI and SQL remain in previous review states
    assert cand_crit1["FastAPI"]["verification_state"] == "unverified"
    assert cand_crit1["FastAPI"]["human_decision"] is None
    assert cand_crit1["SQL"]["verification_state"] == "unverified"
    assert cand_crit1["SQL"]["human_decision"] is None

    # Step 11 & 12: Refresh / refetch -> Python still displays Human Verified
    cand_eval_res2 = await client.get(
        f"/api/v1/evaluations/application/{application_id}",
        headers=cand_headers,
    )
    assert cand_eval_res2.status_code == 200
    cand_eval_data2 = cand_eval_res2.json()
    cand_crit2 = {ce["criterion_name"]: ce for ce in cand_eval_data2["criteria_evaluations"]}
    assert cand_crit2["Python"]["verification_state"] == "human_verified"
    assert cand_crit2["Python"]["human_decision"] == "accepted"

    # Step 13: Employer/admin rejects SQL with rationale containing internal notes
    sql_reject_rationale = (
        "SQL experience does not satisfy enterprise complex optimization standards. "
        "[Internal Notes: candidate lacks distributed db experience and sharding background]"
    )
    decision_res2 = await client.post(
        f"/api/v1/reviews/{sql_ce_id}/decision",
        json={
            "decision": "rejected",
            "mandatory_rationale": sql_reject_rationale,
        },
        headers=emp_headers,
    )
    assert decision_res2.status_code == 201
    decision_data2 = decision_res2.json()
    assert decision_data2["decision"] == "rejected"
    assert decision_data2["new_verification_state"] == "human_rejected"

    # Step 14: Candidate sees rejection status and permitted explanation ([Internal Notes: ...] excluded)
    cand_eval_res3 = await client.get(
        f"/api/v1/evaluations/application/{application_id}",
        headers=cand_headers,
    )
    assert cand_eval_res3.status_code == 200
    cand_eval_data3 = cand_eval_res3.json()
    cand_crit3 = {ce["criterion_name"]: ce for ce in cand_eval_data3["criteria_evaluations"]}

    assert cand_crit3["SQL"]["verification_state"] == "human_rejected"
    assert cand_crit3["SQL"]["human_decision"] == "rejected"
    # Ensure permitted public rationale is visible
    assert "SQL experience does not satisfy enterprise" in cand_crit3["SQL"]["decision_rationale"]
    # Ensure confidential internal notes are excluded from candidate view!
    assert "Internal Notes" not in cand_crit3["SQL"]["decision_rationale"]
    assert "lacks distributed db" not in cand_crit3["SQL"]["decision_rationale"]

    # Step 15: Verify audit history preserves both decisions
    test_session.expire_all()
    async with test_session.begin():
        decisions_q = await test_session.execute(
            select(ReviewDecision).order_by(ReviewDecision.created_at.asc())
        )
        decisions = decisions_q.scalars().all()
        assert len(decisions) >= 2

        audit_q = await test_session.execute(
            select(AuditEvent).where(AuditEvent.action == "REVIEW_DECISION_RECORDED")
        )
        audit_events = audit_q.scalars().all()
        assert len(audit_events) >= 2
        actions = [e.action for e in audit_events]
        assert "REVIEW_DECISION_RECORDED" in actions
