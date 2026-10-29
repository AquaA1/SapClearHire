import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import DocumentProcessingStatus


class DocumentUploadResponse(BaseModel):
    """Response returned immediately upon successful document upload."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    file_hash: str
    file_size_bytes: int
    processing_status: DocumentProcessingStatus
    created_at: datetime


class DocumentStatusResponse(BaseModel):
    """Response returned when polling document processing status and extracted text."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    processing_status: DocumentProcessingStatus
    page_count: int | None = None
    extracted_text_by_page: dict[str, str] = Field(default_factory=dict)
    processing_error: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
