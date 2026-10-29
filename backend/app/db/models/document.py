import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import DocumentProcessingStatus

if TYPE_CHECKING:
    from app.db.models.application import Application
    from app.db.models.evaluation import CriterionEvidence, Evaluation
    from app.db.models.user import User


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Uploaded candidate document (resume, portfolio, transcript) with preserved page layout."""

    __tablename__ = "documents"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf", nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_text_by_page: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    processing_status: Mapped[DocumentProcessingStatus] = mapped_column(
        Enum(DocumentProcessingStatus, native_enum=False, length=50),
        default=DocumentProcessingStatus.QUEUED,
        nullable=False,
        index=True,
    )
    processing_error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    candidate: Mapped["User"] = relationship("User", back_populates="documents", lazy="selectin")
    extraction_runs: Mapped[list["ExtractionRun"]] = relationship(
        "ExtractionRun",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ExtractionRun.run_number",
        lazy="selectin",
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="primary_document",
        lazy="selectin",
    )
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(
        "EvidenceItem",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ExtractionRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an execution of resume parsing and structured claim extraction."""

    __tablename__ = "extraction_runs"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="fake", nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), default="default", nullable=False)
    status: Mapped[DocumentProcessingStatus] = mapped_column(
        Enum(DocumentProcessingStatus, native_enum=False, length=50),
        default=DocumentProcessingStatus.QUEUED,
        nullable=False,
        index=True,
    )
    raw_output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("document_id", "run_number", name="uq_extraction_runs_doc_run"),
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document", back_populates="extraction_runs", lazy="selectin"
    )
    candidate_skills: Mapped[list["CandidateSkill"]] = relationship(
        "CandidateSkill",
        back_populates="extraction_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(
        "EvidenceItem",
        back_populates="extraction_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        "Evaluation",
        back_populates="extraction_run",
        lazy="selectin",
    )


class CandidateSkill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Extracted skill or qualification from a candidate profile extraction run."""

    __tablename__ = "candidate_skills"

    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    extraction_run: Mapped["ExtractionRun"] = relationship(
        "ExtractionRun", back_populates="candidate_skills"
    )
    candidate: Mapped["User"] = relationship("User")


class EvidenceItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Atomic evidence item extracted from a document with source grounding."""

    __tablename__ = "evidence_items"

    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    source_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    grounding_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (Index("ix_evidence_items_doc_page", "document_id", "source_page"),)

    # Relationships
    extraction_run: Mapped["ExtractionRun"] = relationship(
        "ExtractionRun", back_populates="evidence_items"
    )
    document: Mapped["Document"] = relationship("Document", back_populates="evidence_items")
    criterion_evidence_links: Mapped[list["CriterionEvidence"]] = relationship(
        "CriterionEvidence",
        back_populates="evidence_item",
    )
