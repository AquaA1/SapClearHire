import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import DocumentProcessingStatus, EvidenceStatus

if TYPE_CHECKING:
    from app.db.models.application import Application
    from app.db.models.job import JobCriterion
    from app.db.models.user import User


class InterviewTranscript(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Candidate interview dialogue transcript for Phase 3 Interview Coach & Audit.
    Stores metadata and file path in secure storage; raw file is never stored as DB blob.
    """

    __tablename__ = "interview_transcripts"

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploader_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    round_name: Mapped[str] = mapped_column(
        String(120), default="Technical Interview", nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="text/plain", nullable=False)
    processing_status: Mapped[DocumentProcessingStatus] = mapped_column(
        Enum(
            DocumentProcessingStatus,
            name="document_processing_status",
            create_constraint=False,
            native_enum=False,
        ),
        default=DocumentProcessingStatus.QUEUED,
        nullable=False,
        index=True,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    processing_error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="transcripts",
    )
    uploader: Mapped["User | None"] = relationship("User")
    qa_items: Mapped[list["TranscriptQAItem"]] = relationship(
        "TranscriptQAItem",
        back_populates="transcript",
        cascade="all, delete-orphan",
        order_by="TranscriptQAItem.question_index",
    )


class TranscriptQAItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Extracted Question-and-Answer pair with conceptual alignment and constructive coaching.
    Adheres to strict Phase 3 bounds: verbatim quotes, no personality judging, no hiring probability.
    """

    __tablename__ = "transcript_qa_items"

    transcript_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("interview_transcripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    interviewer_question: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_answer_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Linkage to Job Criterion
    mapped_criterion_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("job_criteria.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mapped_skill_name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # Conceptual evaluation
    evidence_status: Mapped[EvidenceStatus] = mapped_column(
        Enum(
            EvidenceStatus,
            name="evidence_status",
            create_constraint=False,
            native_enum=False,
        ),
        default=EvidenceStatus.SUPPORTED,
        nullable=False,
    )
    expected_concept: Mapped[str] = mapped_column(Text, nullable=False)
    alignment_summary: Mapped[str] = mapped_column(Text, nullable=False)
    coaching_suggestion: Mapped[str] = mapped_column(Text, nullable=False)

    # Clarification lifecycle
    clarification_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    candidate_clarification_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    transcript: Mapped["InterviewTranscript"] = relationship(
        "InterviewTranscript",
        back_populates="qa_items",
    )
    mapped_criterion: Mapped["JobCriterion | None"] = relationship("JobCriterion")
