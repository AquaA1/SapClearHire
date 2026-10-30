import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ClearHireError
from app.db.models.audit import AuditEvent
from app.repositories.audit import AuditEventRepository
from app.services.audit import AuditVerificationService


@pytest.mark.asyncio
async def test_audit_event_immutability_blocks_updates_and_deletes(
    test_session: AsyncSession,
) -> None:
    """
    Test that the application rejects updates and deletions of AuditEvent instances
    via SQLAlchemy lifecycle hooks.
    """
    repo = AuditEventRepository(test_session)
    event = await repo.log_event(
        action="TEST_ACTION",
        resource_type="test_resource",
        resource_id="res_1",
        actor_id="user_1",
        actor_role="admin",
        details={"key": "val1"},
    )
    await test_session.commit()
    event_id = event.id

    # 1. Attempting an update in the application must be blocked
    event.action = "MODIFIED_ACTION"
    with pytest.raises(ClearHireError) as exc_update:
        await test_session.flush()
    assert "immutable" in str(exc_update.value).lower()
    await test_session.rollback()

    # Re-fetch instance after rollback
    res = await test_session.execute(select(AuditEvent).where(AuditEvent.id == event_id))
    persisted = res.scalar_one()
    assert persisted.action == "TEST_ACTION"

    # 2. Attempting a deletion in the application must be blocked
    with pytest.raises(ClearHireError) as exc_delete:
        await test_session.delete(persisted)
        await test_session.flush()
    assert "append-only" in str(exc_delete.value).lower()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_hash_chain_valid_sequence(test_session: AsyncSession) -> None:
    """Test that sequential audit events form a cryptographically continuous and valid chain."""
    repo = AuditEventRepository(test_session)
    e1 = await repo.log_event(
        action="ACTION_1", resource_type="item", resource_id="1", actor_id="a1"
    )
    e2 = await repo.log_event(
        action="ACTION_2", resource_type="item", resource_id="2", actor_id="a2"
    )
    e3 = await repo.log_event(
        action="ACTION_3", resource_type="item", resource_id="3", actor_id="a3"
    )
    await test_session.commit()

    assert e1.sequence_number == 1
    assert e2.sequence_number == 2
    assert e3.sequence_number == 3
    assert e2.previous_hash == e1.event_hash
    assert e3.previous_hash == e2.event_hash

    verifier = AuditVerificationService()
    result = await verifier.verify_chain(test_session)
    assert result.is_valid is True
    assert result.total_events == 3
    assert result.verified_events == 3
    assert result.error is None


@pytest.mark.asyncio
async def test_hash_chain_detects_content_tampering(test_session: AsyncSession) -> None:
    """
    Test that directly modifying audit event content in the database
    is identified by the verification service as CONTENT_TAMPERED.
    """
    repo = AuditEventRepository(test_session)
    await repo.log_event(action="LOGIN", resource_type="user", resource_id="u1", actor_id="u1")
    e2 = await repo.log_event(action="UPLOAD", resource_type="doc", resource_id="d1", actor_id="u1")
    await test_session.commit()

    # Tamper with event 2's action directly in the DB using raw SQL (simulating database breach)
    await test_session.execute(
        text("UPDATE audit_events SET action = 'TAMPERED_ACTION' WHERE sequence_number = 2"),
    )
    await test_session.commit()
    test_session.expire_all()

    verifier = AuditVerificationService()
    result = await verifier.verify_chain(test_session)
    assert result.is_valid is False
    assert result.discrepancy_type == "CONTENT_TAMPERED"
    assert result.broken_sequence_number == 2
    assert result.broken_event_id == e2.id
    assert "tampered" in str(result.error).lower()


@pytest.mark.asyncio
async def test_hash_chain_detects_deletion_and_sequence_gap(test_session: AsyncSession) -> None:
    """
    Test that deleting an event from history creates a sequence gap
    and broken link detected by the verification service.
    """
    repo = AuditEventRepository(test_session)
    await repo.log_event(action="A1", resource_type="res", resource_id="1")
    await repo.log_event(action="A2", resource_type="res", resource_id="2")
    await repo.log_event(action="A3", resource_type="res", resource_id="3")
    await test_session.commit()

    # Delete event 2 via raw SQL
    await test_session.execute(
        text("DELETE FROM audit_events WHERE sequence_number = 2"),
    )
    await test_session.commit()
    test_session.expire_all()

    verifier = AuditVerificationService()
    result = await verifier.verify_chain(test_session)
    assert result.is_valid is False
    assert result.discrepancy_type in ("SEQUENCE_GAP", "BROKEN_LINK")
    assert result.broken_sequence_number in (2, 3)


@pytest.mark.asyncio
async def test_hash_chain_detects_reordered_events(test_session: AsyncSession) -> None:
    """
    Test that reordering events in the sequence is detected.
    """
    repo = AuditEventRepository(test_session)
    await repo.log_event(action="A1", resource_type="res", resource_id="1")
    await repo.log_event(action="A2", resource_type="res", resource_id="2")
    await test_session.commit()

    # Swap sequence numbers of e1 and e2 via raw SQL
    await test_session.execute(
        text("UPDATE audit_events SET sequence_number = 999 WHERE sequence_number = 1"),
    )
    await test_session.execute(
        text("UPDATE audit_events SET sequence_number = 1 WHERE sequence_number = 2"),
    )
    await test_session.execute(
        text("UPDATE audit_events SET sequence_number = 2 WHERE sequence_number = 999"),
    )
    await test_session.commit()
    test_session.expire_all()

    verifier = AuditVerificationService()
    result = await verifier.verify_chain(test_session)
    assert result.is_valid is False
    assert result.discrepancy_type in ("BROKEN_LINK", "CONTENT_TAMPERED")
