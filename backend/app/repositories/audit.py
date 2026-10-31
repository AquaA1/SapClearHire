import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditEvent
from app.repositories.base import BaseRepository
from app.services.audit import (
    GENESIS_PREVIOUS_HASH,
    canonicalize_audit_payload,
    compute_audit_hash,
)


class AuditEventRepository(BaseRepository[AuditEvent]):
    """Repository handling append-only, cryptographically chained audit event persistence."""

    def __init__(self, session: AsyncSession):
        super().__init__(AuditEvent, session)

    async def log_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        actor_id: str | None = None,
        actor_role: str | None = None,
        entity_version: int | None = None,
        prior_state: dict[str, Any] | None = None,
        new_state: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditEvent:
        """
        Appends an immutable audit event chained cryptographically to the preceding event.
        Must be executed in the same database transaction as the business operation.
        """
        # Determine latest event in sequence
        latest_query = select(AuditEvent).order_by(AuditEvent.sequence_number.desc()).limit(1)
        latest_res = await self.session.execute(latest_query)
        last_event = latest_res.scalar_one_or_none()

        if last_event is None:
            sequence_number = 1
            previous_hash = GENESIS_PREVIOUS_HASH
        else:
            sequence_number = last_event.sequence_number + 1
            previous_hash = last_event.event_hash

        now = datetime.now(UTC)

        canonical_bytes = canonicalize_audit_payload(
            sequence_number=sequence_number,
            timestamp=now,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            entity_version=entity_version,
            prior_state=prior_state,
            new_state=new_state,
            details=details,
            previous_hash=previous_hash,
        )
        event_hash = compute_audit_hash(canonical_bytes)

        actor_role_str = (
            str(actor_role.value)
            if hasattr(actor_role, "value")
            else (str(actor_role) if actor_role is not None else None)
        )

        event = AuditEvent(
            sequence_number=sequence_number,
            timestamp=now,
            actor_id=str(actor_id) if actor_id is not None else None,
            actor_role=actor_role_str,
            action=str(action),
            resource_type=str(resource_type),
            resource_id=str(resource_id),
            entity_version=entity_version,
            prior_state=prior_state,
            new_state=new_state,
            details=details or {},
            ip_address=ip_address,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_by_id(self, event_id: uuid.UUID) -> AuditEvent | None:
        """Retrieves an audit event by its unique ID."""
        query = select(AuditEvent).where(AuditEvent.id == event_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_resource(
        self, resource_type: str, resource_id: str, limit: int = 50
    ) -> Sequence[AuditEvent]:
        """Returns chronological audit events for a specific resource."""
        query = (
            select(AuditEvent)
            .where(
                AuditEvent.resource_type == resource_type,
                AuditEvent.resource_id == resource_id,
            )
            .order_by(AuditEvent.sequence_number.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def query_events(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        actor_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AuditEvent]:
        """Returns paginated, filtered audit events ordered by sequence number descending."""
        query = select(AuditEvent)
        if resource_type:
            query = query.where(AuditEvent.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditEvent.resource_id == str(resource_id))
        if actor_id:
            query = query.where(AuditEvent.actor_id == str(actor_id))
        query = query.order_by(AuditEvent.sequence_number.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()
