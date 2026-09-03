"""Repository for RefreshSession persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.models.auth import AccountSecurityToken, RefreshSession
from app.repositories.base import BaseRepository


class RefreshSessionRepository(BaseRepository[RefreshSession]):
    """Data access for refresh-token sessions."""

    model = RefreshSession

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        """Revoke every still-active session in a rotation family.

        Called when a replay is detected: since a previously-rotated token
        was reused, we can't tell whether the *legitimate* holder or an
        attacker sent the still-valid latest token in the chain, so the
        safe response is to kill the whole family and force a fresh login.
        """
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.family_id == family_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke every still-active refresh session for a user."""
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)


class AccountSecurityTokenRepository(BaseRepository[AccountSecurityToken]):
    """Data access for email verification and password reset tokens."""

    model = AccountSecurityToken

    async def get_by_hash_and_type(
        self, token_hash: str, token_type: str
    ) -> AccountSecurityToken | None:
        stmt = select(AccountSecurityToken).where(
            AccountSecurityToken.token_hash == token_hash,
            AccountSecurityToken.token_type == token_type,
        )
        return await self._session.scalar(stmt)

    async def get_latest_active_token(
        self, user_id: uuid.UUID, token_type: str
    ) -> AccountSecurityToken | None:
        stmt = (
            select(AccountSecurityToken)
            .where(
                AccountSecurityToken.user_id == user_id,
                AccountSecurityToken.token_type == token_type,
                AccountSecurityToken.used_at.is_(None),
            )
            .order_by(AccountSecurityToken.created_at.desc())
            .limit(1)
        )
        return await self._session.scalar(stmt)

    async def invalidate_all_for_user(
        self, user_id: uuid.UUID, token_type: str
    ) -> None:
        stmt = (
            update(AccountSecurityToken)
            .where(
                AccountSecurityToken.user_id == user_id,
                AccountSecurityToken.token_type == token_type,
                AccountSecurityToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)
