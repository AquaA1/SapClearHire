from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.core.exceptions import ClearHireError
from app.db.base import Base, UUIDPrimaryKeyMixin


class AuditEvent(Base, UUIDPrimaryKeyMixin):
    """
    Immutable, append-only record tracking security-relevant and business-relevant operations.
    Cryptographically chained via previous_hash and deterministic event_hash to ensure tamper-evidence.
    """

    __tablename__ = "audit_events"

    sequence_number: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, nullable=False, default=1
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    actor_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prior_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict, nullable=True)
    new_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    __table_args__ = (
        Index("ix_audit_events_resource", "resource_type", "resource_id"),
        Index("ix_audit_events_actor_time", "actor_id", "timestamp"),
        Index("ix_audit_events_seq", "sequence_number"),
    )


@event.listens_for(AuditEvent, "before_update")
def prevent_audit_event_update(mapper: Any, connection: Any, target: AuditEvent) -> None:
    raise ClearHireError("Audit events are immutable and cannot be updated.")


@event.listens_for(AuditEvent, "before_delete")
def prevent_audit_event_delete(mapper: Any, connection: Any, target: AuditEvent) -> None:
    raise ClearHireError("Audit events are append-only and cannot be deleted.")
