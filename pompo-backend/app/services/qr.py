"""M009 QR payment orchestration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.base import get_settings
from app.core.logging import get_logger
from app.models import AuditLog, Branch, Merchant, QRCode, Till, Transaction, User
from app.models.enums import QRStatus, QRType, TERMINAL_TRANSACTION_STATUSES, TransactionStatus
from app.payments.state_machine import validate_transition
from app.qr.payload import QRPayloadError, QRPayloadService
from app.repositories.qr import QRCodeRepository
from app.repositories.payment import TransactionRepository
from app.repositories.rbac import AuthorizationRepository
from app.services.authorization import AuthorizationService
from app.services.payment import PaymentError, PaymentService

logger = get_logger(__name__)

DEFAULT_DYNAMIC_TTL_SECONDS = 900


class QRError(Exception):
    """Base class for QR domain failures."""


class QRNotFoundError(QRError):
    pass


class QRForbiddenError(QRError):
    pass


class QRInvalidError(QRError):
    pass


class QRConflictError(QRError):
    pass


class QRService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._qr_codes = QRCodeRepository(session)
        self._transactions = TransactionRepository(session)
        self._authorization = AuthorizationService(AuthorizationRepository(session))
        settings = get_settings()
        self._payload = QRPayloadService(settings.secret_key)
        self._payments = PaymentService(session)

    async def create_static_qr(self, actor: User, values: dict[str, Any]) -> QRCode:
        await self._require(actor, "qr:create")
        merchant_id = values["merchant_id"]
        branch_id = values["branch_id"]
        till_id = values["till_id"]
        merchant, branch, till = await self._validate_context(merchant_id, branch_id, till_id)
        await self._validate_scope(actor, merchant_id, branch_id)

        public_id = self._new_public_id()
        encoded = self._payload.encode_static(public_identifier=public_id)
        qr = QRCode(
            public_identifier=public_id,
            merchant_id=merchant.id,
            branch_id=branch.id,
            till_id=till.id,
            qr_type=QRType.STATIC,
            status=QRStatus.ACTIVE,
            version=1,
            payload=encoded,
            currency="MWK",
            payload_metadata={"created_by": str(actor.id)},
        )
        self._session.add(qr)
        await self._audit(
            actor,
            "qr_static_created",
            qr.id,
            None,
            {"public_identifier": public_id, "till_id": str(till_id)},
        )
        await self._session.commit()
        await self._session.refresh(qr, attribute_names=["merchant", "branch", "till"])
        logger.info("qr_static_created", public_identifier=public_id, till_id=str(till_id))
        return qr

    async def create_dynamic_qr(self, actor: User, values: dict[str, Any]) -> QRCode:
        await self._require(actor, "qr:create")
        merchant_id = values["merchant_id"]
        branch_id = values["branch_id"]
        till_id = values["till_id"]
        merchant, branch, till = await self._validate_context(merchant_id, branch_id, till_id)
        await self._validate_scope(actor, merchant_id, branch_id)

        ttl = int(values.get("expires_in_seconds", DEFAULT_DYNAMIC_TTL_SECONDS))
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)

        payment_values = {
            "merchant_id": merchant_id,
            "branch_id": branch_id,
            "till_id": till_id,
            "amount": values["amount"],
            "currency": values["currency"],
            "payment_method": values["payment_method"],
            "provider_code": values.get("provider_code"),
            "customer_phone": values.get("customer_phone"),
            "description": values.get("description"),
            "idempotency_key": values["idempotency_key"],
        }
        transaction = await self._payments.create_payment(actor, payment_values)
        existing_qr = await self._qr_codes.get_by_transaction_id(transaction.id)
        if existing_qr is not None:
            return existing_qr

        validate_transition(transaction.status, TransactionStatus.QR_GENERATED)
        transaction.status = TransactionStatus.QR_GENERATED

        public_id = self._new_public_id()
        encoded = self._payload.encode_dynamic(
            public_identifier=public_id,
            amount=values["amount"],
            currency=values["currency"],
            expires_at=expires_at,
            payment_reference=transaction.reference,
        )
        qr = QRCode(
            public_identifier=public_id,
            merchant_id=merchant.id,
            branch_id=branch.id,
            till_id=till.id,
            qr_type=QRType.DYNAMIC,
            status=QRStatus.ACTIVE,
            version=1,
            transaction_id=transaction.id,
            payment_reference=transaction.reference,
            amount=values["amount"],
            currency=values["currency"],
            payload=encoded,
            expires_at=expires_at,
            payload_metadata={"created_by": str(actor.id)},
        )
        self._session.add(qr)
        await self._audit(
            actor,
            "qr_dynamic_created",
            qr.id,
            None,
            {
                "public_identifier": public_id,
                "payment_reference": transaction.reference,
                "amount": str(values["amount"]),
            },
        )
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raced = await self._qr_codes.get_by_transaction_id(transaction.id)
            if raced is not None:
                return raced
            raise
        await self._session.refresh(qr, attribute_names=["merchant", "branch", "till", "transaction"])
        logger.info(
            "qr_dynamic_created",
            public_identifier=public_id,
            payment_reference=transaction.reference,
        )
        return qr

    async def get_qr(self, actor: User, public_identifier: str) -> QRCode:
        await self._require(actor, "qr:read")
        qr = await self._qr_codes.get_by_public_identifier(public_identifier)
        if qr is None:
            raise QRNotFoundError("QR code not found")
        await self._validate_scope(actor, qr.merchant_id, qr.branch_id)
        return qr

    async def inspect_qr(self, public_identifier: str) -> QRCode:
        """Public-safe QR lookup for mobile scan preview."""
        qr = await self._qr_codes.get_by_public_identifier(public_identifier)
        if qr is None:
            raise QRNotFoundError("QR code not found")
        await self._refresh_expiry_if_needed(qr)
        if qr.status not in {QRStatus.ACTIVE}:
            raise QRInvalidError("QR code is not available")
        return qr

    async def revoke_qr(self, actor: User, public_identifier: str) -> QRCode:
        await self._require(actor, "qr:revoke")
        qr = await self.get_qr(actor, public_identifier)
        if qr.status is QRStatus.REVOKED:
            return qr
        if qr.status is QRStatus.CONSUMED:
            raise QRInvalidError("Consumed QR codes cannot be revoked")
        before = qr.status.value
        qr.status = QRStatus.REVOKED
        qr.revoked_at = datetime.now(UTC)
        await self._audit(
            actor,
            "qr_revoked",
            qr.id,
            {"status": before},
            {"status": QRStatus.REVOKED.value, "public_identifier": public_identifier},
        )
        await self._session.commit()
        await self._session.refresh(qr, attribute_names=["merchant", "branch", "till"])
        logger.info("qr_revoked", public_identifier=public_identifier)
        return qr

    async def initiate_payment_from_qr(self, actor: User, values: dict[str, Any]) -> Transaction:
        await self._require(actor, "transactions:create")
        raw_payload = values["payload"]
        idempotency_key = values["idempotency_key"]

        try:
            parsed = self._payload.parse(raw_payload)
        except QRPayloadError as exc:
            await self._audit_invalid(actor, raw_payload, str(exc))
            raise QRInvalidError(str(exc)) from exc

        qr = await self._qr_codes.get_by_public_identifier(parsed.public_identifier)
        if qr is None:
            await self._audit_invalid(actor, parsed.public_identifier, "unknown_qr")
            raise QRNotFoundError("QR code not found")

        if qr.qr_type is QRType.DYNAMIC:
            qr = await self._qr_codes.get_by_public_identifier_for_update(parsed.public_identifier)
            if qr is None:
                raise QRNotFoundError("QR code not found")

        if qr.payload != raw_payload.strip():
            await self._audit_invalid(actor, parsed.public_identifier, "payload_mismatch")
            raise QRInvalidError("QR payload does not match server record")

        await self._refresh_expiry_if_needed(qr)
        if qr.status is not QRStatus.ACTIVE:
            raise QRInvalidError(f"QR code is {qr.status.value}")

        if qr.qr_type is QRType.DYNAMIC:
            client_amount = values.get("amount")
            if client_amount is not None and qr.amount is not None and client_amount != qr.amount:
                await self._audit_invalid(actor, qr.public_identifier, "dynamic_amount_override")
                raise QRInvalidError("Amount cannot be modified for dynamic QR")

        if qr.qr_type is QRType.STATIC:
            return await self._pay_from_static_qr(actor, qr, values, idempotency_key)
        return await self._pay_from_dynamic_qr(actor, qr, parsed, idempotency_key)

    async def mark_consumed_if_terminal(self, transaction: Transaction) -> None:
        if transaction.status not in TERMINAL_TRANSACTION_STATUSES:
            return
        if transaction.qr_code is None:
            qr = await self._session.scalar(
                select(QRCode).where(QRCode.transaction_id == transaction.id)
            )
        else:
            qr = transaction.qr_code
        if qr is None or qr.qr_type is not QRType.DYNAMIC:
            return
        self._finalize_dynamic_qr_for_terminal(qr, transaction.status)

    @staticmethod
    def _finalize_dynamic_qr_for_terminal(qr: QRCode, status: TransactionStatus) -> None:
        if status in TERMINAL_TRANSACTION_STATUSES:
            qr.status = QRStatus.CONSUMED
            qr.is_used = True
        elif qr.expires_at and qr.expires_at <= datetime.now(UTC):
            qr.status = QRStatus.EXPIRED

    async def _pay_from_static_qr(
        self,
        actor: User,
        qr: QRCode,
        values: dict[str, Any],
        idempotency_key: str,
    ) -> Transaction:
        amount = values.get("amount")
        if amount is None:
            raise QRInvalidError("Amount is required for static QR payments")
        payment_values = {
            "merchant_id": qr.merchant_id,
            "branch_id": qr.branch_id,
            "till_id": qr.till_id,
            "amount": amount,
            "currency": qr.currency,
            "payment_method": values.get("payment_method", "mobile_money"),
            "provider_code": values.get("provider_code"),
            "customer_phone": values.get("customer_phone"),
            "description": values.get("description"),
            "idempotency_key": idempotency_key,
        }
        try:
            transaction = await self._payments.create_payment(actor, payment_values)
        except PaymentError as exc:
            raise QRInvalidError(str(exc)) from exc
        await self._audit(
            actor,
            "payment_initiated_from_qr",
            transaction.id,
            None,
            {
                "public_identifier": qr.public_identifier,
                "qr_type": QRType.STATIC.value,
                "reference": transaction.reference,
            },
        )
        await self._session.commit()
        logger.info(
            "payment_from_static_qr",
            public_identifier=qr.public_identifier,
            reference=transaction.reference,
        )
        return transaction

    async def _pay_from_dynamic_qr(
        self,
        actor: User,
        qr: QRCode,
        parsed: Any,
        idempotency_key: str,
    ) -> Transaction:
        if qr.expires_at:
            expires_at = qr.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= datetime.now(UTC):
                qr.status = QRStatus.EXPIRED
                await self._session.commit()
                raise QRInvalidError("QR code has expired")

        if parsed.amount is None or parsed.payment_reference is None:
            raise QRInvalidError("Invalid dynamic QR context")

        if qr.amount != parsed.amount or qr.payment_reference != parsed.payment_reference:
            raise QRInvalidError("QR payment context was tampered")

        if parsed.currency is not None and parsed.currency != qr.currency:
            raise QRInvalidError("QR currency was tampered")

        if qr.transaction_id is None:
            raise QRInvalidError("Dynamic QR has no linked payment")

        transaction = await self._session.get(Transaction, qr.transaction_id)
        if transaction is None:
            raise QRNotFoundError("Linked payment not found")

        if transaction.status in TERMINAL_TRANSACTION_STATUSES:
            self._finalize_dynamic_qr_for_terminal(qr, transaction.status)
            await self._session.commit()
            raise QRInvalidError("QR payment is no longer available")

        existing = await self._transactions.get_by_idempotency(qr.merchant_id, idempotency_key)
        if existing is not None and existing.id != transaction.id:
            raise QRConflictError("Idempotency key conflicts with another payment")

        if transaction.status is TransactionStatus.QR_GENERATED:
            validate_transition(transaction.status, TransactionStatus.PENDING)
            transaction.status = TransactionStatus.PENDING

        await self._audit(
            actor,
            "payment_initiated_from_qr",
            transaction.id,
            None,
            {
                "public_identifier": qr.public_identifier,
                "qr_type": QRType.DYNAMIC.value,
                "reference": transaction.reference,
            },
        )
        await self._session.commit()
        await self._session.refresh(transaction, attribute_names=["attempts"])
        logger.info(
            "payment_from_dynamic_qr",
            public_identifier=qr.public_identifier,
            reference=transaction.reference,
        )
        return transaction

    async def _validate_context(
        self, merchant_id: uuid.UUID, branch_id: uuid.UUID, till_id: uuid.UUID
    ) -> tuple[Merchant, Branch, Till]:
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
            raise QRInvalidError("Merchant, branch, or till is unavailable")
        return merchant, branch, till

    async def _refresh_expiry_if_needed(self, qr: QRCode) -> None:
        if qr.qr_type is not QRType.DYNAMIC or qr.status is not QRStatus.ACTIVE or not qr.expires_at:
            return
        expires_at = qr.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            qr.status = QRStatus.EXPIRED
            await self._session.flush()

    async def _validate_scope(
        self, actor: User, merchant_id: uuid.UUID, branch_id: uuid.UUID
    ) -> None:
        if not await self._is_platform_admin(actor) and (
            actor.merchant_id != merchant_id
            or (actor.branch_id is not None and actor.branch_id != branch_id)
        ):
            raise QRForbiddenError("QR is outside actor scope")

    async def _is_platform_admin(self, actor: User) -> bool:
        role = await self._authorization.get_user_role(actor)
        return role is not None and role.code == "platform_admin"

    async def _require(self, actor: User, permission: str) -> None:
        if not await self._authorization.has_permission(actor, permission):
            raise QRForbiddenError("Insufficient authority")

    @staticmethod
    def _new_public_id() -> str:
        return f"QR{uuid.uuid4().hex[:12].upper()}"

    async def _audit(
        self,
        actor: User,
        action: str,
        entity_id: uuid.UUID,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=actor.id,
                merchant_id=actor.merchant_id,
                action=action,
                entity_type="qr_code",
                entity_id=str(entity_id),
                before_state=before,
                after_state=after,
            )
        )

    async def _audit_invalid(self, actor: User, identifier: str, reason: str) -> None:
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=actor.id,
                merchant_id=actor.merchant_id,
                action="qr_invalid_attempt",
                entity_type="qr_code",
                entity_id=identifier[:64],
                before_state=None,
                after_state={"reason": reason},
            )
        )
        await self._session.commit()
        logger.warning("qr_invalid_attempt", identifier=identifier[:32], reason=reason)
