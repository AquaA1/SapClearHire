import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import UserRole, create_access_token
from app.db.models.document import Document, ExtractionRun
from app.db.models.enums import DocumentProcessingStatus
from app.db.models.user import User
from app.integrations.llm.fake import FakeLLMProvider
from app.integrations.llm.schemas import (
    ExtractedResumeProfile,
    ExtractedSkill,
    SourceQuote,
)
from app.services.extraction import AIExtractionService
from tests.helpers import (
    generate_blank_pdf,
    generate_encrypted_pdf,
    generate_sample_pdf,
)


@pytest.mark.asyncio
async def test_1_pdf_upload_and_persisted_document(client: AsyncClient, test_engine):
    """Test 1: Upload persists the document to DB before background processing."""
    candidate_id = str(uuid.uuid4())
    token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    pdf_content = generate_sample_pdf(["Jane Doe - Backend Engineer with Python"])
    files = {"file": ("jane_resume.pdf", pdf_content, "application/pdf")}

    res = await client.post("/api/v1/documents", headers=headers, files=files)
    assert res.status_code == 202
    data = res.json()
    doc_id = uuid.UUID(data["id"])
    assert data["file_name"] == "jane_resume.pdf"
    assert data["processing_status"] in ("queued", "processing", "completed")

    # Verify directly in the database that the document is already committed
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        query = select(Document).where(Document.id == doc_id)
        result = await session.execute(query)
        db_doc = result.scalar_one_or_none()
        assert db_doc is not None
        assert db_doc.file_name == "jane_resume.pdf"
        assert db_doc.candidate_id == uuid.UUID(candidate_id)


@pytest.mark.asyncio
async def test_2_pdf_text_extraction_with_page_count(client: AsyncClient):
    """Test 2: PDF text extraction runs and persists page count and extracted text by page."""
    candidate_id = str(uuid.uuid4())
    token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    pdf_content = generate_sample_pdf(
        [
            "Page 1: Jane Doe, Senior Python Developer at TechCorp.",
            "Page 2: Core technologies include FastAPI, PostgreSQL, and Docker.",
        ]
    )
    files = {"file": ("multipage_resume.pdf", pdf_content, "application/pdf")}

    upload_res = await client.post("/api/v1/documents", headers=headers, files=files)
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["id"]

    status_res = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["processing_status"] == "completed"
    assert status_data["page_count"] == 2
    assert "1" in status_data["extracted_text_by_page"]
    assert "2" in status_data["extracted_text_by_page"]
    assert "Jane Doe" in status_data["extracted_text_by_page"]["1"]
    assert "FastAPI" in status_data["extracted_text_by_page"]["2"]


@pytest.mark.asyncio
async def test_3_invalid_pdf_handling(client: AsyncClient):
    """Test 3: Corrupt, password-protected, scanned blank, and empty PDFs are rejected/marked failed."""
    candidate_id = str(uuid.uuid4())
    token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    # 3a. Empty file
    empty_res = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert empty_res.status_code == 422
    assert empty_res.json()["error"]["code"] == "VALIDATION_ERROR"

    # 3b. Corrupt PDF
    corrupt_bytes = b"%PDF-1.4\nNon-standard corrupt bytes without header or trailer"
    corrupt_res = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("corrupt.pdf", corrupt_bytes, "application/pdf")},
    )
    assert corrupt_res.status_code == 202
    corrupt_doc_id = corrupt_res.json()["id"]
    corrupt_status = await client.get(f"/api/v1/documents/{corrupt_doc_id}/status", headers=headers)
    assert corrupt_status.status_code == 200
    assert corrupt_status.json()["processing_status"] == "failed"
    assert corrupt_status.json()["processing_error"]["code"] == "CORRUPT_PDF"

    # 3c. Password-protected PDF
    encrypted_bytes = generate_encrypted_pdf("secretpass")
    encrypted_res = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("encrypted.pdf", encrypted_bytes, "application/pdf")},
    )
    assert encrypted_res.status_code == 202
    enc_doc_id = encrypted_res.json()["id"]
    enc_status = await client.get(f"/api/v1/documents/{enc_doc_id}/status", headers=headers)
    assert enc_status.status_code == 200
    assert enc_status.json()["processing_status"] == "failed"
    assert enc_status.json()["processing_error"]["code"] == "PASSWORD_PROTECTED"

    # 3d. Scanned blank PDF (no digital text)
    blank_bytes = generate_blank_pdf(page_count=1)
    blank_res = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("blank.pdf", blank_bytes, "application/pdf")},
    )
    assert blank_res.status_code == 202
    blank_doc_id = blank_res.json()["id"]
    blank_status = await client.get(f"/api/v1/documents/{blank_doc_id}/status", headers=headers)
    assert blank_status.status_code == 200
    assert blank_status.json()["processing_status"] == "failed"
    assert blank_status.json()["processing_error"]["code"] == "OCR_REQUIRED"


