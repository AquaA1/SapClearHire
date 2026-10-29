from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import UserRole
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.application import Application
    from app.db.models.document import Document
    from app.db.models.job import Job
    from app.db.models.review import CorrectionRequest, ReviewDecision, ReviewFlag


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """System user representing candidates, reviewers, employer admins, or auditors."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=50),
        nullable=False,
        default=UserRole.CANDIDATE,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    employer_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="candidate",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="candidate",
        lazy="selectin",
    )
    created_jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="creator",
        lazy="selectin",
    )
    review_decisions: Mapped[list["ReviewDecision"]] = relationship(
        "ReviewDecision",
        back_populates="reviewer",
        lazy="selectin",
    )
    assigned_flags: Mapped[list["ReviewFlag"]] = relationship(
        "ReviewFlag",
        back_populates="assigned_to",
        lazy="selectin",
    )
    correction_requests: Mapped[list["CorrectionRequest"]] = relationship(
        "CorrectionRequest",
        foreign_keys="CorrectionRequest.candidate_id",
        back_populates="candidate",
        lazy="selectin",
    )
    reviewed_corrections: Mapped[list["CorrectionRequest"]] = relationship(
        "CorrectionRequest",
        foreign_keys="CorrectionRequest.reviewed_by_user_id",
        back_populates="reviewed_by",
        lazy="selectin",
    )
