import uuid

import pytest
from httpx import AsyncClient

from app.core.security import UserRole, create_access_token
from tests.helpers import generate_blank_pdf, generate_sample_pdf


@pytest.mark.asyncio
async def test_candidate_upload_and_poll_status_success(client: AsyncClient):
    candidate_id = str(uuid.uuid4())
    token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    pdf_content = generate_sample_pdf(
        [
            "Alice Smith - Senior Python Engineer at TechCorp",
            "Core skills: FastAPI, PostgreSQL, Docker, Kubernetes",
        ]
    )

    files = {"file": ("alice_resume.pdf", pdf_content, "application/pdf")}
    res = await client.post("/api/v1/documents", headers=headers, files=files)

    assert res.status_code == 202
    data = res.json()
    assert "id" in data
    doc_id = data["id"]
    assert data["file_name"] == "alice_resume.pdf"
    assert data["file_size_bytes"] == len(pdf_content)
    assert data["processing_status"] in ("queued", "processing", "completed")

    # Poll status endpoint
    status_res = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["id"] == doc_id
    assert status_data["processing_status"] == "completed"
    assert status_data["page_count"] == 2
    assert "1" in status_data["extracted_text_by_page"]
    assert "2" in status_data["extracted_text_by_page"]
    assert "Alice Smith" in status_data["extracted_text_by_page"]["1"]
    assert "FastAPI" in status_data["extracted_text_by_page"]["2"]
    assert status_data["processing_error"] is None


@pytest.mark.asyncio
async def test_candidate_cannot_view_another_candidates_document(client: AsyncClient):
    candidate_a = str(uuid.uuid4())
    candidate_b = str(uuid.uuid4())

    token_a = create_access_token(subject=candidate_a, role=UserRole.CANDIDATE)
    token_b = create_access_token(subject=candidate_b, role=UserRole.CANDIDATE)

    pdf_content = generate_sample_pdf(["Confidential Candidate A Resume"])
    files = {"file": ("resume_a.pdf", pdf_content, "application/pdf")}

    upload_res = await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token_a}"},
        files=files,
    )
    doc_id = upload_res.json()["id"]

    # Candidate B attempts to poll Candidate A's document
    forbidden_res = await client.get(
        f"/api/v1/documents/{doc_id}/status",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden_res.status_code == 403
    assert forbidden_res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_reviewer_can_view_candidate_document_status(client: AsyncClient):
    candidate_id = str(uuid.uuid4())
    reviewer_id = str(uuid.uuid4())

    candidate_token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)
    reviewer_token = create_access_token(subject=reviewer_id, role=UserRole.REVIEWER)

    pdf_content = generate_sample_pdf(["Reviewer Accessible Candidate Resume"])
    files = {"file": ("resume.pdf", pdf_content, "application/pdf")}

    upload_res = await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {candidate_token}"},
        files=files,
    )
    doc_id = upload_res.json()["id"]

    # Reviewer polls candidate status
    reviewer_res = await client.get(
        f"/api/v1/documents/{doc_id}/status",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert reviewer_res.status_code == 200
    assert reviewer_res.json()["id"] == doc_id


@pytest.mark.asyncio
async def test_upload_scanned_blank_pdf_results_in_ocr_required_status(client: AsyncClient):
    candidate_id = str(uuid.uuid4())
    token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    blank_pdf = generate_blank_pdf(page_count=1)
    files = {"file": ("scanned_resume.pdf", blank_pdf, "application/pdf")}

    upload_res = await client.post("/api/v1/documents", headers=headers, files=files)
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["id"]

    status_res = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["processing_status"] == "failed"
    assert status_data["processing_error"] is not None
    assert status_data["processing_error"]["code"] == "OCR_REQUIRED"
    assert "OCR is required" in status_data["processing_error"]["message"]
    assert status_data["processing_error"]["details"]["ocr_required"] is True


@pytest.mark.asyncio
async def test_upload_corrupt_pdf_results_in_corrupt_pdf_status(client: AsyncClient):
    candidate_id = str(uuid.uuid4())
    token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    corrupt_content = b"%PDF-1.4\nCorrupted binary junk without proper trailer or stream EOF"
    files = {"file": ("corrupt.pdf", corrupt_content, "application/pdf")}

    upload_res = await client.post("/api/v1/documents", headers=headers, files=files)
    assert upload_res.status_code == 202
    doc_id = upload_res.json()["id"]

    status_res = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["processing_status"] == "failed"
    assert status_data["processing_error"] is not None
    assert status_data["processing_error"]["code"] == "CORRUPT_PDF"


@pytest.mark.asyncio
async def test_upload_invalid_extension_rejected_immediately(client: AsyncClient):
    candidate_id = str(uuid.uuid4())
    token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("resume.docx", b"PK\x03\x04docx_binary_data", "application/vnd.ms-word")}
    res = await client.post("/api/v1/documents", headers=headers, files=files)

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "Only PDF documents are supported" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_upload_empty_file_rejected_immediately(client: AsyncClient):
    candidate_id = str(uuid.uuid4())
    token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("empty.pdf", b"", "application/pdf")}
    res = await client.post("/api/v1/documents", headers=headers, files=files)

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "Uploaded file is empty" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_get_nonexistent_document_returns_404(client: AsyncClient):
    candidate_id = str(uuid.uuid4())
    token = create_access_token(subject=candidate_id, role=UserRole.CANDIDATE)
    headers = {"Authorization": f"Bearer {token}"}

    missing_id = str(uuid.uuid4())
    res = await client.get(f"/api/v1/documents/{missing_id}/status", headers=headers)

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
    pdf_content = generate_sample_pdf(["Test resume"])
    files = {"file": ("resume.pdf", pdf_content, "application/pdf")}

    res = await client.post("/api/v1/documents", files=files)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    res_get = await client.get(f"/api/v1/documents/{uuid.uuid4()}/status")
    assert res_get.status_code == 401
    assert res_get.json()["error"]["code"] == "AUTHENTICATION_FAILED"
