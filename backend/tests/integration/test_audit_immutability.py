import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.core.security import UserRole
from app.db.models.application import Application
from app.db.models.audit import AuditEvent
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
from app.db.models.review import ReviewDecision
from app.db.models.user import User
from app.repositories.domain import EvaluationRepository, ReviewDecisionRepository


@pytest.mark.asyncio
async def test_evaluation_audit_logging_and_version_preservation(test_session: AsyncSession):
    employer = User(
        email="emp_audit1@example.com", role=UserRole.EMPLOYER_ADMIN, full_name="Emp Audit1"
    )
    candidate = User(
        email="cand_audit1@example.com", role=UserRole.CANDIDATE, full_name="Cand Audit1"
    )
    test_session.add_all([employer, candidate])
    await test_session.flush()

    job = Job(creator=employer, title="Audit Job", status=JobStatus.ACTIVE)
    crit1 = JobCriterion(job=job, name="Kubernetes", version=1)
    doc = Document(
        candidate=candidate,
        file_name="res_audit.pdf",
        file_path="/res_audit.pdf",
        file_hash="hash_audit",
        mime_type="application/pdf",
        file_size_bytes=1000,
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
    test_session.add_all([job, crit1, doc, run])
    await test_session.flush()

    app = Application(
        job=job,
        candidate=candidate,
        primary_document=doc,
        status=ApplicationStatus.SCREENING,
    )
    test_session.add(app)
    await test_session.flush()

    eval_repo = EvaluationRepository(test_session)

    # 1. Record Version 1 evaluation
    eval_v1 = await eval_repo.record_evaluation(
        application_id=app.id,
        job_criteria_version=1,
        extraction_run_id=run.id,
        overall_status=EvidenceStatus.AMBIGUOUS,
        criterion_mappings=[
            {
                "job_criterion_id": crit1.id,
                "ai_status": EvidenceStatus.AMBIGUOUS,
                "ai_confidence": 0.60,
                "ai_reasoning": "Uncertain mention on page 1",
            }
        ],
        actor_id="system_ai_pipeline",
    )
    await test_session.commit()

    assert eval_v1.version == 1
    assert eval_v1.is_latest is True

    # 2. Record Version 2 evaluation (e.g. after criteria update or re-screening)
    eval_v2 = await eval_repo.record_evaluation(
        application_id=app.id,
        job_criteria_version=1,
        extraction_run_id=run.id,
        overall_status=EvidenceStatus.SUPPORTED,
        criterion_mappings=[
            {
                "job_criterion_id": crit1.id,
                "ai_status": EvidenceStatus.SUPPORTED,
                "ai_confidence": 0.95,
                "ai_reasoning": "Clarified evidence verified",
            }
        ],
        actor_id="system_ai_pipeline",
    )
    await test_session.commit()

    assert eval_v2.version == 2
    assert eval_v2.is_latest is True

    # Verify that eval_v1 history is preserved and is_latest is now False
    await test_session.refresh(eval_v1)
    assert eval_v1.version == 1
    assert eval_v1.is_latest is False

    # Verify audit events were written for each evaluation
    audit_events = (
        (
            await test_session.execute(
                select(AuditEvent)
                .where(AuditEvent.action == "EVALUATION_RECORDED")
                .order_by(AuditEvent.timestamp.asc())
            )
        )
        .scalars()
        .all()
    )

    assert len(audit_events) == 2
    assert audit_events[0].details["evaluation_version"] == 1
    assert audit_events[1].details["evaluation_version"] == 2


@pytest.mark.asyncio
async def test_reviewer_decision_audit_trail_and_history_preservation(test_session: AsyncSession):
    employer = User(
        email="emp_audit2@example.com", role=UserRole.EMPLOYER_ADMIN, full_name="Emp Audit2"
    )
    reviewer = User(email="rev_audit2@example.com", role=UserRole.REVIEWER, full_name="Rev Audit2")
    candidate = User(
        email="cand_audit2@example.com", role=UserRole.CANDIDATE, full_name="Cand Audit2"
    )
    test_session.add_all([employer, reviewer, candidate])
    await test_session.flush()

    job = Job(creator=employer, title="Audit Job 2", status=JobStatus.ACTIVE)
    crit = JobCriterion(job=job, name="PostgreSQL", version=1)
    doc = Document(
        candidate=candidate,
        file_name="res2.pdf",
        file_path="/res2.pdf",
        file_hash="hash_audit2",
        mime_type="application/pdf",
        file_size_bytes=1000,
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
        job=job,
        candidate=candidate,
        primary_document=doc,
        status=ApplicationStatus.SCREENING,
    )
    test_session.add(app)
    await test_session.flush()

    eval_record = Evaluation(
        application=app,
        version=1,
        job_criteria_version=1,
        extraction_run=run,
        overall_status=EvidenceStatus.AMBIGUOUS,
        raw_model_output={},
    )
    test_session.add(eval_record)
    await test_session.flush()

    ce = CriterionEvidence(
        evaluation=eval_record,
        criterion=crit,
        ai_status=EvidenceStatus.AMBIGUOUS,
        verification_state=VerificationState.UNVERIFIED,
    )
    test_session.add(ce)
    await test_session.flush()

    decision_repo = ReviewDecisionRepository(test_session)

    # 1. Empty rationale should be rejected before saving
    with pytest.raises(ValidationError):
        await decision_repo.record_decision(
            application_id=app.id,
            criterion_evidence_id=ce.id,
            reviewer_id=reviewer.id,
            decision=ReviewDecisionType.ACCEPTED,
            mandatory_rationale="   ",  # Blank
            new_verification_state=VerificationState.HUMAN_VERIFIED,
        )

    # 2. Record first reviewer decision (Request Clarification)
    decision1 = await decision_repo.record_decision(
        application_id=app.id,
        criterion_evidence_id=ce.id,
        reviewer_id=reviewer.id,
        decision=ReviewDecisionType.REQUESTED_CLARIFICATION,
        mandatory_rationale="Need to confirm years of production PostgreSQL administration experience.",
        new_verification_state=VerificationState.CANDIDATE_CLARIFIED,
    )
    await test_session.commit()

    assert decision1.is_active is True
    assert ce.verification_state == VerificationState.CANDIDATE_CLARIFIED

    # 3. Record second reviewer decision (Accept Evidence)
    decision2 = await decision_repo.record_decision(
        application_id=app.id,
        criterion_evidence_id=ce.id,
        reviewer_id=reviewer.id,
        decision=ReviewDecisionType.ACCEPTED,
        mandatory_rationale="Candidate provided verification of DBA experience; criterion is now satisfied.",
        new_verification_state=VerificationState.HUMAN_VERIFIED,
    )
    await test_session.commit()

    # Prior decision is deactivated but preserved in the table
    await test_session.refresh(decision1)
    assert decision1.is_active is False
    assert decision2.is_active is True
    assert ce.verification_state == VerificationState.HUMAN_VERIFIED

    # Total review decisions for this criterion evidence is 2 (history preserved)
    decisions_in_db = (
        (
            await test_session.execute(
                select(ReviewDecision).where(ReviewDecision.criterion_evidence_id == ce.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(decisions_in_db) == 2

    # Verify audit log recorded both decisions with audit actions
    audit_events = (
        (
            await test_session.execute(
                select(AuditEvent)
                .where(
                    AuditEvent.action == "REVIEW_DECISION_RECORDED",
                    AuditEvent.resource_type == "review_decision",
                )
                .order_by(AuditEvent.timestamp.asc())
            )
        )
        .scalars()
        .all()
    )

    assert len(audit_events) == 2
    assert audit_events[0].details["decision"] == str(ReviewDecisionType.REQUESTED_CLARIFICATION)
    assert audit_events[1].details["decision"] == str(ReviewDecisionType.ACCEPTED)
    assert audit_events[1].details["previous_state"] == str(VerificationState.CANDIDATE_CLARIFIED)
    assert audit_events[1].details["new_state"] == str(VerificationState.HUMAN_VERIFIED)
