import tempfile
import uuid
from pathlib import Path

import pytest

from app.core.exceptions import ValidationError
from app.services.storage import LocalStorageService
from app.utils.document import (
    CorruptPDFError,
    OCRRequiredError,
    PageLimitExceededError,
    PasswordProtectedPDFError,
    compute_file_sha256,
    extract_text_by_page,
    validate_uploaded_pdf,
)
from tests.helpers import (
    generate_blank_pdf,
    generate_encrypted_pdf,
    generate_sample_pdf,
)


def test_validate_uploaded_pdf_accepts_valid():
    content = generate_sample_pdf(["Valid resume text"])
    validate_uploaded_pdf("candidate_resume.pdf", content, max_size_mb=15)


def test_validate_uploaded_pdf_rejects_non_pdf():
    content = b"%PDF-valid_header_but_wrong_ext"
    with pytest.raises(ValidationError) as exc_info:
        validate_uploaded_pdf("resume.docx", content)
    assert "Only PDF documents are supported" in str(exc_info.value)


def test_validate_uploaded_pdf_rejects_empty_file():
    with pytest.raises(ValidationError) as exc_info:
        validate_uploaded_pdf("empty.pdf", b"")
    assert "Uploaded file is empty" in str(exc_info.value)


def test_validate_uploaded_pdf_rejects_oversized_file():
    # 2 MB limit for test
    oversized = b"%PDF-" + (b"0" * (2 * 1024 * 1024 + 10))
    with pytest.raises(ValidationError) as exc_info:
        validate_uploaded_pdf("big.pdf", oversized, max_size_mb=2)
    assert "exceeds maximum allowed limit" in str(exc_info.value)


def test_validate_uploaded_pdf_rejects_invalid_magic_bytes():
    fake_content = b"PK\x03\x04not_a_pdf"
    with pytest.raises(ValidationError) as exc_info:
        validate_uploaded_pdf("fake.pdf", fake_content)
    assert "signature" in str(exc_info.value)


def test_extract_text_by_page_preserves_pages():
    page1 = "Alice Smith - Staff Backend Engineer at TechCorp"
    page2 = "Education: BS Computer Science, MIT 2018"
    pdf_bytes = generate_sample_pdf([page1, page2])

    pages = extract_text_by_page(pdf_bytes)
    assert len(pages) == 2
    assert 1 in pages and 2 in pages
    assert "Alice Smith" in pages[1]
    assert "MIT 2018" in pages[2]


def test_extract_text_scanned_pdf_reports_ocr_needed():
    blank_pdf = generate_blank_pdf(page_count=2)
    with pytest.raises(OCRRequiredError) as exc_info:
        extract_text_by_page(blank_pdf)

    assert exc_info.value.code == "OCR_REQUIRED"
    assert "OCR is required" in exc_info.value.message
    assert exc_info.value.details.get("ocr_required") is True


def test_extract_text_corrupt_pdf():
    corrupt_pdf = b"%PDF-1.4\ncorrupted_binary_garbage_stream_eof_missing"
    with pytest.raises(CorruptPDFError) as exc_info:
        extract_text_by_page(corrupt_pdf)

    assert exc_info.value.code == "CORRUPT_PDF"
    assert "Failed to parse PDF document structure" in exc_info.value.message


def test_extract_text_password_protected_pdf():
    encrypted_pdf = generate_encrypted_pdf(password="secret123")
    with pytest.raises(PasswordProtectedPDFError) as exc_info:
        extract_text_by_page(encrypted_pdf)

    assert exc_info.value.code == "PASSWORD_PROTECTED"
    assert "password-protected" in exc_info.value.message


def test_extract_text_page_limit_exceeded():
    pages = [f"Page {i} content" for i in range(1, 6)]
    pdf_bytes = generate_sample_pdf(pages)
    with pytest.raises(PageLimitExceededError) as exc_info:
        extract_text_by_page(pdf_bytes, max_pages=3)

    assert exc_info.value.code == "PAGE_LIMIT_EXCEEDED"
    assert exc_info.value.details["page_count"] == 5
    assert exc_info.value.details["max_pages"] == 3


def test_local_storage_service():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageService(base_dir=tmpdir)
        doc_id = uuid.uuid4()
        content = generate_sample_pdf(["Storage test resume"])

        file_path, file_hash, file_size = storage.save_file(
            file_content=content,
            original_filename="../../../evil/traversal.pdf",
            document_id=doc_id,
        )

        # Ensure safe naming without path traversal
        assert Path(file_path).name == f"{doc_id}.pdf"
        assert Path(file_path).exists()
        assert file_hash == compute_file_sha256(content)
        assert file_size == len(content)

        # Verify deletion
        storage.delete_file(file_path)
        assert not Path(file_path).exists()
