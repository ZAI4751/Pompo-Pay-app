"""Lightweight customer support requests. Not a ticketing platform."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import AuditLog, User
from app.models.customer import SupportRequest
from app.models.enums import SupportCategory, SupportRequestStatus
from app.repositories.customer import PaymentRequestRepository, SupportRequestRepository
from app.repositories.payment import TransactionRepository

logger = get_logger(__name__)


class SupportError(Exception):
    pass


class SupportNotFoundError(SupportError):
    pass


class SupportForbiddenError(SupportError):
    pass


class SupportInvalidError(SupportError):
    pass


class SupportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._support = SupportRequestRepository(session)
        self._requests = PaymentRequestRepository(session)
        self._transactions = TransactionRepository(session)

    async def create(self, actor: User, values: dict[str, Any]) -> SupportRequest:
        try:
            category = SupportCategory(values["category"])
        except ValueError as exc:
            raise SupportInvalidError("Unknown support category") from exc
        payment_reference = values.get("payment_reference")
        if payment_reference:
            transaction = await self._transactions.get_active_by_reference(payment_reference)
            if transaction is None:
                raise SupportInvalidError("Payment reference was not found")
            if transaction.cashier_id != actor.id and actor.merchant_id != transaction.merchant_id:
                role = actor.role
                if role is None or role.code != "platform_admin":
                    raise SupportForbiddenError("Payment reference is outside actor scope")
        payment_request_row = None
        public_request_id = values.get("payment_request_id")
        if public_request_id:
            payment_request_row = await self._requests.get_by_public_id(str(public_request_id))
            if payment_request_row is None:
                raise SupportInvalidError("Payment request was not found")
            if (
                payment_request_row.requester_id != actor.id
                and payment_request_row.payer_user_id != actor.id
            ):
                role = actor.role
                if role is None or role.code != "platform_admin":
                    raise SupportForbiddenError("Payment request is outside actor scope")
        row = SupportRequest(
            public_identifier=f"SUP-{uuid.uuid4().hex[:12].upper()}",
            user_id=actor.id,
            category=category,
            subject=values["subject"].strip(),
            message=values["message"].strip(),
            payment_reference=payment_reference,
            payment_request_id=payment_request_row.id if payment_request_row is not None else None,
            status=SupportRequestStatus.OPEN,
        )
        self._session.add(row)
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=actor.id,
                merchant_id=actor.merchant_id,
                action="support_request_created",
                entity_type="support_request",
                entity_id=str(row.public_identifier),
                before_state=None,
                after_state={
                    "category": category.value,
                    "payment_reference": payment_reference,
                },
            )
        )
        await self._session.commit()
        logger.info(
            "support_request_created",
            support_id=row.public_identifier,
            user_id=str(actor.id),
            payment_reference=payment_reference,
        )
        return row

    async def list_visible(
        self, actor: User, *, limit: int = 50, offset: int = 0
    ) -> list[SupportRequest]:
        role = actor.role
        if role is not None and role.code == "platform_admin":
            return await self._support.list_all(limit=min(limit, 100), offset=max(offset, 0))
        return await self._support.list_for_user(
            actor.id, limit=min(limit, 100), offset=max(offset, 0)
        )

    async def get_visible(self, actor: User, public_identifier: str) -> SupportRequest:
        row = await self._support.get_by_public_id(public_identifier)
        if row is None:
            raise SupportNotFoundError("Support request not found")
        role = actor.role
        if row.user_id != actor.id and (role is None or role.code != "platform_admin"):
            raise SupportForbiddenError("Support request is outside actor scope")
        return row
