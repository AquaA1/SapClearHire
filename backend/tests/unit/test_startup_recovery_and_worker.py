import asyncio
import uuid
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import UserRole
from app.db.models.document import CandidateSkill, Document, EvidenceItem, ExtractionRun
from app.db.models.enums import DocumentProcessingStatus
from app.db.models.user import User
from app.main import recover_stale_processing_jobs
from app.services.document import DocumentService


@pytest.fixture
def dummy_pdf(tmp_path: Path) -> Path:
    pdf_file = tmp_path / "sample_resume.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF")
    return pdf_file


@pytest.mark.asyncio
async def test_1_server_startup_with_queued_documents(test_session: AsyncSession, dummy_pdf: Path):
    """Scenario 1: Server startup with queued documents — documents remain queued and are not failed."""
    cand = User(id=uuid.uuid4(), email="c1@example.com", full_name="Candidate 1", role=UserRole.CANDIDATE)
    test_session.add(cand)
    await test_session.flush()

    doc = Document(
        candidate_id=cand.id,
        file_name="resume.pdf",
        file_path=str(dummy_pdf),
        file_hash="hash_q1",
        file_size_bytes=100,
        processing_status=DocumentProcessingStatus.QUEUED,
    )
    test_session.add(doc)
    await test_session.commit()

    stats = await recover_stale_processing_jobs(test_session, enqueue=False)
    await test_session.refresh(doc)

    assert doc.processing_status == DocumentProcessingStatus.QUEUED
    assert stats["documents_queued"] == 1
    assert stats["documents_failed"] == 0


@pytest.mark.asyncio
async def test_2_server_restart_with_interrupted_processing(test_session: AsyncSession, dummy_pdf: Path):
    """Scenario 2: Server restart with interrupted processing — recovered to queued with attempt increment."""
    cand = User(id=uuid.uuid4(), email="c2@example.com", full_name="Candidate 2", role=UserRole.CANDIDATE)
    test_session.add(cand)
    await test_session.flush()

    doc = Document(
        candidate_id=cand.id,
        file_name="resume.pdf",
        file_path=str(dummy_pdf),
        file_hash="hash_p1",
        file_size_bytes=100,
        processing_status=DocumentProcessingStatus.PROCESSING,
    )
    test_session.add(doc)
    await test_session.commit()

    stats = await recover_stale_processing_jobs(test_session, enqueue=False)
    await test_session.refresh(doc)

    assert doc.processing_status == DocumentProcessingStatus.QUEUED
    assert doc.processing_error.get("recovery_attempts") == 1
    assert stats["documents_recovered"] == 1


