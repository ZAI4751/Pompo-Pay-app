"""Repository for User persistence."""

from __future__ import annotations

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access for User rows."""

    model = User

    async def get_by_email(self, email: str) -> User | None:
        """Fetch an active (non-soft-deleted) user by email, or None."""
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
