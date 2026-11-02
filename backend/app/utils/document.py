import asyncio
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


def validate_uploaded_document(filename: str, content: bytes, max_size_mb: int = 15) -> None:
    """
    Validates uploaded document for size, extension, and magic bytes.
    Supports PDF documents (.pdf) and images (.png, .jpg, .jpeg, .webp).
    Raises ValidationError if invalid.
    """
    clean_name = filename.lower()
    allowed_exts = (".pdf", ".png", ".jpg", ".jpeg", ".webp")
    if not any(clean_name.endswith(ext) for ext in allowed_exts):
        raise ValidationError(
            f"Unsupported file format '{filename}'. Allowed formats: PDF (.pdf), PNG (.png), JPEG (.jpg, .jpeg), WebP (.webp)"
        )

    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationError(f"File size exceeds maximum allowed limit of {max_size_mb} MB")

    if len(content) == 0:
        raise ValidationError("Uploaded file is empty")

    # Magic byte validation
    if clean_name.endswith(".pdf"):
        if not content.startswith(b"%PDF-"):
            raise ValidationError("Uploaded file does not match valid PDF file format signature")
    elif clean_name.endswith(".png"):
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValidationError("Uploaded file does not match valid PNG file format signature")
    elif clean_name.endswith((".jpg", ".jpeg")):
        if not content.startswith(b"\xff\xd8\xff"):
            raise ValidationError("Uploaded file does not match valid JPEG file format signature")
    elif clean_name.endswith(".webp"):
        if not (content.startswith(b"RIFF") and len(content) > 12 and content[8:12] == b"WEBP"):
            raise ValidationError("Uploaded file does not match valid WebP file format signature")


def validate_uploaded_pdf(filename: str, content: bytes, max_size_mb: int = 15) -> None:
    """
    Strict PDF validator for backward compatibility with existing tests and PDF-only endpoints.
    """
    if not filename.lower().endswith(".pdf"):
        raise ValidationError("Only PDF documents are supported (.pdf)")
    validate_uploaded_document(filename, content, max_size_mb)


def _detect_image_mime(source_bytes: bytes, filename_or_path: str = "") -> str | None:
    """Determines image MIME type if source is an image format."""
    name = filename_or_path.lower()
    if name.endswith(".png") or source_bytes.startswith(b"\x89PNG"):
        return "image/png"
    if name.endswith((".jpg", ".jpeg")) or source_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if name.endswith(".webp") or (source_bytes.startswith(b"RIFF") and len(source_bytes) > 12 and source_bytes[8:12] == b"WEBP"):
        return "image/webp"
    return None


async def extract_text_by_page_async(
    source: bytes | Path,
    max_pages: int = 30,
    enable_ocr: bool = True,
) -> dict[int, str]:
    """
    Asynchronously extracts text from a PDF or image file while strictly preserving 1-indexed page boundaries.
    Automatically invokes multimodal Vision/OCR fallback for image resumes or scanned PDFs.
    """
    source_bytes = source.read_bytes() if isinstance(source, Path) else source
    filename_hint = str(source) if isinstance(source, Path) else ""

    # Check if direct image file
    img_mime = _detect_image_mime(source_bytes, filename_hint)
    if img_mime:
        if not enable_ocr:
            raise OCRRequiredError("Image document requires OCR/Vision extraction", {"ocr_required": True})
        from app.utils.ocr import get_vision_ocr_provider

        ocr_provider = get_vision_ocr_provider()
        return await ocr_provider.extract_text_from_images([(1, source_bytes, img_mime)])

    # Process as PDF
    stream = io.BytesIO(source_bytes)
    try:
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

        if total_chars > 0:
            return pages_dict

        # If zero digital text characters, attempt Vision OCR on embedded page images
        if enable_ocr:
            page_images: list[tuple[int, bytes, str]] = []
            for index, page in enumerate(reader.pages):
                if hasattr(page, "images") and len(page.images) > 0:
                    img = page.images[0]
                    mime = "image/png" if str(getattr(img, "name", "")).lower().endswith(".png") else "image/jpeg"
                    page_images.append((index + 1, img.data, mime))

            if page_images:
                from app.utils.ocr import get_vision_ocr_provider

                ocr_provider = get_vision_ocr_provider()
                ocr_results = await ocr_provider.extract_text_from_images(page_images)
                if ocr_results and any(len(t.strip()) > 0 for t in ocr_results.values()):
                    return ocr_results

        raise OCRRequiredError(
            "Document contains no extractable digital text. It appears to be a scanned image and OCR is required.",
            {"scanned_pages": total_pages, "ocr_required": True},
        )

    except (PasswordProtectedPDFError, PageLimitExceededError, EmptyPDFError, OCRRequiredError):
        raise
    except Exception as exc:
        raise CorruptPDFError(
            f"Failed to parse PDF document structure: {str(exc)}",
            {"original_error": str(exc)},
        ) from exc
    finally:
        stream.close()


def extract_text_by_page(source: bytes | Path, max_pages: int = 30) -> dict[int, str]:
    """
    Synchronous entry point maintaining exact backward compatibility with existing tests.
    Extracts text from digital PDF or raises appropriate PDFProcessingError.
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
