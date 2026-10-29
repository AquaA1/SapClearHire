import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit import AuditEventRepository


@pytest.mark.asyncio
async def test_audit_event_repository_persistence(test_session: AsyncSession):
    repo = AuditEventRepository(test_session)

    res_id = str(uuid.uuid4())
    event = await repo.log_event(
        action="DOCUMENT_UPLOADED",
        resource_type="document",
        resource_id=res_id,
        actor_id="user_test_456",
        actor_role="candidate",
        details={"filename": "resume.pdf", "sha256": "fakehash123"},
        ip_address="127.0.0.1",
    )
    await test_session.commit()

    assert event.id is not None
    assert event.action == "DOCUMENT_UPLOADED"
    assert event.resource_id == res_id

    # Retrieve logged event
    events = await repo.get_by_resource("document", res_id)
    assert len(events) == 1
    assert events[0].actor_id == "user_test_456"
    assert events[0].details["filename"] == "resume.pdf"


@pytest.mark.asyncio
async def test_session_rollback_on_failure(test_session: AsyncSession):
    repo = AuditEventRepository(test_session)
    res_id = str(uuid.uuid4())

    await repo.log_event(
        action="TEST_ROLLBACK",
        resource_type="test",
        resource_id=res_id,
    )
    # Explicitly rollback instead of committing
    await test_session.rollback()

    events = await repo.get_by_resource("test", res_id)
    assert len(events) == 0