@pytest.mark.asyncio
async def test_4_ai_extraction_before_pdf_completion_returns_409(client: AsyncClient, test_engine):
    """Test 4: AI extraction is rejected with HTTP 409 if PDF processing is still queued or processing."""
    candidate_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    token = create_access_token(subject=str(candidate_id), role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        user = User(
            id=candidate_id,
            email=f"{candidate_id}@example.com",
            full_name="Test User",
            role=UserRole.CANDIDATE,
        )
        doc = Document(
            id=doc_id,
            candidate_id=candidate_id,
            file_name="queued_resume.pdf",
            file_path="/storage/queued.pdf",
            file_hash="mock_hash_1",
            file_size_bytes=512,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.PROCESSING,
            extracted_text_by_page={},
        )
        session.add(user)
        session.add(doc)
        await session.commit()

    res = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "CONFLICT"
    assert "still in progress" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_5_extraction_run_persisted_before_http_202(client: AsyncClient, test_engine):
    """Test 5: ExtractionRun database record is committed before returning HTTP 202."""
    candidate_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    token = create_access_token(subject=str(candidate_id), role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        user = User(
            id=candidate_id,
            email=f"{candidate_id}@example.com",
            full_name="Jane Dev",
            role=UserRole.CANDIDATE,
        )
        doc = Document(
            id=doc_id,
            candidate_id=candidate_id,
            file_name="ready.pdf",
            file_path="/storage/ready.pdf",
            file_hash="mock_hash_ready",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            extracted_text_by_page={"1": "Jane Dev. Senior Python Engineer."},
        )
        session.add(user)
        session.add(doc)
        await session.commit()

    res = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=headers)
    assert res.status_code == 202
    data = res.json()
    run_id = uuid.UUID(data["id"])

    # Verify that the extraction run actually exists in DB
    async with session_factory() as session:
        db_run = await session.get(ExtractionRun, run_id)
        assert db_run is not None
        assert db_run.document_id == doc_id
        assert db_run.run_number == 1
        assert db_run.status in (
            DocumentProcessingStatus.QUEUED,
            DocumentProcessingStatus.PROCESSING,
            DocumentProcessingStatus.COMPLETED,
        )


@pytest.mark.asyncio
async def test_6_immediate_get_extraction_results_returns_200_not_404(
    client: AsyncClient, test_engine
):
    """Test 6: Immediate GET /extraction-results after POST /extract returns HTTP 200 with queued status, never 404."""
    candidate_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    token = create_access_token(subject=str(candidate_id), role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        user = User(
            id=candidate_id,
            email=f"{candidate_id}@example.com",
            full_name="Jane Dev",
            role=UserRole.CANDIDATE,
        )
        doc = Document(
            id=doc_id,
            candidate_id=candidate_id,
            file_name="ready2.pdf",
            file_path="/storage/ready2.pdf",
            file_hash="mock_hash_ready2",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            extracted_text_by_page={"1": "Jane Dev. Python Developer."},
        )
        session.add(user)
        session.add(doc)
        await session.commit()

    post_res = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=headers)
    assert post_res.status_code == 202
    run_id = post_res.json()["id"]

    # Immediate GET must return 200, never 404
    get_res = await client.get(f"/api/v1/documents/{doc_id}/extraction-results", headers=headers)
    assert get_res.status_code == 200
    res_data = get_res.json()
    assert res_data["id"] == run_id
    assert res_data["document_id"] == str(doc_id)
    assert res_data["status"] in ("queued", "processing", "completed")


@pytest.mark.asyncio
async def test_7_background_task_receives_actual_run_id_and_completes(test_engine):
    """Test 7: Background task receives actual persisted run ID and updates that exact run through completed."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    candidate_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    run_id = uuid.uuid4()

    async with session_factory() as session:
        user = User(
            id=candidate_id,
            email=f"{candidate_id}@test.com",
            full_name="Bob Worker",
            role=UserRole.CANDIDATE,
        )
        doc = Document(
            id=doc_id,
            candidate_id=candidate_id,
            file_name="worker.pdf",
            file_path="/storage/worker.pdf",
            file_hash="mock_hash_worker",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            extracted_text_by_page={"1": "Bob Worker. Python and Docker experience."},
        )
        run = ExtractionRun(
            id=run_id,
            document_id=doc_id,
            run_number=1,
            provider="fake",
            model_name="deterministic-stub-v1",
            status=DocumentProcessingStatus.QUEUED,
        )
        session.add(user)
        session.add(doc)
        session.add(run)
        await session.commit()

    service = AIExtractionService(
        llm_provider=FakeLLMProvider(),
        session_factory=session_factory,
    )
    completed_run, skills, evidence = await service.extract_and_persist(
        document_id=doc_id, run_id=run_id
    )

    assert completed_run.id == run_id
    assert completed_run.status == DocumentProcessingStatus.COMPLETED
    assert completed_run.completed_at is not None

    # Verify directly in DB that the exact run is COMPLETED
    async with session_factory() as session:
        db_run = await session.get(ExtractionRun, run_id)
        assert db_run is not None
        assert db_run.status == DocumentProcessingStatus.COMPLETED
        assert db_run.completed_at is not None


@pytest.mark.asyncio
async def test_8_successful_extraction_persists_skills_and_evidence(
    client: AsyncClient, test_engine
):
    """Test 8: Successful extraction persists candidate skills and grounded evidence items."""
    candidate_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    token = create_access_token(subject=str(candidate_id), role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        user = User(
            id=candidate_id,
            email=f"{candidate_id}@example.com",
            full_name="Alice Developer",
            role=UserRole.CANDIDATE,
        )
        doc = Document(
            id=doc_id,
            candidate_id=candidate_id,
            file_name="alice.pdf",
            file_path="/storage/alice.pdf",
            file_hash="mock_hash_alice",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            extracted_text_by_page={
                "1": "Alice Developer. 6 years Python and FastAPI experience. PostgreSQL database architect."
            },
        )
        session.add(user)
        session.add(doc)
        await session.commit()

    service = AIExtractionService(
        llm_provider=FakeLLMProvider(),
        session_factory=session_factory,
    )
    run, skills, evidence = await service.extract_and_persist(document_id=doc_id)

    assert run.status == DocumentProcessingStatus.COMPLETED
    assert len(skills) >= 2
    assert len(evidence) >= 2

    # Query endpoint
    res = await client.get(f"/api/v1/documents/{doc_id}/extraction-results", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert len(data["skills"]) >= 2
    assert len(data["evidence_items"]) >= 2

    # Verify grounding verified on evidence
    for item in data["evidence_items"]:
        assert item["grounding_verified"] is True
        assert item["confidence"] > 0.0
        assert item["source_page"] == 1


@pytest.mark.asyncio
async def test_9_provider_failure_persists_failed_run_with_error_and_completed_at(
    test_engine,
):
    """Test 9: Provider failure persists a failed run with error message and completed_at."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    candidate_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    run_id = uuid.uuid4()

    async with session_factory() as session:
        user = User(
            id=candidate_id,
            email=f"{candidate_id}@test.com",
            full_name="Crash Test",
            role=UserRole.CANDIDATE,
        )
        doc = Document(
            id=doc_id,
            candidate_id=candidate_id,
            file_name="crash.pdf",
            file_path="/storage/crash.pdf",
            file_hash="mock_hash_crash",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            extracted_text_by_page={"1": "Valid resume text."},
        )
        run = ExtractionRun(
            id=run_id,
            document_id=doc_id,
            run_number=1,
            provider="fake",
            model_name="failing-model",
            status=DocumentProcessingStatus.QUEUED,
        )
        session.add(user)
        session.add(doc)
        session.add(run)
        await session.commit()

    failing_provider = FakeLLMProvider(simulate_error=RuntimeError("Simulated LLM network timeout"))
    service = AIExtractionService(
        llm_provider=failing_provider,
        session_factory=session_factory,
    )

    with pytest.raises(RuntimeError, match="Simulated LLM network timeout"):
        await service.extract_and_persist(document_id=doc_id, run_id=run_id)

    # Verify run in DB is FAILED with error_message and completed_at
    async with session_factory() as session:
        db_run = await session.get(ExtractionRun, run_id)
        assert db_run is not None
        assert db_run.status == DocumentProcessingStatus.FAILED
        assert "Simulated LLM network timeout" in (db_run.error_message or "")
        assert db_run.completed_at is not None


@pytest.mark.asyncio
async def test_10_failed_runs_remain_retrievable_via_get_results(client: AsyncClient, test_engine):
    """Test 10: Failed runs remain retrievable via GET /extraction-results (never 404)."""
    candidate_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    run_id = uuid.uuid4()
    token = create_access_token(subject=str(candidate_id), role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        user = User(
            id=candidate_id,
            email=f"{candidate_id}@example.com",
            full_name="Failed Run User",
            role=UserRole.CANDIDATE,
        )
        doc = Document(
            id=doc_id,
            candidate_id=candidate_id,
            file_name="failed_run.pdf",
            file_path="/storage/failed_run.pdf",
            file_hash="mock_hash_failed",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            extracted_text_by_page={"1": "Text."},
        )
        run = ExtractionRun(
            id=run_id,
            document_id=doc_id,
            run_number=1,
            provider="fake",
            model_name="failing-model",
            status=DocumentProcessingStatus.FAILED,
            error_message="Upstream API rate limit exceeded",
        )
        session.add(user)
        session.add(doc)
        session.add(run)
        await session.commit()

    res = await client.get(f"/api/v1/documents/{doc_id}/extraction-results", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(run_id)
    assert data["status"] == "failed"
    assert data["error_message"] == "Upstream API rate limit exceeded"
    assert data["skills"] == []
    assert data["evidence_items"] == []


@pytest.mark.asyncio
async def test_11_unsupported_source_excerpts_grounding_verified_false(test_engine):
    """Test 11: Unsupported / hallucinated excerpts are rejected with grounding_verified=False and confidence 0.0."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    candidate_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    run_id = uuid.uuid4()

    async with session_factory() as session:
        user = User(
            id=candidate_id,
            email=f"{candidate_id}@test.com",
            full_name="Ungrounded Candidate",
            role=UserRole.CANDIDATE,
        )
        doc = Document(
            id=doc_id,
            candidate_id=candidate_id,
            file_name="unsupported.pdf",
            file_path="/storage/unsupported.pdf",
            file_hash="mock_hash_unsupported",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            extracted_text_by_page={"1": "Real text: Jane has 3 years of basic Python experience."},
        )
        run = ExtractionRun(
            id=run_id,
            document_id=doc_id,
            run_number=1,
            provider="fake",
            model_name="deterministic-stub-v1",
            status=DocumentProcessingStatus.QUEUED,
        )
        session.add(user)
        session.add(doc)
        session.add(run)
        await session.commit()

    # Create profile with an unsupported excerpt that is NOT in the resume text
    hallucinated_quote = SourceQuote(
        page_number=1,
        exact_excerpt="Invented Hallucinated Quantum Computing Architect Excerpt",
        start_char=0,
        end_char=50,
    )
    custom_profile = ExtractedResumeProfile(
        candidate_name="Ungrounded Candidate",
        skills=[
            ExtractedSkill(
                skill_name="Quantum Computing",
                category="Emerging Tech",
                confidence=0.98,
                source_quote=hallucinated_quote,
            )
        ],
        experiences=[],
        projects=[],
        education=[],
    )

    provider = FakeLLMProvider(custom_profile_override=custom_profile)
    service = AIExtractionService(
        llm_provider=provider,
        session_factory=session_factory,
    )

    completed_run, skills, evidence = await service.extract_and_persist(
        document_id=doc_id, run_id=run_id
    )

    assert completed_run.status == DocumentProcessingStatus.COMPLETED
    assert len(evidence) == 1
    assert len(skills) == 1

    # Exact source quote and page are preserved verbatim
    assert evidence[0].source_excerpt == "Invented Hallucinated Quantum Computing Architect Excerpt"
    assert evidence[0].source_page == 1

    # Grounding is marked False, and confidence is set to 0.0
    assert evidence[0].grounding_verified is False
    assert evidence[0].confidence == 0.0
    assert skills[0].confidence == 0.0


@pytest.mark.asyncio
async def test_12_repeated_extraction_requests_do_not_create_duplicate_runs(
    client: AsyncClient, test_engine
):
    """Test 12: Repeated extraction requests while a run is in-flight return the existing run without creating duplicates."""
    candidate_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    token = create_access_token(subject=str(candidate_id), role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        user = User(
            id=candidate_id,
            email=f"{candidate_id}@example.com",
            full_name="Duplicate Test User",
            role=UserRole.CANDIDATE,
        )
        doc = Document(
            id=doc_id,
            candidate_id=candidate_id,
            file_name="idempotent.pdf",
            file_path="/storage/idempotent.pdf",
            file_hash="mock_hash_idempotent",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            extracted_text_by_page={"1": "Idempotent resume text."},
        )
        session.add(user)
        session.add(doc)
        await session.commit()

    run_id = uuid.uuid4()
    async with session_factory() as session:
        in_flight_run = ExtractionRun(
            id=run_id,
            document_id=doc_id,
            run_number=1,
            provider="fake",
            model_name="deterministic-stub-v1",
            status=DocumentProcessingStatus.PROCESSING,
        )
        session.add(in_flight_run)
        await session.commit()

    # First trigger: detects in-flight run and returns it without creating a new run
    res1 = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=headers)
    assert res1.status_code == 202
    run1_id = res1.json()["id"]

    # Second trigger: also returns the in-flight run
    res2 = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=headers)
    assert res2.status_code == 202
    run2_id = res2.json()["id"]

    assert run1_id == str(run_id)
    assert run2_id == str(run_id)

    # Verify that only 1 ExtractionRun row exists in DB for this document
    async with session_factory() as session:
        query = select(func.count(ExtractionRun.id)).where(ExtractionRun.document_id == doc_id)
        count = (await session.execute(query)).scalar_one()
        assert count == 1
