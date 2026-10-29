import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import (
    CorrectionRequestStatus,
    ReviewDecisionType,
    ReviewFlagStatus,
)

if TYPE_CHECKING:
    from app.db.models.application import Application
    from app.db.models.document import Document
    from app.db.models.evaluation import CriterionEvidence
    from app.db.models.user import User


class ReviewFlag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Flag raising ambiguous or disputed evidence for reviewer attention."""

    __tablename__ = "review_flags"

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("criterion_evidence.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    flag_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ReviewFlagStatus] = mapped_column(
        Enum(ReviewFlagStatus, native_enum=False, length=50),
        default=ReviewFlagStatus.PENDING,
        nullable=False,
        index=True,
    )
    priority: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", back_populates="review_flags", lazy="selectin"
    )
    criterion_evidence: Mapped["CriterionEvidence | None"] = relationship(
        "CriterionEvidence", back_populates="review_flags", lazy="selectin"
    )
    assigned_to: Mapped["User | None"] = relationship(
        "User", back_populates="assigned_flags", lazy="selectin"
    )


class CorrectionRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Candidate-submitted clarification or additional evidence contesting an evaluation."""

    __tablename__ = "correction_requests"

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    criterion_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("criterion_evidence.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    candidate_statement: Mapped[str] = mapped_column(Text, nullable=False)
    additional_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[CorrectionRequestStatus] = mapped_column(
        Enum(CorrectionRequestStatus, native_enum=False, length=50),
        default=CorrectionRequestStatus.SUBMITTED,
        nullable=False,
        index=True,
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", back_populates="correction_requests", lazy="selectin"
    )
    candidate: Mapped["User"] = relationship(
        "User",
        foreign_keys=[candidate_id],
        back_populates="correction_requests",
        lazy="selectin",
    )
    criterion_evidence: Mapped["CriterionEvidence | None"] = relationship(
        "CriterionEvidence", back_populates="correction_requests", lazy="selectin"
    )
    additional_document: Mapped["Document | None"] = relationship("Document", lazy="selectin")
    reviewed_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[reviewed_by_user_id],
        back_populates="reviewed_corrections",
        lazy="selectin",
    )


class ReviewDecision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Authorized reviewer verdict on evidence with mandatory explanatory rationale.
    Preserves audit history without overwriting prior reviewer determinations.
    """

    __tablename__ = "review_decisions"

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("criterion_evidence.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    decision: Mapped[ReviewDecisionType] = mapped_column(
        Enum(ReviewDecisionType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    mandatory_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    previous_verification_state: Mapped[str] = mapped_column(String(64), nullable=False)
    new_verification_state: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    __table_args__ = (
        CheckConstraint(
            "length(trim(mandatory_rationale)) > 0",
            name="ck_review_decisions_rationale_not_empty",
        ),
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", back_populates="review_decisions", lazy="selectin"
    )
    criterion_evidence: Mapped["CriterionEvidence | None"] = relationship(
        "CriterionEvidence", back_populates="review_decisions", lazy="selectin"
    )
    reviewer: Mapped["User"] = relationship(
        "User", back_populates="review_decisions", lazy="selectin"
    )
