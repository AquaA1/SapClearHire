import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.core.security import CurrentUser, UserRole
from app.db.models.application import Application
from app.db.models.document import Document, ExtractionRun
from app.db.models.enums import (
    ApplicationStatus,
    DocumentProcessingStatus,
    EvidenceStatus,
    ReviewDecisionType,
    ReviewFlagStatus,
    VerificationState,
)
from app.db.models.evaluation import CriterionEvidence, Evaluation
from app.db.models.job import Job, JobCriterion
from app.db.models.user import User
from app.services.review import ReviewWorkflowService


@pytest.mark.asyncio
async def test_auto_flagging_rules(test_session: AsyncSession) -> None:
    """
    Test that ambiguous and not_found required criteria are flagged by default,
    while preferred criteria are flagged only when flag_preferred=True.
    """
    candidate_id = uuid.uuid4()
    employer_id = uuid.uuid4()

    test_session.add_all(
        [
            User(
                id=candidate_id,
                email="cand_flag@test.com",
                full_name="Cand",
                role=UserRole.CANDIDATE,
            ),
            User(
                id=employer_id,
                email="emp_flag@test.com",
                full_name="Emp",
                role=UserRole.EMPLOYER_ADMIN,
            ),
        ]
    )

    job = Job(id=uuid.uuid4(), employer_id=employer_id, title="Backend Lead")
    test_session.add(job)
    await test_session.flush()

    c1 = JobCriterion(id=uuid.uuid4(), job_id=job.id, name="Python", category="required", version=1)
    c2 = JobCriterion(
        id=uuid.uuid4(), job_id=job.id, name="Kubernetes", category="required", version=1
    )
    c3 = JobCriterion(id=uuid.uuid4(), job_id=job.id, name="Rust", category="preferred", version=1)
    test_session.add_all([c1, c2, c3])

    doc = Document(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        file_name="res.pdf",
        file_path="/tmp/r.pdf",
        file_hash="hash_flag",
        file_size_bytes=1000,
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    test_session.add(doc)
    await test_session.flush()

    run = ExtractionRun(
        id=uuid.uuid4(),
        document_id=doc.id,
        run_number=1,
        provider="fake",
        model_name="fake-model",
        status=DocumentProcessingStatus.COMPLETED,
    )
    test_session.add(run)
    await test_session.flush()

    app = Application(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_id=candidate_id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SCREENING,
    )
    test_session.add(app)
    await test_session.flush()

    evaluation = Evaluation(
        id=uuid.uuid4(),
        application_id=app.id,
        version=1,
        job_criteria_version=1,
        extraction_run_id=run.id,
        overall_status=EvidenceStatus.AMBIGUOUS,
    )
    test_session.add(evaluation)
    await test_session.flush()

    # ce1: required + ambiguous -> SHOULD flag
    ce1 = CriterionEvidence(
        id=uuid.uuid4(),
        evaluation_id=evaluation.id,
        job_criterion_id=c1.id,
        ai_status=EvidenceStatus.AMBIGUOUS,
        verification_state=VerificationState.UNVERIFIED,
    )
    # ce2: required + not_found -> SHOULD flag
    ce2 = CriterionEvidence(
        id=uuid.uuid4(),
        evaluation_id=evaluation.id,
        job_criterion_id=c2.id,
        ai_status=EvidenceStatus.NOT_FOUND,
        verification_state=VerificationState.UNVERIFIED,
    )
    # ce3: preferred + ambiguous -> SHOULD NOT flag by default
    ce3 = CriterionEvidence(
        id=uuid.uuid4(),
        evaluation_id=evaluation.id,
        job_criterion_id=c3.id,
        ai_status=EvidenceStatus.AMBIGUOUS,
        verification_state=VerificationState.UNVERIFIED,
    )
    test_session.add_all([ce1, ce2, ce3])
    await test_session.flush()

    service = ReviewWorkflowService()

    # 1. Flag with flag_preferred=False (default)
    flags = await service.create_review_flags(
        application_id=app.id,
        session=test_session,
        flag_preferred=False,
    )

    assert len(flags) == 2
    flagged_ce_ids = {f.criterion_evidence_id for f in flags}
    assert ce1.id in flagged_ce_ids
    assert ce2.id in flagged_ce_ids
    assert ce3.id not in flagged_ce_ids
    assert app.status == ApplicationStatus.NEEDS_REVIEW

    # 2. Flag with flag_preferred=True -> should now flag ce3 as well
    flags_with_pref = await service.create_review_flags(
        application_id=app.id,
        session=test_session,
        flag_preferred=True,
    )
    assert len(flags_with_pref) == 3


@pytest.mark.asyncio
async def test_reviewer_mandatory_rationale_validation(test_session: AsyncSession) -> None:
    """Test that reviewer decision requires a non-empty rationale."""
    reviewer_id = uuid.uuid4()
    reviewer = CurrentUser(id=str(reviewer_id), email="rev@test.com", role=UserRole.REVIEWER)

    service = ReviewWorkflowService()
    with pytest.raises(ValidationError) as exc:
        await service.record_reviewer_decision(
            flag_id=uuid.uuid4(),
            decision=ReviewDecisionType.ACCEPTED,
            mandatory_rationale="   ",
            current_user=reviewer,
            session=test_session,
        )
    assert "mandatory" in str(exc.value.message).lower()


@pytest.mark.asyncio
async def test_reviewer_decisions_state_transitions(test_session: AsyncSession) -> None:
    """
    Test reviewer decisions (accepted, rejected, requested_clarification)
    and their verification state transitions.
    """
    candidate_id = uuid.uuid4()
    employer_id = uuid.uuid4()
    reviewer_id = uuid.uuid4()

    test_session.add_all(
        [
            User(
                id=candidate_id,
                email="cand_dec@test.com",
                full_name="Cand",
                role=UserRole.CANDIDATE,
            ),
            User(
                id=employer_id,
                email="emp_dec@test.com",
                full_name="Emp",
                role=UserRole.EMPLOYER_ADMIN,
            ),
            User(id=reviewer_id, email="rev_dec@test.com", full_name="Rev", role=UserRole.REVIEWER),
        ]
    )

    job = Job(id=uuid.uuid4(), employer_id=employer_id, title="Systems Engineer")
    test_session.add(job)
    await test_session.flush()

    crit = JobCriterion(id=uuid.uuid4(), job_id=job.id, name="C++", category="required", version=1)
    test_session.add(crit)

    doc = Document(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        file_name="res.pdf",
        file_path="/tmp/r.pdf",
        file_hash="hash_dec",
        file_size_bytes=1000,
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    test_session.add(doc)
    await test_session.flush()

    run = ExtractionRun(
        id=uuid.uuid4(),
        document_id=doc.id,
        run_number=1,
        provider="fake",
        model_name="fake-model",
        status=DocumentProcessingStatus.COMPLETED,
    )
    test_session.add(run)
    await test_session.flush()

    app = Application(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_id=candidate_id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SCREENING,
    )
    test_session.add(app)
    await test_session.flush()

    eval_obj = Evaluation(
        id=uuid.uuid4(),
        application_id=app.id,
        version=1,
        job_criteria_version=1,
        extraction_run_id=run.id,
        overall_status=EvidenceStatus.AMBIGUOUS,
    )
    test_session.add(eval_obj)
    await test_session.flush()

    ce = CriterionEvidence(
        id=uuid.uuid4(),
        evaluation_id=eval_obj.id,
        job_criterion_id=crit.id,
        ai_status=EvidenceStatus.AMBIGUOUS,
        verification_state=VerificationState.UNVERIFIED,
    )
    test_session.add(ce)
    await test_session.flush()

    service = ReviewWorkflowService()
    flags = await service.create_review_flags(
        application_id=app.id,
        session=test_session,
        assigned_to_user_id=reviewer_id,
    )
    flag_id = flags[0].id

    reviewer_user = CurrentUser(
        id=str(reviewer_id), email="rev_dec@test.com", role=UserRole.REVIEWER
    )

    # 1. Request Clarification -> UNVERIFIED, flag is UNDER_REVIEW
    res_clar = await service.record_reviewer_decision(
        flag_id=flag_id,
        decision=ReviewDecisionType.REQUESTED_CLARIFICATION,
        mandatory_rationale="Please provide evidence of production C++ multi-threading experience.",
        current_user=reviewer_user,
        session=test_session,
    )
    assert res_clar.new_verification_state == VerificationState.UNVERIFIED
    assert res_clar.flag_status == ReviewFlagStatus.UNDER_REVIEW
    assert ce.verification_state == VerificationState.UNVERIFIED

    # 2. Candidate submits clarification -> CANDIDATE_CLARIFIED (unverified until approved)
    cand_user = CurrentUser(
        id=str(candidate_id), email="cand_dec@test.com", role=UserRole.CANDIDATE
    )
    res_sub = await service.submit_candidate_clarification(
        application_id=app.id,
        criterion_evidence_id=ce.id,
        candidate_statement="I maintained the low-latency matching engine in C++20 for 3 years.",
        additional_document_id=None,
        candidate=cand_user,
        session=test_session,
    )
    assert res_sub.new_verification_state == VerificationState.CANDIDATE_CLARIFIED
    assert ce.verification_state == VerificationState.CANDIDATE_CLARIFIED

    # 3. Reviewer accepts -> HUMAN_VERIFIED, flag is RESOLVED
    res_acc = await service.record_reviewer_decision(
        flag_id=flag_id,
        decision=ReviewDecisionType.ACCEPTED,
        mandatory_rationale="Candidate statement confirms substantial C++20 production exposure.",
        current_user=reviewer_user,
        session=test_session,
    )
    assert res_acc.new_verification_state == VerificationState.HUMAN_VERIFIED
    assert res_acc.flag_status == ReviewFlagStatus.RESOLVED
    assert ce.verification_state == VerificationState.HUMAN_VERIFIED
    assert app.status == ApplicationStatus.REVIEWED
