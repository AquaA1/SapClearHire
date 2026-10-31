import uuid
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserRole
from app.db.models.document import Document, ExtractionRun
from app.db.models.enums import DocumentProcessingStatus
from app.db.models.user import User
from app.main import recover_stale_processing_jobs


@pytest.mark.asyncio
async def test_recover_stale_processing_jobs_on_startup(
    test_session: AsyncSession, tmp_path: Path
):
    """
    Verify that in-flight jobs are recovered safely on startup:
    - QUEUED documents remain QUEUED (not failed).
    - PROCESSING documents interrupted by restart are safely recovered to QUEUED.
    - COMPLETED documents remain COMPLETED.
    - Extraction runs are safely queued/recovered without permanent failure.
    """
    user = User(
        id=uuid.uuid4(),
        email=f"candidate-{uuid.uuid4().hex[:6]}@example.com",
        full_name="Stale Candidate",
        role=UserRole.CANDIDATE,
    )
    test_session.add(user)
    await test_session.flush()

    # Create real files on disk
    file1 = tmp_path / "stale_queued.pdf"
    file1.write_bytes(b"%PDF-1.4 dummy content 1")
    file2 = tmp_path / "stale_processing.pdf"
    file2.write_bytes(b"%PDF-1.4 dummy content 2")
    file3 = tmp_path / "completed.pdf"
    file3.write_bytes(b"%PDF-1.4 dummy content 3")

    doc_queued = Document(
        candidate_id=user.id,
        file_name="stale_queued.pdf",
        file_path=str(file1),
        file_hash="hash1",
        file_size_bytes=100,
        processing_status=DocumentProcessingStatus.QUEUED,
    )
    doc_processing = Document(
        candidate_id=user.id,
        file_name="stale_processing.pdf",
        file_path=str(file2),
        file_hash="hash2",
        file_size_bytes=200,
        processing_status=DocumentProcessingStatus.PROCESSING,
    )
    doc_completed = Document(
        candidate_id=user.id,
        file_name="completed.pdf",
        file_path=str(file3),
        file_hash="hash3",
        file_size_bytes=300,
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    test_session.add_all([doc_queued, doc_processing, doc_completed])
    await test_session.flush()

    run_queued = ExtractionRun(
        document_id=doc_completed.id,
        run_number=1,
        status=DocumentProcessingStatus.QUEUED,
    )
    run_processing = ExtractionRun(
        document_id=doc_completed.id,
        run_number=2,
        status=DocumentProcessingStatus.PROCESSING,
    )
    test_session.add_all([run_queued, run_processing])
    await test_session.commit()

    # Run recovery (enqueue=False for unit session verification)
    await recover_stale_processing_jobs(test_session, enqueue=False)

    # Verify updated statuses
    await test_session.refresh(doc_queued)
    await test_session.refresh(doc_processing)
    await test_session.refresh(doc_completed)
    await test_session.refresh(run_queued)
    await test_session.refresh(run_processing)

    # Queued jobs must remain queued and not be permanently failed
    assert doc_queued.processing_status == DocumentProcessingStatus.QUEUED

    # Interrupted processing jobs must be safely recovered to QUEUED with recovery attempts tracked
    assert doc_processing.processing_status == DocumentProcessingStatus.QUEUED
    assert doc_processing.processing_error.get("recovery_attempts") == 1

    # Completed documents must remain untouched
    assert doc_completed.processing_status == DocumentProcessingStatus.COMPLETED

    # Extraction runs must be safely recovered to QUEUED
    assert run_queued.status == DocumentProcessingStatus.QUEUED
    assert run_processing.status == DocumentProcessingStatus.QUEUED
    assert run_processing.raw_output.get("recovery_attempts") == 1

