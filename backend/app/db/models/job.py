import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import JobStatus

if TYPE_CHECKING:
    from app.db.models.application import Application
    from app.db.models.evaluation import CriterionEvidence
    from app.db.models.user import User


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Employer job requisition with criteria versions and applications."""

    __tablename__ = "jobs"

    employer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    external_requisition_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, length=50),
        default=JobStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="created_jobs", lazy="selectin")
    criteria: Mapped[list["JobCriterion"]] = relationship(
        "JobCriterion",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobCriterion.version.desc()",
        lazy="selectin",
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="job",
        lazy="selectin",
    )


class JobCriterion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Explicit, versioned evaluation requirement or skill benchmark for a job."""

    __tablename__ = "job_criteria"

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), default="requirement", nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("job_id", "name", "version", name="uq_job_criteria_job_name_version"),
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="criteria")
    criterion_evidence_links: Mapped[list["CriterionEvidence"]] = relationship(
        "CriterionEvidence",
        back_populates="criterion",
    )
