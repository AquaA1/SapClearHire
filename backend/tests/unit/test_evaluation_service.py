import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.core.security import UserRole
from app.db.models.application import Application
from app.db.models.document import CandidateSkill, Document, EvidenceItem, ExtractionRun
from app.db.models.enums import ApplicationStatus, DocumentProcessingStatus, EvidenceStatus
from app.db.models.job import Job, JobCriterion
from app.db.models.user import User
from app.services.evaluation import EvaluationService


@pytest.mark.asyncio
async def test_evaluation_service_supported_criterion(test_session: AsyncSession) -> None:
    """Test that grounded, verified evidence yields supported status."""
    candidate_id = uuid.uuid4()
    employer_id = uuid.uuid4()

    # Create users
    cand = User(
        id=candidate_id, email="candidate@clearhire.com", full_name="Alice", role=UserRole.CANDIDATE
    )
    emp = User(
        id=employer_id, email="emp@clearhire.com", full_name="Bob", role=UserRole.EMPLOYER_ADMIN
    )
    test_session.add_all([cand, emp])
    await test_session.flush()

    # Create Job and Criteria
    job = Job(id=uuid.uuid4(), employer_id=employer_id, title="Backend Engineer")
    test_session.add(job)
    await test_session.flush()

    crit = JobCriterion(
        id=uuid.uuid4(),
        job_id=job.id,
        name="Python",
        category="required",
        weight=1.0,
        version=1,
    )
    test_session.add(crit)

    # Create Document and ExtractionRun
    doc = Document(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        file_name="resume.pdf",
        file_path="/tmp/res.pdf",
        file_hash="hash123",
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

    skill = CandidateSkill(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        candidate_id=candidate_id,
        skill_name="Python",
        confidence=0.95,
        source_page=1,
        source_excerpt="Built microservices using Python and asyncio",
    )
    evidence = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Developed Python backend services",
        source_page=1,
        source_excerpt="Built microservices using Python and asyncio",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={},
    )
    test_session.add_all([skill, evidence])

    # Create Application
    application = Application(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_id=candidate_id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SUBMITTED,
    )
    test_session.add(application)
    await test_session.flush()

    service = EvaluationService()
    evaluation = await service.evaluate_application(application.id, session=test_session)

    assert evaluation.version == 1
    assert evaluation.job_criteria_version == 1
    assert evaluation.overall_status == EvidenceStatus.SUPPORTED

    response = EvaluationService.build_evaluation_response(evaluation)
    assert response.coverage.total_criteria == 1
    assert response.coverage.supported_count == 1
    assert response.coverage.not_found_count == 0
    assert response.coverage.ambiguous_count == 0
    assert response.coverage.required_supported_count == 1

    item = response.criteria_evaluations[0]
    assert item.status == EvidenceStatus.SUPPORTED
    assert "directly demonstrates experience" in item.plain_language_explanation


