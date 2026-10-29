import hashlib
import io
from pathlib import Path

from pypdf import PdfReader

from app.core.exceptions import ValidationError


class PDFProcessingError(Exception):
    """Base exception for PDF parsing and extraction errors."""

    code: str = "PROCESSING_ERROR"

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class CorruptPDFError(PDFProcessingError):
    """Raised when PDF structure is damaged or malformed."""

    code = "CORRUPT_PDF"


class PasswordProtectedPDFError(PDFProcessingError):
    """Raised when PDF is encrypted or requires a password."""

    code = "PASSWORD_PROTECTED"


class PageLimitExceededError(PDFProcessingError):
    """Raised when PDF page count exceeds permitted threshold."""

    code = "PAGE_LIMIT_EXCEEDED"


class EmptyPDFError(PDFProcessingError):
    """Raised when PDF contains 0 pages."""

    code = "EMPTY_DOCUMENT"


class OCRRequiredError(PDFProcessingError):
    """Raised when PDF contains only scanned images and no extractable digital text."""

    code = "OCR_REQUIRED"


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
    if not filename.lower().endswith(".pdf"):
        raise ValidationError("Only PDF documents are supported (.pdf)")

    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationError(f"File size exceeds maximum allowed limit of {max_size_mb} MB")

    if len(content) == 0:
        raise ValidationError("Uploaded file is empty")

    # Check PDF magic bytes (%PDF-)
    if not content.startswith(b"%PDF-"):
        raise ValidationError("Uploaded file does not match valid PDF file format signature")


def extract_text_by_page(source: bytes | Path, max_pages: int = 30) -> dict[int, str]:
    """
    Extracts text from PDF while strictly preserving 1-indexed page boundaries.
    Detects scanned/image-only PDFs, password-protected files, page limits, and corruption.

    Returns mapping: {page_number: page_text}.
    """
    stream = None
    try:
        stream = io.BytesIO(source) if isinstance(source, bytes) else open(source, "rb")
        reader = PdfReader(stream)

        if reader.is_encrypted:
            raise PasswordProtectedPDFError(
                "The PDF document is password-protected or encrypted. Please provide an unencrypted document.",
                {"is_encrypted": True},
            )

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise EmptyPDFError("The PDF document contains no pages.")

        if total_pages > max_pages:
            raise PageLimitExceededError(
                f"Document has {total_pages} pages, which exceeds the maximum limit of {max_pages} pages.",
                {"page_count": total_pages, "max_pages": max_pages},
            )

        pages_dict: dict[int, str] = {}
        total_chars = 0
        for index, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            stripped = page_text.strip()
            total_chars += len(stripped)
            pages_dict[index + 1] = stripped

        if total_chars == 0:
            raise OCRRequiredError(
                "Document contains no extractable digital text. It appears to be a scanned image and OCR is required.",
                {"scanned_pages": total_pages, "ocr_required": True},
            )

        return pages_dict

    except (PasswordProtectedPDFError, PageLimitExceededError, EmptyPDFError, OCRRequiredError):
        raise
    except Exception as exc:
        raise CorruptPDFError(
            f"Failed to parse PDF document structure: {str(exc)}",
            {"original_error": str(exc)},
        ) from exc
    finally:
        if isinstance(source, Path) and stream is not None:
            stream.close()
