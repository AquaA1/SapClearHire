import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserRole, create_access_token
from app.db.models.application import Application
from app.db.models.document import Document, ExtractionRun
from app.db.models.enums import (
    ApplicationStatus,
    DocumentProcessingStatus,
    EvidenceStatus,
    JobStatus,
    ReviewDecisionType,
    VerificationState,
)
from app.db.models.evaluation import CriterionEvidence, Evaluation
from app.db.models.job import Job, JobCriterion
from app.db.models.review import ReviewFlag
from app.db.models.user import User
from app.repositories.audit import AuditEventRepository
from app.repositories.domain import ReviewDecisionRepository


@pytest.mark.asyncio
async def test_audit_verify_endpoint_permissions_and_report(
    client: AsyncClient, test_session: AsyncSession
):
    """
    Test that /api/v1/audit/verify can be accessed by SYSTEM_AUDITOR and EMPLOYER_ADMIN,
    and returns a valid report, while CANDIDATE and REVIEWER are denied (403).
    """
    admin_id = str(uuid.uuid4())
    auditor_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    reviewer_id = str(uuid.uuid4())

    admin_headers = {
        "Authorization": f"Bearer {create_access_token(admin_id, UserRole.EMPLOYER_ADMIN)}"
    }
    auditor_headers = {
        "Authorization": f"Bearer {create_access_token(auditor_id, UserRole.SYSTEM_AUDITOR)}"
    }
    cand_headers = {
        "Authorization": f"Bearer {create_access_token(candidate_id, UserRole.CANDIDATE)}"
    }
    rev_headers = {"Authorization": f"Bearer {create_access_token(reviewer_id, UserRole.REVIEWER)}"}

    # Seed an audit event
    repo = AuditEventRepository(test_session)
    await repo.log_event(
        action="CONFIG_INITIALIZED",
        resource_type="system",
        resource_id="0",
        actor_id=admin_id,
        actor_role=UserRole.EMPLOYER_ADMIN,
        details={"init": True},
    )
    await test_session.commit()

    # 1. Auditor can verify
    res_auditor = await client.get("/api/v1/audit/verify", headers=auditor_headers)
    assert res_auditor.status_code == 200
    data = res_auditor.json()
    assert data["is_valid"] is True
    assert data["total_events"] >= 1
    assert data["verified_events"] >= 1
    assert data["chain_head_hash"] is not None
    assert "tamper-evidence" in data["tamper_evidence_disclaimer"].lower()

    # 2. Employer Admin can verify
    res_admin = await client.get("/api/v1/audit/verify", headers=admin_headers)
    assert res_admin.status_code == 200
    assert res_admin.json()["is_valid"] is True

    # 3. Candidate is forbidden
    res_cand = await client.get("/api/v1/audit/verify", headers=cand_headers)
    assert res_cand.status_code == 403

    # 4. Reviewer is forbidden
    res_rev = await client.get("/api/v1/audit/verify", headers=rev_headers)
    assert res_rev.status_code == 403


