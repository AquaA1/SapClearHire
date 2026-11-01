import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserRole, create_access_token
from app.db.models.audit import AuditEvent
from app.db.models.enums import ReviewDecisionType, ReviewFlagStatus, VerificationState
from app.db.models.evaluation import CriterionEvidence
from app.db.models.review import ReviewDecision, ReviewFlag
from tests.helpers import generate_sample_pdf


@pytest.mark.asyncio
async def test_review_resolution_unresolved_counts_and_triage_synchronization(
    client: AsyncClient, test_session: AsyncSession
):
    """
    End-to-end integration test verifying review resolution, triage queue filtering,
    unresolved counts, and candidate-reviewer synchronization:
    1. Employer creates a job requisition with ambiguous and missing criteria.
    2. Candidate uploads resume and submits application.
    3. AI evaluation generates criteria evidence with ambiguous/missing items.
    4. Review flags are created for the ambiguous/missing criteria.
    5. Triage queue shows authoritative initial counts (pending = 2, resolved = 0).
    6. Employer accepts Criterion 1 with valid rationale:
       - Pending count decrements by 1 (2 -> 1).
       - Resolved count increments by 1 (0 -> 1).
       - Criterion 1 leaves Pending Action and enters Resolved tab.
       - Candidate application page reflects 'human_verified'.
       - Calling create_review_flags again does NOT re-flag Criterion 1.
    7. Full refresh preserves counts and resolution.
    8. Employer rejects Criterion 2 with valid rationale:
       - Pending count decrements by 1 (1 -> 0).
       - Resolved count increments by 1 (1 -> 2).
       - Criterion 2 enters Resolved tab.
       - Candidate application page reflects 'human_rejected'.
    9. Employer requests clarification on a new case:
       - Case transitions to UNDER_REVIEW (unresolved).
       - Pending count DOES NOT decrement.
       - Case does NOT enter Resolved tab.
       - Candidate sees unverified state.
    10. Audit trail preserves all decisions.
    """
    employer_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    reviewer_id = str(uuid.uuid4())

    emp_token = create_access_token(subject=employer_id, role=UserRole.EMPLOYER_ADMIN)
    cand_token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)
    rev_token = create_access_token(subject=reviewer_id, role=UserRole.REVIEWER)

    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    cand_headers = {"Authorization": f"Bearer {cand_token}"}
    rev_headers = {"Authorization": f"Bearer {rev_token}"}

    # 1. Employer creates job with 2 required criteria that will trigger review flags
    job_payload = {
        "title": "Principal Distributed Systems Engineer",
        "department": "Infrastructure",
        "criteria": [
            {
                "name": "Team Leadership",
                "category": "required",
                "description": "Collaborative leadership and cross-functional mentoring",
            },
            {
                "name": "Distributed Storage",
                "category": "required",
                "description": "Architecture of distributed blob and transactional storage",
            },
        ],
    }
    job_res = await client.post("/api/v1/jobs", json=job_payload, headers=emp_headers)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 2. Candidate uploads resume with ambiguous statements
    resume_pdf = generate_sample_pdf(
        [
            "Alex Smith - Senior Systems Specialist",
            "Familiar with team leadership concepts and participated in engineering team meetings.",
            "Basic exposure to distributed storage systems during internship.",
        ]
    )
    doc_res = await client.post(
        "/api/v1/documents",
        files={"file": ("alex_resume.pdf", resume_pdf, "application/pdf")},
        headers=cand_headers,
    )
    assert doc_res.status_code == 202
    doc_id = doc_res.json()["id"]

    # Extract claims
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

    # 3. Evaluate application
    eval_res = await client.post(
        "/api/v1/evaluations",
        json={"application_id": application_id},
        headers=emp_headers,
    )
    assert eval_res.status_code == 201

    # 4. Create review flags assigned to reviewer
    flag_res = await client.post(
        "/api/v1/review-flags",
        json={
            "application_id": application_id,
            "assigned_to_user_id": reviewer_id,
            "priority": "high",
        },
        headers=emp_headers,
    )
    assert flag_res.status_code == 201
    flags_data = flag_res.json()
    assert flags_data["total_flagged"] == 2
    created_flags = flags_data["flags"]
    flag_1_id = created_flags[0]["id"]
    flag_2_id = created_flags[1]["id"]

    # 5. Check initial triage queue for reviewer
    queue_all_res = await client.get("/api/v1/review-flags", headers=rev_headers)
    assert queue_all_res.status_code == 200
    all_flags = queue_all_res.json()
    assert len(all_flags) == 2

    # Check unresolved / pending filter
    queue_pending_res = await client.get("/api/v1/review-flags?status=pending", headers=rev_headers)
    assert queue_pending_res.status_code == 200
    pending_flags = queue_pending_res.json()
    assert len(pending_flags) == 2

    # Check resolved filter
    queue_resolved_res = await client.get("/api/v1/review-flags?status=resolved", headers=rev_headers)
    assert queue_resolved_res.status_code == 200
    resolved_flags = queue_resolved_res.json()
    assert len(resolved_flags) == 0

    # Employer also sees both cases in their organization triage queue
    emp_queue_res = await client.get("/api/v1/review-flags", headers=emp_headers)
    assert emp_queue_res.status_code == 200
    assert len(emp_queue_res.json()) == 2

    # 6. Reviewer accepts Flag 1 with valid mandatory rationale
    accept_rationale = (
        "Candidate demonstrated verified cross-functional leadership in verbal review and technical references."
    )
    dec1_res = await client.post(
        f"/api/v1/reviews/{flag_1_id}/decision",
        json={
            "decision": "accepted",
            "mandatory_rationale": accept_rationale,
        },
        headers=rev_headers,
    )
    assert dec1_res.status_code == 201
    dec1_data = dec1_res.json()
    assert dec1_data["decision"] == "accepted"
    assert dec1_data["new_verification_state"] == "human_verified"
    assert dec1_data["flag_status"] == "resolved"

    # Verify pending count decrements by 1 (2 -> 1)
    queue_pending_res2 = await client.get("/api/v1/review-flags?status=pending", headers=rev_headers)
    assert queue_pending_res2.status_code == 200
    pending_flags2 = queue_pending_res2.json()
    assert len(pending_flags2) == 1
    assert pending_flags2[0]["id"] == flag_2_id

    # Verify resolved count increments by 1 (0 -> 1)
    queue_resolved_res2 = await client.get("/api/v1/review-flags?status=resolved", headers=rev_headers)
    assert queue_resolved_res2.status_code == 200
    resolved_flags2 = queue_resolved_res2.json()
    assert len(resolved_flags2) == 1
    assert resolved_flags2[0]["id"] == flag_1_id

    # Total cases remains 2
    queue_all_res2 = await client.get("/api/v1/review-flags", headers=rev_headers)
    assert len(queue_all_res2.json()) == 2

    # Verify candidate dossier reflects 'human_verified' for accepted criterion
    cand_eval_res1 = await client.get(
        f"/api/v1/evaluations/application/{application_id}",
        headers=cand_headers,
    )
    assert cand_eval_res1.status_code == 200
    cand_eval_items1 = {
        item["criterion_name"]: item for item in cand_eval_res1.json()["criteria_evaluations"]
    }
    # One criterion is human_verified, the other remains unverified
    verified_items = [
        item for item in cand_eval_items1.values() if item["verification_state"] == "human_verified"
    ]
    assert len(verified_items) == 1
    assert verified_items[0]["decision_rationale"] == accept_rationale

    # 6b. Guard: Calling create_review_flags again must NOT re-flag or re-open the resolved criterion!
    reflag_res = await client.post(
        "/api/v1/review-flags",
        json={"application_id": application_id},
        headers=emp_headers,
    )
    assert reflag_res.status_code == 201
    # Only the remaining unresolved criterion should be flagged/returned
    reflag_batch = reflag_res.json()
    assert all(f["id"] != flag_1_id or f["status"] == "resolved" for f in reflag_batch["flags"])

    # 7. Full refresh verification: verify persistence in database
    test_session.expire_all()
    async with test_session.begin():
        db_flag1 = await test_session.get(ReviewFlag, uuid.UUID(flag_1_id))
        assert db_flag1.status == ReviewFlagStatus.RESOLVED
        assert db_flag1.resolved_at is not None

    # 8. Reviewer rejects Flag 2 with valid rationale
    reject_rationale = (
        "Candidate lacks enterprise hands-on distributed transactional storage experience."
    )
    dec2_res = await client.post(
        f"/api/v1/reviews/{flag_2_id}/decision",
        json={
            "decision": "rejected",
            "mandatory_rationale": reject_rationale,
        },
        headers=rev_headers,
    )
    assert dec2_res.status_code == 201
    dec2_data = dec2_res.json()
    assert dec2_data["decision"] == "rejected"
    assert dec2_data["new_verification_state"] == "human_rejected"
    assert dec2_data["flag_status"] == "resolved"

    # Pending count is now 0
    queue_pending_res3 = await client.get("/api/v1/review-flags?status=pending", headers=rev_headers)
    assert len(queue_pending_res3.json()) == 0

    # Resolved count is now 2
    queue_resolved_res3 = await client.get("/api/v1/review-flags?status=resolved", headers=rev_headers)
    assert len(queue_resolved_res3.json()) == 2

    # Candidate dossier reflects human_rejected for second criterion
    cand_eval_res2 = await client.get(
        f"/api/v1/evaluations/application/{application_id}",
        headers=cand_headers,
    )
    cand_eval_items2 = {
        item["criterion_name"]: item for item in cand_eval_res2.json()["criteria_evaluations"]
    }
    rejected_items = [
        item for item in cand_eval_items2.values() if item["verification_state"] == "human_rejected"
    ]
    assert len(rejected_items) == 1
    assert rejected_items[0]["decision_rationale"] == reject_rationale

    # 9. Test Request Clarification behavior
    # Create a 2nd candidate and application with a flag to test clarification request
    cand2_id = str(uuid.uuid4())
    cand2_token = create_access_token(subject=cand2_id, role=UserRole.CANDIDATE)
    cand2_headers = {"Authorization": f"Bearer {cand2_token}"}

    doc_res2 = await client.post(
        "/api/v1/documents",
        files={"file": ("alex2_resume.pdf", resume_pdf, "application/pdf")},
        headers=cand2_headers,
    )
    doc2_id = doc_res2.json()["id"]
    await client.post(f"/api/v1/documents/{doc2_id}/extract", headers=cand2_headers)

    app_res2 = await client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "primary_document_id": doc2_id},
        headers=cand2_headers,
    )
    app2_id = app_res2.json()["id"]
    await client.post("/api/v1/evaluations", json={"application_id": app2_id}, headers=emp_headers)

    flag_res2 = await client.post(
        "/api/v1/review-flags",
        json={
            "application_id": app2_id,
            "assigned_to_user_id": reviewer_id,
            "priority": "normal",
        },
        headers=emp_headers,
    )
    flag_3_id = flag_res2.json()["flags"][0]["id"]

    # Current pending count before clarification
    queue_pending_pre = await client.get(
        f"/api/v1/review-flags?status=pending&application_id={app2_id}",
        headers=rev_headers,
    )
    pending_count_pre = len(queue_pending_pre.json())
    assert pending_count_pre >= 1

    # Reviewer requests clarification
    clar_res = await client.post(
        f"/api/v1/reviews/{flag_3_id}/decision",
        json={
            "decision": "requested_clarification",
            "mandatory_rationale": "Please provide GitHub repositories or design docs proving leadership responsibilities.",
        },
        headers=rev_headers,
    )
    assert clar_res.status_code == 201
    clar_data = clar_res.json()
    assert clar_data["decision"] == "requested_clarification"
    assert clar_data["new_verification_state"] == "unverified"
    assert clar_data["flag_status"] == "under_review"

    # CRITICAL: Pending / unresolved count must NOT decrement!
    queue_pending_post = await client.get(
        f"/api/v1/review-flags?status=pending&application_id={app2_id}",
        headers=rev_headers,
    )
    pending_count_post = len(queue_pending_post.json())
    assert pending_count_post == pending_count_pre

    # Must NOT appear in Resolved tab
    queue_resolved_post = await client.get(
        f"/api/v1/review-flags?status=resolved&application_id={app2_id}",
        headers=rev_headers,
    )
    assert len(queue_resolved_post.json()) == 0

    # 10. Verify audit history preserves all decisions
    test_session.expire_all()
    async with test_session.begin():
        decisions_q = await test_session.execute(
            select(ReviewDecision).where(ReviewDecision.application_id == uuid.UUID(application_id))
        )
        decisions = decisions_q.scalars().all()
        assert len(decisions) == 2

        audit_q = await test_session.execute(
            select(AuditEvent).where(AuditEvent.action == "REVIEW_DECISION_RECORDED")
        )
        audit_events = audit_q.scalars().all()
        assert len(audit_events) >= 3
