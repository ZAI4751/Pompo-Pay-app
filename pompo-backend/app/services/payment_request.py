"""Payment requests and bill splits — instructions for merchant payments, not wallets."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import AuditLog, Branch, Merchant, Till, User
from app.models.customer import BillSplit, PaymentRequest
from app.models.enums import (
    BillSplitStatus,
    NotificationType,
    PaymentRequestStatus,
    TransactionStatus,
)
from app.models.payment import Transaction
from app.repositories.customer import BillSplitRepository, PaymentRequestRepository
from app.repositories.payment import TransactionRepository
from app.services.notification import NotificationService
from app.services.payment import (
    PaymentError,
    PaymentForbiddenError,
    PaymentInvalidError,
    PaymentNotFoundError,
    PaymentService,
)

logger = get_logger(__name__)


class PaymentRequestError(Exception):
    pass


class PaymentRequestNotFoundError(PaymentRequestError):
    pass


class PaymentRequestForbiddenError(PaymentRequestError):
    pass


class PaymentRequestInvalidError(PaymentRequestError):
    pass


class PaymentRequestConflictError(PaymentRequestError):
    pass


def _public_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


class PaymentRequestService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._requests = PaymentRequestRepository(session)
        self._splits = BillSplitRepository(session)
        self._transactions = TransactionRepository(session)
        self._payments = PaymentService(session)
        self._notifications = NotificationService(session)

    async def create(self, actor: User, values: dict[str, Any]) -> PaymentRequest:
        existing = await self._requests.get_by_idempotency(actor.id, values["idempotency_key"])
        if existing is not None:
            return existing
        merchant_id, branch_id, till_id = await self._resolve_destination(actor, values)
        expires_at = self._expiry(values.get("expires_in_seconds", 86400))
        public_id = _public_id("REQ")
        request = PaymentRequest(
            public_identifier=public_id,
            requester_id=actor.id,
            merchant_id=merchant_id,
            branch_id=branch_id,
            till_id=till_id,
            amount=values["amount"],
            currency=values.get("currency", "MWK"),
            description=values.get("description"),
            status=PaymentRequestStatus.PENDING,
            expires_at=expires_at,
            idempotency_key=values["idempotency_key"],
            share_code=f"POMPO:1:req:{public_id}",
        )
        self._session.add(request)
        await self._audit(
            actor,
            "payment_request_created",
            request,
            {"amount": str(values["amount"]), "merchant_id": str(merchant_id)},
        )
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            existing = await self._requests.get_by_idempotency(actor.id, values["idempotency_key"])
            if existing is not None:
                return existing
            raise
        loaded = await self._requests.get_by_public_id(public_id)
        assert loaded is not None
        logger.info(
            "payment_request_created",
            request_id=str(loaded.id),
            public_identifier=public_id,
            user_id=str(actor.id),
        )
        return loaded

    async def create_split(self, actor: User, values: dict[str, Any]) -> BillSplit:
        existing = await self._splits.get_by_idempotency(actor.id, values["idempotency_key"])
        if existing is not None:
            return existing
        participants = values["participants"]
        parts = [Decimal(str(item["amount"])) for item in participants]
        total = Decimal(str(values["total_amount"]))
        if sum(parts) != total:
            raise PaymentRequestInvalidError("Participant amounts must equal the total")
        merchant_id, branch_id, till_id = await self._resolve_destination(actor, values)
        expires_at = self._expiry(values.get("expires_in_seconds", 86400))
        split = BillSplit(
            public_identifier=_public_id("SPL"),
            creator_id=actor.id,
            merchant_id=merchant_id,
            branch_id=branch_id,
            till_id=till_id,
            total_amount=total,
            currency=values.get("currency", "MWK"),
            description=values.get("description"),
            status=BillSplitStatus.PENDING,
            expires_at=expires_at,
            idempotency_key=values["idempotency_key"],
        )
        self._session.add(split)
        await self._session.flush()
        for index, item in enumerate(participants):
            public_id = _public_id("REQ")
            request = PaymentRequest(
                public_identifier=public_id,
                requester_id=actor.id,
                merchant_id=merchant_id,
                branch_id=branch_id,
                till_id=till_id,
                bill_split_id=split.id,
                amount=item["amount"],
                currency=values.get("currency", "MWK"),
                description=item.get("label") or values.get("description"),
                status=PaymentRequestStatus.PENDING,
                expires_at=expires_at,
                idempotency_key=f"{values['idempotency_key']}:p{index}",
                share_code=f"POMPO:1:req:{public_id}",
            )
            self._session.add(request)
        await self._audit(
            actor,
            "payment_request_created",
            split,
            {"split": True, "participants": len(participants), "total": str(total)},
            entity_type="bill_split",
        )
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            existing = await self._splits.get_by_idempotency(actor.id, values["idempotency_key"])
            if existing is not None:
                return existing
            raise
        loaded = await self._splits.get_by_public_id(split.public_identifier)
        assert loaded is not None
        logger.info(
            "bill_split_created",
            split_id=str(loaded.id),
            public_identifier=loaded.public_identifier,
            user_id=str(actor.id),
        )
        return loaded

    async def list_mine(
        self, actor: User, *, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[PaymentRequest]:
        parsed = None
        if status:
            try:
                parsed = PaymentRequestStatus(status)
            except ValueError as exc:
                raise PaymentRequestInvalidError("Unknown payment request status") from exc
        rows = await self._requests.list_for_user(
            actor.id, status=parsed, limit=min(limit, 100), offset=max(offset, 0)
        )
        changed = False
        for row in rows:
            if await self._expire_if_needed(row):
                changed = True
        if changed:
            await self._session.commit()
        return rows

    async def inspect_public(self, public_identifier: str) -> PaymentRequest:
        request = await self._requests.get_by_public_id(public_identifier)
        if request is None:
            raise PaymentRequestNotFoundError("Payment request not found")
        if await self._expire_if_needed(request):
            await self._session.commit()
        return request

    async def get_owned(self, actor: User, public_identifier: str) -> PaymentRequest:
        request = await self.inspect_public(public_identifier)
        if request.requester_id != actor.id and request.payer_user_id != actor.id:
            raise PaymentRequestForbiddenError("Payment request is outside actor scope")
        return request

    async def cancel(self, actor: User, public_identifier: str) -> PaymentRequest:
        request = await self.inspect_public(public_identifier)
        if request.requester_id != actor.id:
            raise PaymentRequestForbiddenError("Only the requester can cancel this request")
        if request.status is PaymentRequestStatus.PAID:
            raise PaymentRequestInvalidError("Paid requests cannot be cancelled")
        if request.status is PaymentRequestStatus.CANCELLED:
            return request
        request.status = PaymentRequestStatus.CANCELLED
        request.cancelled_at = datetime.now(UTC)
        await self._audit(
            actor,
            "payment_request_cancelled",
            request,
            {"status": PaymentRequestStatus.CANCELLED.value},
        )
        await self._refresh_split(request)
        await self._session.commit()
        logger.info(
            "payment_request_cancelled",
            request_id=str(request.id),
            public_identifier=public_identifier,
            user_id=str(actor.id),
        )
        return request

    async def pay(self, actor: User, public_identifier: str, values: dict[str, Any]) -> Transaction:
        request = await self._requests.get_by_public_id(public_identifier, for_update=True)
        if request is None:
            raise PaymentRequestNotFoundError("Payment request not found")
        if await self._expire_if_needed(request):
            await self._session.flush()
        if request.status is PaymentRequestStatus.PAID:
            raise PaymentRequestInvalidError("Payment request is already paid")
        if request.status is PaymentRequestStatus.CANCELLED:
            raise PaymentRequestInvalidError("Payment request was cancelled")
        if request.status is PaymentRequestStatus.EXPIRED:
            raise PaymentRequestInvalidError("Payment request has expired")
        if request.last_payment_id is not None:
            existing = await self._transactions.get_by_id(request.last_payment_id)
            if existing is not None:
                if existing.status is TransactionStatus.SUCCESS:
                    await self.fulfill_if_matching(existing)
                    return existing
                if existing.status not in {
                    TransactionStatus.FAILED,
                    TransactionStatus.TIMEOUT,
                    TransactionStatus.CANCELLED,
                    TransactionStatus.REFUNDED,
                }:
                    return existing
        payment_values = {
            "merchant_id": request.merchant_id,
            "branch_id": request.branch_id,
            "till_id": request.till_id,
            "amount": request.amount,
            "currency": request.currency,
            "payment_method": values.get("payment_method", "mobile_money"),
            "provider_code": values.get("provider_code"),
            "customer_phone": values.get("customer_phone"),
            "description": request.description,
            "idempotency_key": values["idempotency_key"],
        }
        try:
            transaction = await self._payments.create_payment(
                actor, payment_values, require_merchant_scope=False, commit=False
            )
        except PaymentError as exc:
            raise PaymentRequestInvalidError(str(exc)) from exc
        request.last_payment_id = transaction.id
        request.payer_user_id = actor.id
        await self._session.commit()
        logger.info(
            "payment_request_payment_created",
            request_id=str(request.id),
            public_identifier=public_identifier,
            payment_reference=transaction.reference,
            user_id=str(actor.id),
        )
        return transaction

    async def fulfill_if_matching(self, transaction: Transaction) -> None:
        if transaction.status is not TransactionStatus.SUCCESS:
            return
        request = await self._requests.get_by_last_payment_id(transaction.id)
        if request is None or request.status is not PaymentRequestStatus.PENDING:
            return
        request.status = PaymentRequestStatus.PAID
        request.paid_at = datetime.now(UTC)
        request.payment_id = transaction.id
        request.payment_reference = transaction.reference
        request.payer_user_id = transaction.cashier_id
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=transaction.cashier_id,
                merchant_id=transaction.merchant_id,
                action="payment_request_fulfilled",
                entity_type="payment_request",
                entity_id=str(request.id),
                before_state={"status": PaymentRequestStatus.PENDING.value},
                after_state={
                    "status": PaymentRequestStatus.PAID.value,
                    "payment_reference": transaction.reference,
                },
            )
        )
        await self._refresh_split(request)
        await self._notifications.record(
            user_id=request.requester_id,
            notification_type=NotificationType.PAYMENT_REQUEST_PAID,
            title="Payment request paid",
            body="Someone completed a payment for your request.",
            event_key=f"payment_request_paid:{request.public_identifier}",
            entity_type="payment_request",
            entity_id=request.public_identifier,
            payment_reference=transaction.reference,
        )
        logger.info(
            "payment_request_fulfilled",
            request_id=str(request.id),
            public_identifier=request.public_identifier,
            payment_reference=transaction.reference,
        )

    async def _expire_if_needed(self, request: PaymentRequest) -> bool:
        if request.status is not PaymentRequestStatus.PENDING:
            return False
        if request.expires_at is None:
            return False
        expires = request.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires > datetime.now(UTC):
            return False
        request.status = PaymentRequestStatus.EXPIRED
        await self._refresh_split(request)
        await self._notifications.record(
            user_id=request.requester_id,
            notification_type=NotificationType.PAYMENT_REQUEST_EXPIRED,
            title="Payment request expired",
            body="A payment request expired before it was paid.",
            event_key=f"payment_request_expired:{request.public_identifier}",
            entity_type="payment_request",
            entity_id=request.public_identifier,
        )
        return True

    async def _refresh_split(self, request: PaymentRequest) -> None:
        if request.bill_split_id is None:
            return
        split = await self._splits.get_by_id(request.bill_split_id)
        if split is None:
            return
        children = split.requests or await self._session.scalars(
            select(PaymentRequest).where(PaymentRequest.bill_split_id == split.id)
        )
        statuses = [child.status for child in children]
        if statuses and all(item is PaymentRequestStatus.PAID for item in statuses):
            split.status = BillSplitStatus.COMPLETED
        elif statuses and all(item is PaymentRequestStatus.CANCELLED for item in statuses):
            split.status = BillSplitStatus.CANCELLED
        elif statuses and all(
            item in {PaymentRequestStatus.EXPIRED, PaymentRequestStatus.CANCELLED} for item in statuses
        ) and any(item is PaymentRequestStatus.EXPIRED for item in statuses):
            split.status = BillSplitStatus.EXPIRED

    async def _resolve_destination(
        self, actor: User, values: dict[str, Any]
    ) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
        source_ref = values.get("source_payment_reference")
        if source_ref:
            transaction = await self._transactions.get_active_by_reference(source_ref)
            if transaction is None:
                raise PaymentRequestNotFoundError("Source payment not found")
            if transaction.cashier_id != actor.id and actor.merchant_id != transaction.merchant_id:
                raise PaymentRequestForbiddenError("Source payment is outside actor scope")
            merchant_id, branch_id, till_id = (
                transaction.merchant_id,
                transaction.branch_id,
                transaction.till_id,
            )
        elif values.get("merchant_id") and values.get("branch_id") and values.get("till_id"):
            merchant_id, branch_id, till_id = (
                values["merchant_id"],
                values["branch_id"],
                values["till_id"],
            )
            if actor.merchant_id is not None and actor.merchant_id != merchant_id:
                raise PaymentRequestForbiddenError("Destination is outside actor scope")
        elif actor.merchant_id is not None:
            till = await self._default_till(actor)
            merchant_id, branch_id, till_id = till
        else:
            raise PaymentRequestInvalidError(
                "A merchant destination is required. Use a previous payment or an active till."
            )
        await self._assert_destination_active(merchant_id, branch_id, till_id)
        return merchant_id, branch_id, till_id

    async def _default_till(self, actor: User) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
        assert actor.merchant_id is not None
        query = select(Till).join(Branch).where(
            Branch.merchant_id == actor.merchant_id,
            Branch.deleted_at.is_(None),
            Branch.is_active.is_(True),
            Till.deleted_at.is_(None),
            Till.is_active.is_(True),
        )
        if actor.branch_id is not None:
            query = query.where(Till.branch_id == actor.branch_id)
        till = await self._session.scalar(query)
        if till is None:
            raise PaymentRequestInvalidError("No active till is available for this merchant")
        return actor.merchant_id, till.branch_id, till.id

    async def _assert_destination_active(
        self, merchant_id: uuid.UUID, branch_id: uuid.UUID, till_id: uuid.UUID
    ) -> None:
        merchant = await self._session.scalar(
            select(Merchant).where(
                Merchant.id == merchant_id,
                Merchant.deleted_at.is_(None),
                Merchant.is_active.is_(True),
            )
        )
        branch = await self._session.scalar(
            select(Branch).where(
                Branch.id == branch_id,
                Branch.merchant_id == merchant_id,
                Branch.deleted_at.is_(None),
                Branch.is_active.is_(True),
            )
        )
        till = await self._session.scalar(
            select(Till).where(
                Till.id == till_id,
                Till.branch_id == branch_id,
                Till.deleted_at.is_(None),
                Till.is_active.is_(True),
            )
        )
        if merchant is None or branch is None or till is None:
            raise PaymentRequestInvalidError("Merchant, branch, or till is unavailable")

    @staticmethod
    def _expiry(seconds: int | None) -> datetime | None:
        if not seconds:
            return None
        return datetime.now(UTC) + timedelta(seconds=int(seconds))

    async def _audit(
        self,
        actor: User,
        action: str,
        entity: Any,
        after: dict[str, Any],
        *,
        entity_type: str = "payment_request",
    ) -> None:
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=actor.id,
                merchant_id=getattr(entity, "merchant_id", actor.merchant_id),
                action=action,
                entity_type=entity_type,
                entity_id=str(entity.id),
                before_state=None,
                after_state=after,
            )
        )