@pytest.mark.asyncio
async def test_audit_event_get_detail_and_cryptographic_verification(
    client: AsyncClient, test_session: AsyncSession
):
    """
    Test GET /api/v1/audit/{id} returns previous_hash, event_hash, and is_verified=True.
    """
    admin_id = str(uuid.uuid4())
    admin_headers = {
        "Authorization": f"Bearer {create_access_token(admin_id, UserRole.EMPLOYER_ADMIN)}"
    }

    repo = AuditEventRepository(test_session)
    event = await repo.log_event(
        action="TENANT_SETTINGS_UPDATED",
        resource_type="tenant",
        resource_id="tenant_1",
        actor_id=admin_id,
        actor_role=UserRole.EMPLOYER_ADMIN,
        details={"setting": "strict_mode", "enabled": True},
        entity_version=1,
    )
    await test_session.commit()

    res = await client.get(f"/api/v1/audit/{event.id}", headers=admin_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == str(event.id)
    assert body["action"] == "TENANT_SETTINGS_UPDATED"
    assert body["sequence_number"] == event.sequence_number
    assert body["previous_hash"] == event.previous_hash
    assert body["event_hash"] == event.event_hash
    assert body["is_verified"] is True


@pytest.mark.asyncio
async def test_candidate_access_control_isolated_to_own_records(
    client: AsyncClient, test_session: AsyncSession
):
    """
    Test that candidate A can view audit events for candidate A's records,
    while candidate B is forbidden (403) from accessing candidate A's audit event.
    """
    cand_a = User(email="cand_a@example.com", role=UserRole.CANDIDATE, full_name="Candidate A")
    cand_b = User(email="cand_b@example.com", role=UserRole.CANDIDATE, full_name="Candidate B")
    test_session.add_all([cand_a, cand_b])
    await test_session.flush()

    doc_a = Document(
        candidate=cand_a,
        file_name="res_a.pdf",
        file_path="/res_a.pdf",
        file_hash="hash_a",
        mime_type="application/pdf",
        file_size_bytes=500,
        extracted_text_by_page={},
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    test_session.add(doc_a)
    await test_session.flush()

    # Log document uploaded event for candidate A
    repo = AuditEventRepository(test_session)
    event = await repo.log_event(
        action="DOCUMENT_UPLOADED",
        resource_type="document",
        resource_id=str(doc_a.id),
        actor_id=str(cand_a.id),
        actor_role=UserRole.CANDIDATE,
        details={"file_name": doc_a.file_name, "file_hash": doc_a.file_hash},
    )
    await test_session.commit()

    cand_a_token = create_access_token(str(cand_a.id), UserRole.CANDIDATE)
    cand_b_token = create_access_token(str(cand_b.id), UserRole.CANDIDATE)

    # 1. Candidate A can access their own document's audit event
    res_a = await client.get(
        f"/api/v1/audit/{event.id}", headers={"Authorization": f"Bearer {cand_a_token}"}
    )
    assert res_a.status_code == 200
    assert res_a.json()["id"] == str(event.id)

    # 2. Candidate B cannot access Candidate A's audit event
    res_b = await client.get(
        f"/api/v1/audit/{event.id}", headers={"Authorization": f"Bearer {cand_b_token}"}
    )
    assert res_b.status_code == 403
    assert "own records" in res_b.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_reviewer_access_control_isolated_to_assigned_cases(
    client: AsyncClient, test_session: AsyncSession
):
    """
    Test that Reviewer 1 can access audit events for cases assigned to them,
    while Reviewer 2 is forbidden (403) from accessing cases assigned to Reviewer 1.
    """
    employer = User(
        email="emp_iso@example.com", role=UserRole.EMPLOYER_ADMIN, full_name="Employer Iso"
    )
    candidate = User(
        email="cand_iso@example.com", role=UserRole.CANDIDATE, full_name="Candidate Iso"
    )
    reviewer_1 = User(email="rev_iso1@example.com", role=UserRole.REVIEWER, full_name="Reviewer 1")
    reviewer_2 = User(email="rev_iso2@example.com", role=UserRole.REVIEWER, full_name="Reviewer 2")
    test_session.add_all([employer, candidate, reviewer_1, reviewer_2])
    await test_session.flush()

    job = Job(creator=employer, title="Iso Job", status=JobStatus.ACTIVE)
    crit = JobCriterion(job=job, name="Security Audit", version=1)
    doc = Document(
        candidate=candidate,
        file_name="res_iso.pdf",
        file_path="/res_iso.pdf",
        file_hash="hash_iso",
        mime_type="application/pdf",
        file_size_bytes=500,
        extracted_text_by_page={},
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    run = ExtractionRun(
        document=doc,
        run_number=1,
        provider="fake",
        model_name="stub",
        status=DocumentProcessingStatus.COMPLETED,
        raw_output={},
    )
    test_session.add_all([job, crit, doc, run])
    await test_session.flush()

    app = Application(
        job=job, candidate=candidate, primary_document=doc, status=ApplicationStatus.SCREENING
    )
    test_session.add(app)
    await test_session.flush()

    evaluation = Evaluation(
        application=app,
        version=1,
        job_criteria_version=1,
        extraction_run=run,
        overall_status=EvidenceStatus.AMBIGUOUS,
    )
    test_session.add(evaluation)
    await test_session.flush()

    ce = CriterionEvidence(
        evaluation=evaluation,
        criterion=crit,
        ai_status=EvidenceStatus.AMBIGUOUS,
        verification_state=VerificationState.UNVERIFIED,
    )
    flag = ReviewFlag(
        application=app,
        criterion_evidence_id=ce.id,
        flag_type="ambiguous_criterion",
        reason="Ambiguous evidence requiring human review",
        assigned_to_user_id=reviewer_1.id,  # Assigned specifically to Reviewer 1
    )
    test_session.add_all([ce, flag])
    await test_session.flush()

    # Reviewer 1 records a decision (which logs an audit event)
    decision_repo = ReviewDecisionRepository(test_session)
    decision = await decision_repo.record_decision(
        application_id=app.id,
        criterion_evidence_id=ce.id,
        reviewer_id=reviewer_1.id,
        decision=ReviewDecisionType.ACCEPTED,
        mandatory_rationale="Candidate demonstrated security knowledge in code audit sample.",
        new_verification_state=VerificationState.HUMAN_VERIFIED,
    )
    await test_session.commit()

    # Find the audit event logged for this decision
    audit_repo = AuditEventRepository(test_session)
    events = await audit_repo.get_by_resource(
        resource_type="review_decision", resource_id=str(decision.id)
    )
    assert len(events) >= 1
    decision_event = events[0]

    rev1_token = create_access_token(str(reviewer_1.id), UserRole.REVIEWER)
    rev2_token = create_access_token(str(reviewer_2.id), UserRole.REVIEWER)

    # 1. Reviewer 1 can access the audit event for their decision
    res_rev1 = await client.get(
        f"/api/v1/audit/{decision_event.id}",
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert res_rev1.status_code == 200
    assert res_rev1.json()["id"] == str(decision_event.id)

    # 2. Reviewer 2 is forbidden from accessing Reviewer 1's decision audit event
    res_rev2 = await client.get(
        f"/api/v1/audit/{decision_event.id}",
        headers={"Authorization": f"Bearer {rev2_token}"},
    )
    assert res_rev2.status_code == 403
    assert "assigned review cases" in res_rev2.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_audit_unauthenticated_request_rejected(client: AsyncClient):
    """
    Test that requests without credentials to audit endpoints are rejected with 401 Unauthorized.
    """
    random_id = uuid.uuid4()
    res = await client.get(f"/api/v1/audit/{random_id}")
    assert res.status_code == 401
