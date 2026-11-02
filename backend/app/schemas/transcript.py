import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import DocumentProcessingStatus, EvidenceStatus


class TranscriptQAItemResponse(BaseModel):
    """Structured Q&A exchange with conceptual alignment and constructive coaching."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transcript_id: uuid.UUID
    question_index: int
    interviewer_question: str
    candidate_answer_excerpt: str
    start_line: int | None = None
    end_line: int | None = None
    mapped_criterion_id: uuid.UUID | None = None
    mapped_skill_name: str | None = None
    evidence_status: EvidenceStatus
    expected_concept: str
    alignment_summary: str
    coaching_suggestion: str
    clarification_requested: bool = False
    candidate_clarification_text: str | None = None
    created_at: datetime


class InterviewTranscriptResponse(BaseModel):
    """Interview transcript record with extracted Q&A pairs."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    uploader_id: uuid.UUID | None = None
    round_name: str
    file_name: str
    file_size_bytes: int
    mime_type: str
    processing_status: DocumentProcessingStatus
    created_at: datetime
    qa_items: list[TranscriptQAItemResponse] = Field(default_factory=list)


class TranscriptClarificationRequest(BaseModel):
    """Candidate request to clarify or provide context for an interview answer."""

    clarification_text: str = Field(
        ...,
        min_length=5,
        max_length=3000,
        description="Factual clarification or context regarding the interview answer",
    )
