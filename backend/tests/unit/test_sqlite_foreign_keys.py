import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.enums import DocumentProcessingStatus


@pytest.mark.asyncio
async def test_sqlite_foreign_key_enforcement(test_session: AsyncSession):
    """Verify that foreign key constraints are strictly enforced in SQLite."""
    non_existent_user_id = uuid.uuid4()

    orphan_doc = Document(
        candidate_id=non_existent_user_id,
        file_name="orphan.pdf",
        file_path="/tmp/orphan.pdf",
        file_hash="dummyhash",
        file_size_bytes=100,
        processing_status=DocumentProcessingStatus.QUEUED,
    )
    test_session.add(orphan_doc)
    with pytest.raises(IntegrityError):
        await test_session.commit()
