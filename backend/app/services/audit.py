import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditEvent

GENESIS_PREVIOUS_HASH = "0" * 64
TAMPER_DISCLAIMER = (
    "A hash chain provides cryptographic tamper-evidence (detection of unilateral modifications, "
    "deletions, or reorderings), not tamper-prevention against root database rewrites. "
    "Historical consistency is mathematically verified from genesis."
)


def format_canonical_timestamp(ts: datetime | str) -> str:
    if isinstance(ts, str):
        clean = ts.replace("+00:00", "").replace("Z", "")
        try:
            parsed = datetime.fromisoformat(clean)
            return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return ts
    elif hasattr(ts, "strftime"):
        return ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(ts)


def _normalize_string(val: Any) -> str:
    if val is None:
        return ""
    if hasattr(val, "value"):
        return str(val.value)
    return str(val)


def _sanitize_dict(obj: Any) -> Any:
    if hasattr(obj, "value"):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _sanitize_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_dict(v) for v in obj]
    return obj


def canonicalize_audit_payload(
    sequence_number: int,
    timestamp: datetime,
    actor_id: str | None,
    actor_role: str | None,
    action: str,
    resource_type: str,
    resource_id: str,
    entity_version: int | None,
    prior_state: dict[str, Any] | None,
    new_state: dict[str, Any] | None,
    details: dict[str, Any] | None,
    previous_hash: str | None,
) -> bytes:
    """
    Produces deterministic, canonical JSON bytes for an audit event.
    Keys are strictly sorted and separators are minimized to eliminate formatting variance.
    """
    ts_str = format_canonical_timestamp(timestamp)

    payload = {
        "action": _normalize_string(action),
        "actor_id": _normalize_string(actor_id),
        "actor_role": _normalize_string(actor_role),
        "details": _sanitize_dict(details or {}),
        "entity_version": entity_version if entity_version is not None else 1,
        "new_state": _sanitize_dict(new_state or {}),
        "previous_hash": _normalize_string(previous_hash or GENESIS_PREVIOUS_HASH),
        "prior_state": _sanitize_dict(prior_state or {}),
        "resource_id": _normalize_string(resource_id),
        "resource_type": _normalize_string(resource_type),
        "sequence_number": int(sequence_number),
        "timestamp": ts_str,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def compute_audit_hash(canonical_bytes: bytes) -> str:
    """Computes SHA-256 hexadecimal digest from canonical payload bytes."""
    return hashlib.sha256(canonical_bytes).hexdigest()


class AuditVerificationResult(BaseModel):
    """Factual report on the integrity of the audit event hash chain."""

    model_config = ConfigDict(from_attributes=True)

    is_valid: bool
    total_events: int
    verified_events: int
    chain_head_hash: str | None = None
    discrepancy_type: str | None = None
    error: str | None = None
    broken_event_id: uuid.UUID | None = None
    broken_sequence_number: int | None = None
    tamper_evidence_disclaimer: str = TAMPER_DISCLAIMER


class AuditVerificationService:
    """
    Service verifying append-only audit event hash-chain continuity and cryptographic integrity.
    Identifies content tampering, broken hash links, deletions (sequence gaps), and reorderings.
    """

    async def verify_chain(
        self,
        session: AsyncSession,
    ) -> AuditVerificationResult:
        """
        Scans all audit events in sequential order and verifies:
        1. Monotonic sequence numbering without gaps.
        2. Correct previous_hash link to the preceding event's event_hash.
        3. Deterministic canonical hash recalculation matches event_hash.
        """
        query = select(AuditEvent).order_by(AuditEvent.sequence_number.asc())
        result = await session.execute(query)
        events = list(result.scalars().all())

        if not events:
            return AuditVerificationResult(
                is_valid=True,
                total_events=0,
                verified_events=0,
                chain_head_hash=None,
            )

        expected_seq = 1
        expected_prev_hash = GENESIS_PREVIOUS_HASH

        for idx, event in enumerate(events):
            # Check 1: Sequence number continuity
            if event.sequence_number != expected_seq:
                return AuditVerificationResult(
                    is_valid=False,
                    total_events=len(events),
                    verified_events=idx,
                    chain_head_hash=expected_prev_hash if idx > 0 else None,
                    discrepancy_type="SEQUENCE_GAP"
                    if event.sequence_number > expected_seq
                    else "REORDERED",
                    error=(
                        f"Audit sequence discontinuity detected at position {idx + 1}: "
                        f"expected sequence {expected_seq}, encountered {event.sequence_number}."
                    ),
                    broken_event_id=event.id,
                    broken_sequence_number=event.sequence_number,
                )

            # Check 2: Hash chain pointer integrity
            actual_prev = event.previous_hash or GENESIS_PREVIOUS_HASH
            if actual_prev != expected_prev_hash:
                return AuditVerificationResult(
                    is_valid=False,
                    total_events=len(events),
                    verified_events=idx,
                    chain_head_hash=expected_prev_hash if idx > 0 else None,
                    discrepancy_type="BROKEN_LINK",
                    error=(
                        f"Cryptographic hash chain broken at sequence {event.sequence_number}: "
                        f"previous_hash '{actual_prev}' does not match expected '{expected_prev_hash}'."
                    ),
                    broken_event_id=event.id,
                    broken_sequence_number=event.sequence_number,
                )

            # Check 3: Canonical content recalculation
            canonical_bytes = canonicalize_audit_payload(
                sequence_number=event.sequence_number,
                timestamp=event.timestamp,
                actor_id=event.actor_id,
                actor_role=event.actor_role,
                action=event.action,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                entity_version=event.entity_version,
                prior_state=event.prior_state,
                new_state=event.new_state,
                details=event.details,
                previous_hash=event.previous_hash,
            )
            recalculated_hash = compute_audit_hash(canonical_bytes)

            if event.event_hash != recalculated_hash:
                return AuditVerificationResult(
                    is_valid=False,
                    total_events=len(events),
                    verified_events=idx,
                    chain_head_hash=expected_prev_hash if idx > 0 else None,
                    discrepancy_type="CONTENT_TAMPERED",
                    error=(
                        f"Audit event content tampered at sequence {event.sequence_number}: "
                        f"stored hash '{event.event_hash}' differs from computed '{recalculated_hash}'."
                    ),
                    broken_event_id=event.id,
                    broken_sequence_number=event.sequence_number,
                )

            # Advance expected pointer for next iteration
            expected_prev_hash = event.event_hash
            expected_seq += 1

        return AuditVerificationResult(
            is_valid=True,
            total_events=len(events),
            verified_events=len(events),
            chain_head_hash=expected_prev_hash,
            error=None,
        )
