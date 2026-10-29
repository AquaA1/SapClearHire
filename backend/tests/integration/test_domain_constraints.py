import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserRole
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
from app.db.models.review import ReviewDecision
from app.db.models.user import User


@pytest.mark.asyncio
async def test_duplicate_application_constraint(test_session: AsyncSession):
    employer = User(email="emp_c1@example.com", role=UserRole.EMPLOYER_ADMIN, full_name="Emp C1")
    candidate = User(email="cand_c1@example.com", role=UserRole.CANDIDATE, full_name="Cand C1")
    test_session.add_all([employer, candidate])
    await test_session.flush()

    job = Job(employer_id=employer.id, title="Job C1", status=JobStatus.ACTIVE)
    doc = Document(
        candidate_id=candidate.id,
        file_name="res.pdf",
        file_path="/res.pdf",
        file_hash="hash_c1",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_by_page={},
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    test_session.add_all([job, doc])
    await test_session.flush()

    app1 = Application(
        job_id=job.id,
        candidate_id=candidate.id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SUBMITTED,
    )
    test_session.add(app1)
    await test_session.flush()

    # Second application for same candidate and job must violate unique constraint
    app2 = Application(
        job_id=job.id,
        candidate_id=candidate.id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SUBMITTED,
    )
    test_session.add(app2)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_duplicate_evaluation_version_constraint(test_session: AsyncSession):
    employer = User(email="emp_c2@example.com", role=UserRole.EMPLOYER_ADMIN, full_name="Emp C2")
    candidate = User(email="cand_c2@example.com", role=UserRole.CANDIDATE, full_name="Cand C2")
    test_session.add_all([employer, candidate])
    await test_session.flush()

    job = Job(employer_id=employer.id, title="Job C2", status=JobStatus.ACTIVE)
    doc = Document(
        candidate_id=candidate.id,
        file_name="res2.pdf",
        file_path="/res2.pdf",
        file_hash="hash_c2",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_by_page={},
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    test_session.add_all([job, doc])
    await test_session.flush()

    app = Application(
        job_id=job.id,
        candidate_id=candidate.id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SUBMITTED,
    )
    run = ExtractionRun(
        document_id=doc.id,
        run_number=1,
        provider="fake",
        model_name="stub",
        status=DocumentProcessingStatus.COMPLETED,
        raw_output={},
    )
    test_session.add_all([app, run])
    await test_session.flush()

    eval1 = Evaluation(
        application_id=app.id,
        version=1,
        job_criteria_version=1,
        extraction_run_id=run.id,
        overall_status=EvidenceStatus.SUPPORTED,
        raw_model_output={},
    )
    test_session.add(eval1)
    await test_session.flush()

    # Duplicate version 1 for same application must violate unique constraint
    eval2 = Evaluation(
        application_id=app.id,
        version=1,
        job_criteria_version=1,
        extraction_run_id=run.id,
        overall_status=EvidenceStatus.AMBIGUOUS,
        raw_model_output={},
    )
    test_session.add(eval2)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_job_criterion_version_uniqueness(test_session: AsyncSession):
    employer = User(email="emp_c3@example.com", role=UserRole.EMPLOYER_ADMIN, full_name="Emp C3")
    test_session.add(employer)
    await test_session.flush()

    job = Job(employer_id=employer.id, title="Job C3", status=JobStatus.ACTIVE)
    test_session.add(job)
    await test_session.flush()

    crit1 = JobCriterion(job_id=job.id, name="Docker", version=1, category="must_have")
    test_session.add(crit1)
    await test_session.flush()

    # Duplicate criterion name with same version must fail
    crit2 = JobCriterion(job_id=job.id, name="Docker", version=1, category="must_have")
    test_session.add(crit2)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_review_decision_mandatory_rationale_constraint(test_session: AsyncSession):
    employer = User(email="emp_c4@example.com", role=UserRole.EMPLOYER_ADMIN, full_name="Emp C4")
    reviewer = User(email="rev_c4@example.com", role=UserRole.REVIEWER, full_name="Rev C4")
    candidate = User(email="cand_c4@example.com", role=UserRole.CANDIDATE, full_name="Cand C4")
    test_session.add_all([employer, reviewer, candidate])
    await test_session.flush()

    job = Job(employer_id=employer.id, title="Job C4", status=JobStatus.ACTIVE)
    doc = Document(
        candidate_id=candidate.id,
        file_name="res4.pdf",
        file_path="/res4.pdf",
        file_hash="hash_c4",
        mime_type="application/pdf",
        file_size_bytes=1000,
        extracted_text_by_page={},
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    test_session.add_all([job, doc])
    await test_session.flush()

    app = Application(
        job_id=job.id,
        candidate_id=candidate.id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SUBMITTED,
    )
    test_session.add(app)
    await test_session.flush()

    # Empty / whitespace-only rationale must violate check constraint
    decision_blank = ReviewDecision(
        application_id=app.id,
        reviewer_id=reviewer.id,
        decision=ReviewDecisionType.ACCEPTED,
        mandatory_rationale="   ",  # Blank rationale
        previous_verification_state=VerificationState.UNVERIFIED,
        new_verification_state=VerificationState.HUMAN_VERIFIED,
        is_active=True,
    )
    test_session.add(decision_blank)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_cascade_delete_evaluation_removes_criterion_evidence(test_session: AsyncSession):
    employer = User(email="emp_c5@example.com", role=UserRole.EMPLOYER_ADMIN, full_name="Emp C5")
    candidate = User(email="cand_c5@example.com", role=UserRole.CANDIDATE, full_name="Cand C5")
    test_session.add_all([employer, candidate])
    await test_session.flush()

    job = Job(creator=employer, title="Job C5", status=JobStatus.ACTIVE)
    crit = JobCriterion(job=job, name="Go", version=1)
    doc = Document(
        candidate=candidate,
        file_name="res5.pdf",
        file_path="/res5.pdf",
        file_hash="hash_c5",
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
        status=ApplicationStatus.SUBMITTED,
    )
    test_session.add(app)
    await test_session.flush()

    eval_record = Evaluation(
        application=app,
        version=1,
        job_criteria_version=1,
        extraction_run=run,
        overall_status=EvidenceStatus.SUPPORTED,
        raw_model_output={},
    )
    test_session.add(eval_record)
    await test_session.flush()

    ce = CriterionEvidence(
        evaluation=eval_record,
        criterion=crit,
        ai_status=EvidenceStatus.SUPPORTED,
        verification_state=VerificationState.UNVERIFIED,
    )
    test_session.add(ce)
    await test_session.flush()

    # Deleting evaluation should delete criterion_evidence via cascade
    await test_session.delete(eval_record)
    await test_session.flush()

    ce_check = await test_session.get(CriterionEvidence, ce.id)
    assert ce_check is None
