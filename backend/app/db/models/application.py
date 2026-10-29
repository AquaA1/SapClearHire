import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import ApplicationStatus

if TYPE_CHECKING:
    from app.db.models.document import Document
    from app.db.models.evaluation import Evaluation
    from app.db.models.job import Job
    from app.db.models.review import CorrectionRequest, ReviewDecision, ReviewFlag
    from app.db.models.user import User


class Application(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Candidate job application linking a resume document to a job requisition."""

    __tablename__ = "applications"

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    primary_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False, length=50),
        default=ApplicationStatus.SUBMITTED,
        nullable=False,
        index=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_applications_job_candidate"),
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="applications", lazy="selectin")
    candidate: Mapped["User"] = relationship("User", back_populates="applications", lazy="selectin")
    primary_document: Mapped["Document"] = relationship(
        "Document", back_populates="applications", lazy="selectin"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        "Evaluation",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="Evaluation.version.desc()",
        lazy="selectin",
    )
    review_flags: Mapped[list["ReviewFlag"]] = relationship(
        "ReviewFlag",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    correction_requests: Mapped[list["CorrectionRequest"]] = relationship(
        "CorrectionRequest",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    review_decisions: Mapped[list["ReviewDecision"]] = relationship(
        "ReviewDecision",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
