import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserRole
from app.db.models.application import Application
from app.db.models.document import CandidateSkill, Document, EvidenceItem, ExtractionRun
from app.db.models.enums import (
    ApplicationStatus,
    CorrectionRequestStatus,
    DocumentProcessingStatus,
    EvidenceStatus,
    JobStatus,
    ReviewDecisionType,
    ReviewFlagStatus,
    VerificationState,
)
from app.db.models.evaluation import CriterionEvidence, Evaluation
from app.db.models.job import Job, JobCriterion
from app.db.models.review import CorrectionRequest, ReviewDecision, ReviewFlag
from app.db.models.user import User


@pytest.mark.asyncio
async def test_full_domain_model_creation_and_relationships(test_session: AsyncSession):
    # 1. Users
    candidate = User(
        email="candidate1@example.com",
        role=UserRole.CANDIDATE,
        full_name="Alice Candidate",
    )
    reviewer = User(
        email="reviewer1@example.com",
        role=UserRole.REVIEWER,
        full_name="Bob Reviewer",
    )
    employer = User(
        email="employer1@example.com",
        role=UserRole.EMPLOYER_ADMIN,
        full_name="Charlie Employer",
        employer_id="emp_acme_01",
    )
    test_session.add_all([candidate, reviewer, employer])
    await test_session.flush()

    # 2. Document
    doc = Document(
        candidate=candidate,
        file_name="alice_resume.pdf",
        file_path="/storage/alice_resume.pdf",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        mime_type="application/pdf",
        file_size_bytes=1048576,
        page_count=2,
        extracted_text_by_page={
            "1": "Alice Candidate - Senior Python Engineer",
            "2": "PostgreSQL tuning",
        },
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    test_session.add(doc)
    await test_session.flush()

    # 3. ExtractionRun
    run = ExtractionRun(
        document=doc,
        run_number=1,
        provider="fake",
        model_name="deterministic-stub-v1",
        status=DocumentProcessingStatus.COMPLETED,
        raw_output={"extracted_skills": ["Python", "PostgreSQL"], "confidence": 0.98},
    )
    test_session.add(run)
    await test_session.flush()

    # 4. CandidateSkill & EvidenceItem
    skill = CandidateSkill(
        extraction_run=run,
        candidate=candidate,
        skill_name="Python",
        category="programming_language",
        confidence=0.98,
        source_page=1,
        source_excerpt="Senior Python Engineer with 6 years experience",
    )
    evidence = EvidenceItem(
        extraction_run=run,
        document=doc,
        claim_text="Demonstrated 6 years of backend engineering in Python",
        source_page=1,
        source_excerpt="Senior Python Engineer with 6 years experience",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={"method": "exact_match"},
    )
    test_session.add_all([skill, evidence])
    await test_session.flush()

    # 5. Job & JobCriterion (versioned)
    job = Job(
        creator=employer,
        external_requisition_id="REQ-2026-SAP-01",
        title="Senior Python Backend Developer",
        description="Build scalable transparency engines for ClearHire.",
        department="Engineering",
        status=JobStatus.ACTIVE,
    )
    test_session.add(job)
    await test_session.flush()

    criterion_v1 = JobCriterion(
        job=job,
        version=1,
        name="Python Backend Mastery",
        description="At least 5 years building async Python services.",
        category="must_have",
        weight=2.0,
    )
    test_session.add(criterion_v1)
    await test_session.flush()

    # 6. Application
    application = Application(
        job=job,
        candidate=candidate,
        primary_document=doc,
        status=ApplicationStatus.SCREENING,
    )
    test_session.add(application)
    await test_session.flush()

    # 7. Evaluation & CriterionEvidence
    evaluation = Evaluation(
        application=application,
        version=1,
        job_criteria_version=1,
        extraction_run=run,
        overall_status=EvidenceStatus.SUPPORTED,
        summary_notes="All must-have criteria strongly supported by resume evidence.",
        raw_model_output={"score": 0.95, "verdict": "supported"},
        is_latest=True,
    )
    test_session.add(evaluation)
    await test_session.flush()

    crit_evidence = CriterionEvidence(
        evaluation=evaluation,
        criterion=criterion_v1,
        evidence_item=evidence,
        ai_status=EvidenceStatus.SUPPORTED,
        ai_confidence=0.95,
        ai_reasoning="Direct match on page 1 with verifiable excerpt.",
        verification_state=VerificationState.UNVERIFIED,
        source_excerpt=evidence.source_excerpt,
        source_page=1,
    )
    test_session.add(crit_evidence)
    await test_session.flush()

    # 8. ReviewFlag
    flag = ReviewFlag(
        application=application,
        criterion_evidence=crit_evidence,
        flag_type="evidence_verification_needed",
        status=ReviewFlagStatus.PENDING,
        priority="high",
        reason="Verify candidate claim against criteria before interview.",
        assigned_to=reviewer,
    )
    test_session.add(flag)
    await test_session.flush()

    # 9. CorrectionRequest
    correction = CorrectionRequest(
        application=application,
        candidate=candidate,
        criterion_evidence=crit_evidence,
        candidate_statement="I also have published open-source FastAPI libraries.",
        status=CorrectionRequestStatus.SUBMITTED,
    )
    test_session.add(correction)
    await test_session.flush()

    # 10. ReviewDecision (Human oversight with mandatory rationale)
    decision = ReviewDecision(
        application=application,
        criterion_evidence=crit_evidence,
        reviewer=reviewer,
        decision=ReviewDecisionType.ACCEPTED,
        mandatory_rationale="Candidate resume page 1 confirms 6+ years in Python, exceeding the 5 year requirement.",
        previous_verification_state=VerificationState.UNVERIFIED,
        new_verification_state=VerificationState.HUMAN_VERIFIED,
        is_active=True,
    )
    test_session.add(decision)
    await test_session.flush()

    # Refresh entities to load collections in async session
    await test_session.refresh(candidate, ["documents"])
    await test_session.refresh(doc, ["extraction_runs"])
    await test_session.refresh(job, ["criteria"])
    await test_session.refresh(application, ["evaluations"])
    await test_session.refresh(evaluation, ["criterion_evidence_items"])
    await test_session.refresh(crit_evidence, ["review_decisions"])

    # Verify relationships & bidirectional traversals
    assert len(candidate.documents) == 1
    assert candidate.documents[0].file_name == "alice_resume.pdf"
    assert len(doc.extraction_runs) == 1
    assert doc.extraction_runs[0].run_number == 1
    assert len(job.criteria) == 1
    assert job.criteria[0].name == "Python Backend Mastery"
    assert len(application.evaluations) == 1
    assert application.evaluations[0].version == 1
    assert len(evaluation.criterion_evidence_items) == 1

    ce_item = evaluation.criterion_evidence_items[0]
    assert ce_item.ai_status == EvidenceStatus.SUPPORTED
    assert ce_item.verification_state == VerificationState.UNVERIFIED
    assert len(ce_item.review_decisions) == 1
    assert ce_item.review_decisions[0].decision == ReviewDecisionType.ACCEPTED
    assert "Candidate resume page 1" in ce_item.review_decisions[0].mandatory_rationale
