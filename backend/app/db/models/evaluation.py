import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import EvidenceStatus, VerificationState

if TYPE_CHECKING:
    from app.db.models.application import Application
    from app.db.models.document import EvidenceItem, ExtractionRun
    from app.db.models.job import JobCriterion
    from app.db.models.review import CorrectionRequest, ReviewDecision, ReviewFlag


class Evaluation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Versioned evaluation of an application against job criteria.
    Preserves historical evaluation runs when criteria change or clarifications are submitted.
    """

    __tablename__ = "evaluations"

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    job_criteria_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    overall_status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, native_enum=False, length=50),
        default=EvidenceStatus.AMBIGUOUS,
        nullable=False,
        index=True,
    )
    summary_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_model_output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("application_id", "version", name="uq_evaluations_app_version"),
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", back_populates="evaluations", lazy="selectin"
    )
    extraction_run: Mapped["ExtractionRun"] = relationship(
        "ExtractionRun", back_populates="evaluations", lazy="selectin"
    )
    criterion_evidence_items: Mapped[list["CriterionEvidence"]] = relationship(
        "CriterionEvidence",
        back_populates="evaluation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CriterionEvidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Mapping between an application evaluation, a job criterion, and candidate evidence.
    Strictly separates initial AI extraction status from human/candidate verification state.
    """

    __tablename__ = "criterion_evidence"

    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_criterion_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("job_criteria.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evidence_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # AI Extraction Status (immutable record of model interpretation)
    ai_status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    ai_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verification State (human and clarification workflow tracking)
    verification_state: Mapped[VerificationState] = mapped_column(
        Enum(VerificationState, native_enum=False, length=50),
        default=VerificationState.UNVERIFIED,
        nullable=False,
        index=True,
    )

    # Provenance snapshot
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_criterion_evidence_eval_criterion", "evaluation_id", "job_criterion_id"),
    )

    # Relationships
    evaluation: Mapped["Evaluation"] = relationship(
        "Evaluation", back_populates="criterion_evidence_items", lazy="selectin"
    )
    criterion: Mapped["JobCriterion"] = relationship(
        "JobCriterion", back_populates="criterion_evidence_links", lazy="selectin"
    )
    evidence_item: Mapped["EvidenceItem | None"] = relationship(
        "EvidenceItem", back_populates="criterion_evidence_links", lazy="selectin"
    )
    review_flags: Mapped[list["ReviewFlag"]] = relationship(
        "ReviewFlag",
        back_populates="criterion_evidence",
        lazy="selectin",
    )
    correction_requests: Mapped[list["CorrectionRequest"]] = relationship(
        "CorrectionRequest",
        back_populates="criterion_evidence",
        lazy="selectin",
    )
    review_decisions: Mapped[list["ReviewDecision"]] = relationship(
        "ReviewDecision",
        back_populates="criterion_evidence",
        lazy="selectin",
    )
