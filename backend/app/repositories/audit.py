from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditEvent
from app.repositories.base import BaseRepository


class AuditEventRepository(BaseRepository[AuditEvent]):
    """Repository handling append-only audit event persistence."""

    def __init__(self, session: AsyncSession):
        super().__init__(AuditEvent, session)

    async def log_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        actor_id: str | None = None,
        actor_role: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditEvent:
        """Appends an immutable audit event."""
        event = AuditEvent(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            actor_role=actor_role,
            details=details or {},
            ip_address=ip_address,
        )
        return await self.create(event)

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
            .order_by(AuditEvent.timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
