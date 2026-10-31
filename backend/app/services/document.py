import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.core.logging import logger
from app.db.models.document import Document
from app.db.models.enums import DocumentProcessingStatus
from app.db.session import get_session_factory
from app.repositories.audit import AuditEventRepository
from app.repositories.domain import DocumentRepository
from app.services.storage import LocalStorageService
from app.utils.document import (
    PDFProcessingError,
    extract_text_by_page,
    validate_uploaded_pdf,
)


class DocumentService:
    """Service orchestrating document upload, secure storage, and text extraction."""

    _lock = asyncio.Lock()
    _active_doc_ids: set[uuid.UUID] = set()

    def __init__(
        self,
        storage_service: LocalStorageService | None = None,
    ):
        self.storage = storage_service or LocalStorageService()
        self.settings = get_settings()

    async def create_and_store_document(
        self,
        file: UploadFile,
        candidate_id: uuid.UUID,
        session: AsyncSession,
    ) -> Document:
        """
        Validates the incoming upload, saves the file to secure storage, and
        persists the initial Document record with QUEUED status.
        """
        filename = file.filename or "document.pdf"
        try:
            content = await file.read()
        except Exception as exc:
            raise ValidationError(f"Failed to read uploaded file: {str(exc)}") from exc

        # Validate file size, extension, and magic bytes
        validate_uploaded_pdf(
            filename=filename,
            content=content,
            max_size_mb=self.settings.MAX_UPLOAD_SIZE_MB,
        )

        doc_id = uuid.uuid4()
        file_path, file_hash, file_size = self.storage.save_file(
            file_content=content,
            original_filename=filename,
            document_id=doc_id,
        )

        doc = Document(
            id=doc_id,
            candidate_id=candidate_id,
            file_name=filename,
            file_path=file_path,
            file_hash=file_hash,
            file_size_bytes=file_size,
            mime_type=file.content_type or "application/pdf",
            processing_status=DocumentProcessingStatus.QUEUED,
            extracted_text_by_page={},
            processing_error=None,
        )
        session.add(doc)
        await session.flush()

        audit_repo = AuditEventRepository(session)
        await audit_repo.log_event(
            action="DOCUMENT_UPLOADED",
            resource_type="document",
            resource_id=str(doc.id),
            actor_id=str(candidate_id),
            actor_role="candidate",
            entity_version=1,
            prior_state=None,
            new_state={
                "processing_status": DocumentProcessingStatus.QUEUED.value,
                "file_name": filename,
                "file_hash": file_hash,
                "file_size_bytes": file_size,
            },
            details={
                "file_name": filename,
                "file_size_bytes": file_size,
                "mime_type": doc.mime_type,
            },
        )

        return doc

    async def process_document_extraction(
        self,
        document_id: uuid.UUID,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        """
        Background task: extracts text page-by-page from stored PDF.
        Transitions through QUEUED -> PROCESSING -> COMPLETED / FAILED.
        Is retry-safe and records structured error codes on failure.
        Includes worker concurrency locking to prevent duplicate simultaneous runs.
        """
        # Concurrency protection: prevent simultaneous processing of the same document
        async with self._lock:
            if document_id in self._active_doc_ids:
                logger.info(
                    "Document %s is already being processed; skipping duplicate task.",
                    document_id,
                )
                return
            self._active_doc_ids.add(document_id)

        try:
            factory = session_factory or get_session_factory()
            async with factory() as session:
                repo = DocumentRepository(session)
                doc = await repo.get_by_id(document_id)
                if not doc:
                    logger.error("Document %s not found for extraction", document_id)
                    return

                # If already completed, skip redundant extraction
                if doc.processing_status == DocumentProcessingStatus.COMPLETED:
                    logger.info(
                        "Document %s is already completed; skipping redundant extraction.",
                        document_id,
                    )
                    return

                # If failed and not explicitly set back to QUEUED or PROCESSING, skip
                if doc.processing_status not in (
                    DocumentProcessingStatus.QUEUED,
                    DocumentProcessingStatus.PROCESSING,
                ):
                    return

                # Transition to PROCESSING
                doc.processing_status = DocumentProcessingStatus.PROCESSING
                await session.commit()

            # Perform extraction in fresh transaction
            async with factory() as session:
                repo = DocumentRepository(session)
                doc = await repo.get_by_id(document_id)
                if not doc:
                    return

                file_path = Path(doc.file_path)
                try:
                    pages_dict = extract_text_by_page(file_path, max_pages=self.settings.MAX_PDF_PAGES)
                    # Store pages with string keys for JSON serialization
                    extracted_pages: dict[str, Any] = {
                        str(page_num): text for page_num, text in pages_dict.items()
                    }
                    doc.processing_status = DocumentProcessingStatus.COMPLETED
                    doc.page_count = len(pages_dict)
                    doc.extracted_text_by_page = extracted_pages
                    doc.processing_error = None
                    logger.info(
                        "Successfully extracted %d pages for document %s",
                        len(pages_dict),
                        document_id,
                    )
                except PDFProcessingError as exc:
                    logger.warning(
                        "Structured processing error for document %s [%s]: %s",
                        document_id,
                        exc.code,
                        exc.message,
                    )
                    doc.processing_status = DocumentProcessingStatus.FAILED
                    doc.processing_error = {
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details,
                    }
                except Exception as exc:
                    logger.exception("Unexpected error processing document %s", document_id)
                    doc.processing_status = DocumentProcessingStatus.FAILED
                    doc.processing_error = {
                        "code": "INTERNAL_PROCESSING_ERROR",
                        "message": f"Unexpected extraction error: {str(exc)}",
                        "details": {},
                    }
                finally:
                    await session.commit()
        finally:
            async with self._lock:
                self._active_doc_ids.discard(document_id)

    async def retry_document_processing(
        self,
        document_id: uuid.UUID,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        actor_id: str | None = None,
    ) -> Document:
        """
        Retries processing for an existing failed document without requiring re-upload.
        Verifies that the original file exists on disk, resets status to QUEUED,
        and schedules extraction.
        """
        factory = session_factory or get_session_factory()
        async with factory() as session:
            repo = DocumentRepository(session)
            doc = await repo.get_by_id(document_id)
            if not doc:
                raise ValidationError(f"Document {document_id} not found")

            file_path = Path(doc.file_path)
            if not file_path.exists():
                raise ValidationError(
                    f"Document file {doc.file_name} is missing from storage and cannot be retried. "
                    "Please upload the resume again."
                )

            # If already completed, nothing to retry
            if doc.processing_status == DocumentProcessingStatus.COMPLETED:
                return doc

            prior_status = doc.processing_status.value
            doc.processing_status = DocumentProcessingStatus.QUEUED
            doc.processing_error = None
            await session.commit()
            await session.refresh(doc)

            if actor_id:
                audit_repo = AuditEventRepository(session)
                await audit_repo.log_event(
                    action="DOCUMENT_RETRY_REQUESTED",
                    resource_type="document",
                    resource_id=str(doc.id),
                    actor_id=actor_id,
                    actor_role="candidate",
                    entity_version=1,
                    prior_state={"processing_status": prior_status},
                    new_state={"processing_status": DocumentProcessingStatus.QUEUED.value},
                    details={"file_name": doc.file_name},
                )
                await session.commit()

        # Trigger background processing
        asyncio.create_task(self.process_document_extraction(document_id, session_factory=factory))
        return doc

