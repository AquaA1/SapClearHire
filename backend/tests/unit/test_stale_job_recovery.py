import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserRole
from app.db.models.document import Document, ExtractionRun
from app.db.models.enums import DocumentProcessingStatus
from app.db.models.user import User
from app.main import recover_stale_processing_jobs


@pytest.mark.asyncio
async def test_recover_stale_processing_jobs_on_startup(test_session: AsyncSession):
    """Verify that in-flight QUEUED/PROCESSING jobs are marked FAILED on startup."""
    user = User(
        id=uuid.uuid4(),
        email=f"candidate-{uuid.uuid4().hex[:6]}@example.com",
        full_name="Stale Candidate",
        role=UserRole.CANDIDATE,
    )
    test_session.add(user)
    await test_session.flush()

    doc_queued = Document(
        candidate_id=user.id,
        file_name="stale_queued.pdf",
        file_path="/tmp/stale_queued.pdf",
        file_hash="hash1",
        file_size_bytes=100,
        processing_status=DocumentProcessingStatus.QUEUED,
    )
    doc_processing = Document(
        candidate_id=user.id,
        file_name="stale_processing.pdf",
        file_path="/tmp/stale_processing.pdf",
        file_hash="hash2",
        file_size_bytes=200,
        processing_status=DocumentProcessingStatus.PROCESSING,
    )
    doc_completed = Document(
        candidate_id=user.id,
        file_name="completed.pdf",
        file_path="/tmp/completed.pdf",
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

    # Run recovery
    await recover_stale_processing_jobs(test_session)

    # Verify updated statuses
    await test_session.refresh(doc_queued)
    await test_session.refresh(doc_processing)
    await test_session.refresh(doc_completed)
    await test_session.refresh(run_queued)
    await test_session.refresh(run_processing)

    assert doc_queued.processing_status == DocumentProcessingStatus.FAILED
    assert doc_queued.processing_error.get("code") == "SERVER_RESTARTED"

    assert doc_processing.processing_status == DocumentProcessingStatus.FAILED
    assert doc_processing.processing_error.get("code") == "SERVER_RESTARTED"

    assert doc_completed.processing_status == DocumentProcessingStatus.COMPLETED

    assert run_queued.status == DocumentProcessingStatus.FAILED
    assert "server restart" in run_queued.error_message

    assert run_processing.status == DocumentProcessingStatus.FAILED
    assert "server restart" in run_processing.error_message
