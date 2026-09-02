"""Repository for User persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access for User rows."""

    model = User

    async def get_by_email(self, email: str) -> User | None:
        """Fetch an active (non-soft-deleted) user by email, or None."""
        stmt = (
            select(User)
            .options(selectinload(User.role))
            .where(User.email == email, User.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_id(self, entity_id) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.role))
            .where(User.id == entity_id, User.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
