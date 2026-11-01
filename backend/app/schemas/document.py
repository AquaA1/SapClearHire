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


class EvidenceItemSummary(BaseModel):
    """Summary of an extracted grounded evidence item."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_text: str
    source_page: int
    source_excerpt: str
    confidence: float
    grounding_verified: bool
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateSkillSummary(BaseModel):
    """Summary of an extracted skill qualification."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill_name: str
    category: str | None = None
    confidence: float
    source_page: int | None = None
    source_excerpt: str | None = None


class ExtractionRunResponse(BaseModel):
    """Response returned when querying AI evidence extraction results."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    run_number: int
    provider: str
    model_name: str
    status: DocumentProcessingStatus
    error_message: str | None = None
    skills: list[CandidateSkillSummary] = Field(default_factory=list)
    evidence_items: list[EvidenceItemSummary] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None
    raw_output: dict[str, Any] | None = None