@pytest.mark.asyncio
async def test_evaluation_service_not_found_criterion(test_session: AsyncSession) -> None:
    """Test that missing evidence results in not_found with a non-judgmental explanation."""
    candidate_id = uuid.uuid4()
    employer_id = uuid.uuid4()

    cand = User(
        id=candidate_id, email="cand2@clearhire.com", full_name="Cand2", role=UserRole.CANDIDATE
    )
    emp = User(
        id=employer_id, email="emp2@clearhire.com", full_name="Emp2", role=UserRole.EMPLOYER_ADMIN
    )
    test_session.add_all([cand, emp])

    job = Job(id=uuid.uuid4(), employer_id=employer_id, title="Frontend Engineer")
    test_session.add(job)
    await test_session.flush()

    crit = JobCriterion(
        id=uuid.uuid4(),
        job_id=job.id,
        name="Rust",
        category="required",
        weight=1.0,
        version=1,
    )
    test_session.add(crit)

    doc = Document(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        file_name="resume.pdf",
        file_path="/tmp/res.pdf",
        file_hash="hash234",
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

    application = Application(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_id=candidate_id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SUBMITTED,
    )
    test_session.add(application)
    await test_session.flush()

    service = EvaluationService()
    evaluation = await service.evaluate_application(application.id, session=test_session)

    assert evaluation.overall_status == EvidenceStatus.NOT_FOUND
    response = EvaluationService.build_evaluation_response(evaluation)
    assert response.coverage.not_found_count == 1
    assert response.coverage.supported_count == 0

    item = response.criteria_evaluations[0]
    assert item.status == EvidenceStatus.NOT_FOUND
    assert "No validated evidence for 'Rust' was found" in item.plain_language_explanation
    assert "This does not mean the candidate lacks this skill" in item.plain_language_explanation


@pytest.mark.asyncio
async def test_evaluation_service_synonyms_matching(test_session: AsyncSession) -> None:
    """Test that domain synonyms (PostgreSQL <-> Postgres, Kubernetes <-> k8s) match successfully."""
    candidate_id = uuid.uuid4()
    employer_id = uuid.uuid4()

    cand = User(
        id=candidate_id, email="cand3@clearhire.com", full_name="Cand3", role=UserRole.CANDIDATE
    )
    emp = User(
        id=employer_id, email="emp3@clearhire.com", full_name="Emp3", role=UserRole.EMPLOYER_ADMIN
    )
    test_session.add_all([cand, emp])

    job = Job(id=uuid.uuid4(), employer_id=employer_id, title="DevOps Engineer")
    test_session.add(job)
    await test_session.flush()

    c1 = JobCriterion(
        id=uuid.uuid4(), job_id=job.id, name="PostgreSQL", category="required", version=1
    )
    c2 = JobCriterion(
        id=uuid.uuid4(), job_id=job.id, name="Kubernetes", category="preferred", version=1
    )
    test_session.add_all([c1, c2])

    doc = Document(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        file_name="resume.pdf",
        file_path="/tmp/res.pdf",
        file_hash="hash345",
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

    # Candidate has 'Postgres' and 'k8s'
    e1 = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Administered Postgres database clusters",
        source_page=1,
        source_excerpt="Administered Postgres database clusters with 99.99% uptime",
        confidence=0.9,
        grounding_verified=True,
        raw_metadata={},
    )
    e2 = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Deployed workloads on k8s",
        source_page=2,
        source_excerpt="Deployed workloads on k8s using Helm charts",
        confidence=0.9,
        grounding_verified=True,
        raw_metadata={},
    )
    test_session.add_all([e1, e2])

    application = Application(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_id=candidate_id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SUBMITTED,
    )
    test_session.add(application)
    await test_session.flush()

    service = EvaluationService()
    evaluation = await service.evaluate_application(application.id, session=test_session)

    response = EvaluationService.build_evaluation_response(evaluation)
    assert response.coverage.supported_count == 2
    assert response.coverage.required_supported_count == 1
    assert response.coverage.preferred_supported_count == 1


