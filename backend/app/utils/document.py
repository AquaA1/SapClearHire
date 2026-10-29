import hashlib
import io
from pathlib import Path

from pypdf import PdfReader

from app.core.exceptions import ValidationError


def compute_file_sha256(content: bytes) -> str:
    """Computes SHA-256 checksum for document provenance and deduplication."""
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()


def validate_uploaded_pdf(filename: str, content: bytes, max_size_mb: int = 15) -> None:
    """
    Validates uploaded document for size, extension, and PDF magic bytes.
    Raises ValidationError if invalid.
    """
    # Check extension
    if not filename.lower().endswith(".pdf"):
        raise ValidationError("Only PDF documents are supported (.pdf)")

    # Check file size
    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationError(f"File size exceeds maximum allowed limit of {max_size_mb} MB")

    if len(content) == 0:
        raise ValidationError("Uploaded file is empty")

    # Check PDF magic bytes (%PDF-)
    if not content.startswith(b"%PDF-"):
        raise ValidationError("Uploaded file does not match valid PDF file format signature")


def extract_text_by_page(source: bytes | Path) -> dict[int, str]:
    """
    Extracts text from PDF while strictly preserving 1-indexed page boundaries.
    Returns mapping: {page_number: page_text}.
    """
    try:
        stream = io.BytesIO(source) if isinstance(source, bytes) else open(source, "rb")
        reader = PdfReader(stream)

        pages_dict: dict[int, str] = {}
        for index, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            pages_dict[index + 1] = page_text.strip()

        if isinstance(source, Path):
            stream.close()

        return pages_dict
    except Exception as exc:
        raise ValidationError(f"Failed to parse PDF document: {str(exc)}") from exc