@pytest.mark.asyncio
async def test_3_completed_documents_remain_completed(test_session: AsyncSession, dummy_pdf: Path):
    """Scenario 3: Completed documents remain completed — never reprocessed."""
    cand = User(id=uuid.uuid4(), email="c3@example.com", full_name="Candidate 3", role=UserRole.CANDIDATE)
    test_session.add(cand)
    await test_session.flush()

    doc = Document(
        candidate_id=cand.id,
        file_name="resume.pdf",
        file_path=str(dummy_pdf),
        file_hash="hash_c1",
        file_size_bytes=100,
        page_count=1,
        extracted_text_by_page={"1": "Sample content"},
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    test_session.add(doc)
    await test_session.commit()

    stats = await recover_stale_processing_jobs(test_session, enqueue=False)
    await test_session.refresh(doc)

    assert doc.processing_status == DocumentProcessingStatus.COMPLETED
    assert stats["documents_queued"] == 0
    assert stats["documents_recovered"] == 0


@pytest.mark.asyncio
async def test_4_previously_failed_documents_remain_failed_unless_retried(test_session: AsyncSession, dummy_pdf: Path):
    """Scenario 4: Previously failed documents remain failed unless explicitly retried."""
    cand = User(id=uuid.uuid4(), email="c4@example.com", full_name="Candidate 4", role=UserRole.CANDIDATE)
    test_session.add(cand)
    await test_session.flush()

    doc = Document(
        candidate_id=cand.id,
        file_name="corrupt.pdf",
        file_path=str(dummy_pdf),
        file_hash="hash_f1",
        file_size_bytes=100,
        processing_status=DocumentProcessingStatus.FAILED,
        processing_error={"code": "PDF_CORRUPTED", "message": "Corrupted stream"},
    )
    test_session.add(doc)
    await test_session.commit()

    stats = await recover_stale_processing_jobs(test_session, enqueue=False)
    await test_session.refresh(doc)

    # Remains failed with original error
    assert doc.processing_status == DocumentProcessingStatus.FAILED
    assert doc.processing_error.get("code") == "PDF_CORRUPTED"
    assert stats["documents_queued"] == 0
    assert stats["documents_recovered"] == 0


@pytest.mark.asyncio
async def test_5_multiple_workers_not_processing_same_job(test_session: AsyncSession, dummy_pdf: Path):
    """Scenario 5: Multiple workers / calls do not process the same document concurrently."""
    cand = User(id=uuid.uuid4(), email="c5@example.com", full_name="Candidate 5", role=UserRole.CANDIDATE)
    test_session.add(cand)
    await test_session.flush()

    doc = Document(
        candidate_id=cand.id,
        file_name="doc.pdf",
        file_path=str(dummy_pdf),
        file_hash="hash_multi",
        file_size_bytes=100,
        processing_status=DocumentProcessingStatus.QUEUED,
    )
    test_session.add(doc)
    await test_session.commit()

    service = DocumentService()
    # Artificial lock acquisition simulating active worker
    async with service._lock:
        service._active_doc_ids.add(doc.id)

    # Second concurrent worker call tries to process the same document
    session_factory = async_sessionmaker(bind=test_session.bind, expire_on_commit=False)
    await service.process_document_extraction(doc.id, session_factory=session_factory)

    # Release artificial lock
    async with service._lock:
        service._active_doc_ids.discard(doc.id)

    await test_session.refresh(doc)
    # The document was safely skipped because it was locked as in-flight
    assert doc.processing_status == DocumentProcessingStatus.QUEUED


@pytest.mark.asyncio
async def test_6_recovery_not_duplicating_extraction_results(test_session: AsyncSession, dummy_pdf: Path):
    """Scenario 6: Recovery of interrupted extraction run does not duplicate extraction results."""
    cand = User(id=uuid.uuid4(), email="c6@example.com", full_name="Candidate 6", role=UserRole.CANDIDATE)
    test_session.add(cand)
    await test_session.flush()

    doc = Document(
        candidate_id=cand.id,
        file_name="doc.pdf",
        file_path=str(dummy_pdf),
        file_hash="hash_dedup",
        file_size_bytes=100,
        page_count=1,
        extracted_text_by_page={"1": "Python Developer"},
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    test_session.add(doc)
    await test_session.flush()

    run = ExtractionRun(
        document_id=doc.id,
        run_number=1,
        status=DocumentProcessingStatus.PROCESSING,
    )
    test_session.add(run)
    await test_session.flush()

    # Add partial artifacts created before interruption
    partial_skill = CandidateSkill(
        extraction_run_id=run.id,
        candidate_id=cand.id,
        skill_name="Python",
        confidence=0.95,
    )
    partial_ev = EvidenceItem(
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Partial claim",
        source_page=1,
        source_excerpt="Python",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={},
    )
    test_session.add_all([partial_skill, partial_ev])
    await test_session.commit()

    # Run recovery
    await recover_stale_processing_jobs(test_session, enqueue=False)
    await test_session.refresh(run)

    # Partial artifacts purged, run reset to QUEUED
    assert run.status == DocumentProcessingStatus.QUEUED

    from app.repositories.domain import ExtractionRepository
    ext_repo = ExtractionRepository(test_session)
    skills = await ext_repo.get_candidate_skills_for_run(run.id)
    evidence = await ext_repo.get_evidence_items_for_run(run.id)
    assert len(skills) == 0
    assert len(evidence) == 0


@pytest.mark.asyncio
async def test_7_repeated_startup_recovery_is_safe(test_session: AsyncSession, dummy_pdf: Path):
    """Scenario 7: Repeated startup recovery is idempotent and safe."""
    cand = User(id=uuid.uuid4(), email="c7@example.com", full_name="Candidate 7", role=UserRole.CANDIDATE)
    test_session.add(cand)
    await test_session.flush()

    doc = Document(
        candidate_id=cand.id,
        file_name="doc.pdf",
        file_path=str(dummy_pdf),
        file_hash="hash_idem",
        file_size_bytes=100,
        processing_status=DocumentProcessingStatus.PROCESSING,
    )
    test_session.add(doc)
    await test_session.commit()

    # First recovery: recovers to QUEUED
    stats1 = await recover_stale_processing_jobs(test_session, enqueue=False)
    assert stats1["documents_recovered"] == 1

    await test_session.refresh(doc)
    assert doc.processing_status == DocumentProcessingStatus.QUEUED
    assert doc.processing_error.get("recovery_attempts") == 1

    # Second recovery immediately after: document remains QUEUED
    stats2 = await recover_stale_processing_jobs(test_session, enqueue=False)
    assert stats2["documents_queued"] == 1
    assert stats2["documents_recovered"] == 0

    await test_session.refresh(doc)
    assert doc.processing_status == DocumentProcessingStatus.QUEUED
    assert doc.processing_error.get("recovery_attempts") == 1


@pytest.mark.asyncio
async def test_8_document_retry_processing_success(test_session: AsyncSession, tmp_path: Path):
    """Scenario 8: Failed document can be retried without re-upload when file exists."""
    from tests.helpers import generate_sample_pdf
    pdf_bytes = generate_sample_pdf(["Bob Miller - Backend Architect", "Experience with FastAPI and Docker"])
    real_pdf = tmp_path / "valid_resume.pdf"
    real_pdf.write_bytes(pdf_bytes)

    cand = User(id=uuid.uuid4(), email="c8@example.com", full_name="Candidate 8", role=UserRole.CANDIDATE)
    test_session.add(cand)
    await test_session.flush()

    doc = Document(
        candidate_id=cand.id,
        file_name="valid_resume.pdf",
        file_path=str(real_pdf),
        file_hash="hash_retry_ok",
        file_size_bytes=len(pdf_bytes),
        processing_status=DocumentProcessingStatus.FAILED,
        processing_error={"code": "INTERRUPTED", "message": "Failed previously"},
    )
    test_session.add(doc)
    await test_session.commit()

    service = DocumentService()
    session_factory = async_sessionmaker(bind=test_session.bind, expire_on_commit=False)
    retried_doc = await service.retry_document_processing(
        document_id=doc.id,
        session_factory=session_factory,
        actor_id=str(cand.id),
    )
    assert retried_doc.processing_status == DocumentProcessingStatus.QUEUED
    assert retried_doc.processing_error is None

    # Wait for the background task to complete extraction
    await asyncio.sleep(0.2)

    await test_session.refresh(doc)
    assert doc.processing_status == DocumentProcessingStatus.COMPLETED
    assert doc.page_count == 2
    assert "FastAPI" in doc.extracted_text_by_page.get("2", "")