@pytest.mark.asyncio
async def test_evaluation_service_vague_criterion_ambiguous(test_session: AsyncSession) -> None:
    """Test that subjective criteria are evaluated as ambiguous."""
    candidate_id = uuid.uuid4()
    employer_id = uuid.uuid4()

    cand = User(
        id=candidate_id, email="cand4@clearhire.com", full_name="Cand4", role=UserRole.CANDIDATE
    )
    emp = User(
        id=employer_id, email="emp4@clearhire.com", full_name="Emp4", role=UserRole.EMPLOYER_ADMIN
    )
    test_session.add_all([cand, emp])

    job = Job(id=uuid.uuid4(), employer_id=employer_id, title="Lead")
    test_session.add(job)
    await test_session.flush()

    crit = JobCriterion(
        id=uuid.uuid4(),
        job_id=job.id,
        name="Team Player",
        category="required",
        version=1,
    )
    test_session.add(crit)

    doc = Document(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        file_name="res.pdf",
        file_path="/tmp/r.pdf",
        file_hash="hash456",
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

    application = Application(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_id=candidate_id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SUBMITTED,
    )
    test_session.add(application)
    await test_session.flush()

    service = EvaluationService()
    evaluation = await service.evaluate_application(application.id, session=test_session)

    response = EvaluationService.build_evaluation_response(evaluation)
    assert response.coverage.ambiguous_count == 1
    item = response.criteria_evaluations[0]
    assert item.status == EvidenceStatus.AMBIGUOUS
    assert "subjective or vague" in item.plain_language_explanation


@pytest.mark.asyncio
async def test_evaluation_service_weak_exposure_and_ungrounded_ambiguous(
    test_session: AsyncSession,
) -> None:
    """Test that weak context, date conflicts, or ungrounded evidence yields ambiguous status."""
    candidate_id = uuid.uuid4()
    employer_id = uuid.uuid4()

    cand = User(
        id=candidate_id, email="cand5@clearhire.com", full_name="Cand5", role=UserRole.CANDIDATE
    )
    emp = User(
        id=employer_id, email="emp5@clearhire.com", full_name="Emp5", role=UserRole.EMPLOYER_ADMIN
    )
    test_session.add_all([cand, emp])

    job = Job(id=uuid.uuid4(), employer_id=employer_id, title="Fullstack")
    test_session.add(job)
    await test_session.flush()

    c1 = JobCriterion(id=uuid.uuid4(), job_id=job.id, name="React", category="required", version=1)
    c2 = JobCriterion(
        id=uuid.uuid4(), job_id=job.id, name="Docker", category="preferred", version=1
    )
    test_session.add_all([c1, c2])

    doc = Document(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        file_name="res.pdf",
        file_path="/tmp/r.pdf",
        file_hash="hash567",
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

    # React has weak exposure ("basic familiarity with React")
    e1 = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Has basic familiarity with React",
        source_page=1,
        source_excerpt="Has basic familiarity with React from university tutorials",
        confidence=0.8,
        grounding_verified=True,
        raw_metadata={},
    )
    # Docker is ungrounded (grounding_verified=False)
    e2 = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Used Docker for containers",
        source_page=1,
        source_excerpt="Fabricated Docker excerpt not in resume",
        confidence=0.5,
        grounding_verified=False,
        raw_metadata={},
    )
    test_session.add_all([e1, e2])

    application = Application(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_id=candidate_id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SUBMITTED,
    )
    test_session.add(application)
    await test_session.flush()

    service = EvaluationService()
    evaluation = await service.evaluate_application(application.id, session=test_session)

    response = EvaluationService.build_evaluation_response(evaluation)
    assert response.coverage.ambiguous_count == 2
    assert response.coverage.supported_count == 0


@pytest.mark.asyncio
async def test_evaluation_service_validates_unprocessed_document(
    test_session: AsyncSession,
) -> None:
    """Test that attempting to evaluate an application whose document is not processed fails."""
    candidate_id = uuid.uuid4()
    employer_id = uuid.uuid4()

    cand = User(
        id=candidate_id, email="cand6@clearhire.com", full_name="Cand6", role=UserRole.CANDIDATE
    )
    emp = User(
        id=employer_id, email="emp6@clearhire.com", full_name="Emp6", role=UserRole.EMPLOYER_ADMIN
    )
    test_session.add_all([cand, emp])

    job = Job(id=uuid.uuid4(), employer_id=employer_id, title="Engineer")
    test_session.add(job)
    await test_session.flush()

    crit = JobCriterion(id=uuid.uuid4(), job_id=job.id, name="Go", category="required", version=1)
    test_session.add(crit)

    # Document still queued
    doc = Document(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        file_name="res.pdf",
        file_path="/tmp/r.pdf",
        file_hash="hash678",
        file_size_bytes=1000,
        processing_status=DocumentProcessingStatus.QUEUED,
    )
    test_session.add(doc)
    await test_session.flush()

    application = Application(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_id=candidate_id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SUBMITTED,
    )
    test_session.add(application)
    await test_session.flush()

    service = EvaluationService()
    with pytest.raises(ValidationError):
        await service.evaluate_application(application.id, session=test_session)
