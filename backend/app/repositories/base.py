import uuid
from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic async repository encapsulating SQLAlchemy persistence operations."""

    def __init__(self, model_cls: type[ModelT], session: AsyncSession):
        self.model_cls = model_cls
        self.session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelT | None:
        """Fetch entity by UUID primary key."""
        return await self.session.get(self.model_cls, entity_id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        """Fetch paginated entities."""
        query = select(self.model_cls).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, entity: ModelT) -> ModelT:
        """Persist a new entity instance."""
        self.session.add(entity)
        await self.session.flush()
        return entity
