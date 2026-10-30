import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditEventDetailResponse(BaseModel):
    """Detailed representation of an immutable, cryptographically chained audit event."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence_number: int
    timestamp: datetime
    actor_id: str | None = None
    actor_role: str | None = None
    action: str
    resource_type: str
    resource_id: str
    entity_version: int | None = None
    prior_state: dict[str, Any] | None = None
    new_state: dict[str, Any] | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    previous_hash: str | None = None
    event_hash: str
    is_verified: bool = True


class AuditVerificationReportResponse(BaseModel):
    """Integrity report verifying audit hash chain continuity and tamper-evidence."""

    model_config = ConfigDict(from_attributes=True)

    is_valid: bool
    total_events: int
    verified_events: int
    chain_head_hash: str | None = None
    discrepancy_type: str | None = None
    error: str | None = None
    broken_event_id: uuid.UUID | None = None
    broken_sequence_number: int | None = None
    tamper_evidence_disclaimer: str
