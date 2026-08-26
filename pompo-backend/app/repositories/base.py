"""Base repository for data access layer."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Abstract base repository providing session access and common queries.

    Subclasses set ``model`` to the concrete ORM class they manage. Soft
    deletion is opt-in and explicit: callers that only want active rows use
    ``get_active_by_id``; anything that legitimately needs deleted rows
    (audit views, admin recovery tools) can query the model directly through
    ``session`` instead.
    """

    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Return the underlying async session."""
        return self._session

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelType | None:
        """Fetch a row by primary key regardless of soft-delete state."""
        return await self._session.get(self.model, entity_id)

    async def get_active_by_id(self, entity_id: uuid.UUID) -> ModelType | None:
        """Fetch a row by primary key, excluding soft-deleted rows.

        Requires ``self.model`` to define ``deleted_at`` (i.e. use
        ``SoftDeleteMixin``); raises ``AttributeError`` otherwise, which is
        preferable to silently ignoring the soft-delete contract.
        """
        stmt = select(self.model).where(
            self.model.id == entity_id, self.model.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, entity: ModelType) -> ModelType:
        """Stage a new entity for insertion (does not commit)."""
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def soft_delete(self, entity: ModelType) -> ModelType:
        """Mark an entity as deleted without removing the row."""
        entity.deleted_at = datetime.now(timezone.utc)
        await self._session.flush()
        return entity
