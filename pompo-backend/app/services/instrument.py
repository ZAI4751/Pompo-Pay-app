"""Customer payment instruments: enrollment, default, revoke, checkout binding.

This is not a wallet. POMPO never stores PINs, CVVs, PANs, or provider passwords.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.base import get_settings
from app.core.logging import get_logger
from app.models import AuditLog, PaymentInstrument, User
from app.models.enums import (
    PaymentInstrumentStatus,
    PaymentInstrumentType,
    ProviderAuthorizationState,
    ProviderCode,
)
from app.payments.instrument_tokens import (
    digest_token,
    mask_card_last4,
    mask_msisdn,
    new_sandbox_token,
    normalize_msisdn,
    reject_secret_fields,
)
from app.payments.providers import UnsupportedProviderOperation, require_capability
from app.payments.registry import ProviderRegistry
from app.repositories.instrument import PaymentInstrumentRepository
from app.repositories.payment import PaymentProviderRepository

logger = get_logger(__name__)

INSTRUMENT_TO_PAYMENT_METHOD = {
    PaymentInstrumentType.MOBILE_MONEY: "mobile_money",
    PaymentInstrumentType.VISA: "card",
    PaymentInstrumentType.MASTERCARD: "card",
}

SANDBOX_VISA_LAST4 = "4242"
SANDBOX_MASTERCARD_LAST4 = "0912"

CATALOG: tuple[dict[str, Any], ...] = (
    {
        "provider_code": "simulated",
        "instrument_type": "mobile_money",
        "label": "Test Airtel Money",
        "available": True,
        "is_sandbox": True,
        "reason": None,
        "authorization_state": ProviderAuthorizationState.NOT_REQUIRED.value,
    },
    {
        "provider_code": "simulated",
        "instrument_type": "visa",
        "label": "Sandbox Visa",
        "available": True,
        "is_sandbox": True,
        "reason": None,
        "authorization_state": ProviderAuthorizationState.NOT_REQUIRED.value,
    },
    {
        "provider_code": "simulated",
        "instrument_type": "mastercard",
        "label": "Sandbox Mastercard",
        "available": True,
        "is_sandbox": True,
        "reason": None,
        "authorization_state": ProviderAuthorizationState.NOT_REQUIRED.value,
    },
    {
        "provider_code": "airtel_money",
        "instrument_type": "mobile_money",
        "label": "Airtel Money",
        "available": False,
        "is_sandbox": False,
        "reason": (
            "Airtel Collection APIs 2.0 swagger does not document a reusable "
            "account token. Enrollment is not available."
        ),
        "authorization_state": ProviderAuthorizationState.UNSUPPORTED.value,
    },
    {
        "provider_code": "tnm_mpamba",
        "instrument_type": "mobile_money",
        "label": "TNM Mpamba",
        "available": False,
        "is_sandbox": False,
        "reason": (
            "TNM Mpamba live HTTP contract is not in POMPO. "
            "Saved Mpamba is not available."
        ),
        "authorization_state": ProviderAuthorizationState.UNSUPPORTED.value,
    },
    {
        "provider_code": "national_bank",
        "instrument_type": "visa",
        "label": "National Bank Visa",
        "available": False,
        "is_sandbox": False,
        "reason": "Coming soon",
        "authorization_state": ProviderAuthorizationState.UNSUPPORTED.value,
    },
    {
        "provider_code": "standard_bank",
        "instrument_type": "visa",
        "label": "Standard Bank Visa",
        "available": False,
        "is_sandbox": False,
        "reason": (
            "Standard Bank Malawi live HTTP contract is not in POMPO. "
            "Saved cards are not available. POMPO does not store PAN or CVV."
        ),
        "authorization_state": ProviderAuthorizationState.UNSUPPORTED.value,
    },
    {
        "provider_code": "standard_bank",
        "instrument_type": "mastercard",
        "label": "Standard Bank Mastercard",
        "available": False,
        "is_sandbox": False,
        "reason": (
            "Standard Bank Malawi live HTTP contract is not in POMPO. "
            "Saved cards are not available. POMPO does not store PAN or CVV."
        ),
        "authorization_state": ProviderAuthorizationState.UNSUPPORTED.value,
    },
    {
        "provider_code": "nbs",
        "instrument_type": "visa",
        "label": "NBS Visa",
        "available": False,
        "is_sandbox": False,
        "reason": "Coming soon",
        "authorization_state": ProviderAuthorizationState.UNSUPPORTED.value,
    },
)


class InstrumentError(Exception):
    pass


class InstrumentNotFoundError(InstrumentError):
    pass


class InstrumentForbiddenError(InstrumentError):
    pass


class InstrumentInvalidError(InstrumentError):
    pass


class InstrumentConflictError(InstrumentError):
    pass


class PaymentInstrumentService:
    def __init__(self, session: AsyncSession, registry: ProviderRegistry | None = None) -> None:
        self._session = session
        self._instruments = PaymentInstrumentRepository(session)
        self._providers = PaymentProviderRepository(session)
        self._registry = registry or ProviderRegistry()

    def catalog(self) -> list[dict[str, Any]]:
        return [dict(item) for item in CATALOG]

    async def list_mine(self, actor: User) -> list[PaymentInstrument]:
        return await self._instruments.list_for_customer(actor.id)

    async def list_admin(self, actor: User, *, limit: int = 50, offset: int = 0) -> list[PaymentInstrument]:
        from app.repositories.rbac import AuthorizationRepository
        from app.services.authorization import AuthorizationService

        authorization = AuthorizationService(AuthorizationRepository(self._session))
        if not await authorization.has_permission(actor, "users:read"):
            raise InstrumentForbiddenError("Insufficient authority")
        return await self._instruments.list_all_safe(limit=limit, offset=offset)

    async def get_mine(self, actor: User, public_identifier: str) -> PaymentInstrument:
        row = await self._instruments.get_by_public_id(public_identifier)
        if row is None or row.customer_id != actor.id:
            raise InstrumentNotFoundError("Payment method not found")
        return row

    async def enroll(self, actor: User, values: dict[str, Any]) -> PaymentInstrument:
        reject_secret_fields(values)
        provider_code = str(values.get("provider_code") or "").strip()
        type_raw = str(values.get("instrument_type") or "").strip().lower()
        try:
            instrument_type = PaymentInstrumentType(type_raw)
        except ValueError as exc:
            raise InstrumentInvalidError("Unsupported payment method type") from exc
        offer = next(
            (
                item
                for item in CATALOG
                if item["provider_code"] == provider_code and item["instrument_type"] == type_raw
            ),
            None,
        )
        if offer is None:
            raise InstrumentInvalidError("That payment method is not offered")
        if not offer["available"]:
            raise InstrumentInvalidError(offer["reason"] or "Not available yet")
        try:
            ProviderCode(provider_code)
        except ValueError as exc:
            raise InstrumentInvalidError("Unknown provider") from exc
        provider = await self._providers.get_by_code(provider_code)
        if provider is None or not provider.is_active:
            raise InstrumentInvalidError("Provider is not available")
        public_id = f"PIM-{uuid.uuid4().hex[:16].upper()}"
        adapter = self._registry.get(provider_code)
        self._audit(
            actor,
            "provider_authorization_started",
            public_id,
            None,
            {
                "provider_code": provider_code,
                "instrument_type": type_raw,
                "authorization_state": ProviderAuthorizationState.COMPLETED.value,
            },
        )
        try:
            require_capability(adapter, "instrument_enroll")
        except UnsupportedProviderOperation as exc:
            self._audit(
                actor,
                "provider_authorization_failed",
                public_id,
                None,
                {"provider_code": provider_code, "reason": "unsupported_capability"},
            )
            await self._session.commit()
            raise InstrumentInvalidError(str(exc)) from exc

        display_name, masked, extra = self._display_for_enroll(instrument_type, values, offer)
        token = new_sandbox_token()
        digest = digest_token(get_settings().jwt_secret_key, token)
        make_default = bool(values.get("make_default"))
        if make_default:
            await self._clear_default(actor.id)
            await self._session.flush()
        row = PaymentInstrument(
            customer_id=actor.id,
            provider_id=provider.id,
            public_identifier=public_id,
            instrument_type=instrument_type,
            display_name=values.get("display_name") or display_name,
            masked_identifier=masked,
            token_reference=digest,
            status=PaymentInstrumentStatus.ACTIVE,
            authorization_state=ProviderAuthorizationState.COMPLETED,
            is_default=make_default or await self._instruments.get_default(actor.id) is None,
            is_sandbox=True,
            safe_metadata={"sandbox": True, **extra},
        )
        if row.is_default:
            await self._clear_default(actor.id)
            await self._session.flush()
            row.is_default = True
        self._session.add(row)
        self._audit(
            actor,
            "payment_method_added",
            public_id,
            None,
            {
                "provider_code": provider_code,
                "instrument_type": type_raw,
                "masked_identifier": masked,
                "is_sandbox": True,
            },
        )
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise InstrumentConflictError("Could not save that payment method") from exc
        loaded = await self._instruments.get_by_public_id(public_id)
        if loaded is None:
            raise InstrumentNotFoundError("Payment method not found")
        logger.info(
            "payment_method_added",
            public_identifier=public_id,
            provider_code=provider_code,
            instrument_type=type_raw,
            user_id=str(actor.id),
        )
        return loaded

    async def verify(self, actor: User, public_identifier: str) -> PaymentInstrument:
        row = await self.get_mine(actor, public_identifier)
        if row.status is PaymentInstrumentStatus.REVOKED:
            raise InstrumentInvalidError("A revoked payment method cannot be verified")
        adapter = self._registry.get(row.provider.code.value)
        try:
            require_capability(adapter, "instrument_verify")
        except UnsupportedProviderOperation as exc:
            raise InstrumentInvalidError(str(exc)) from exc
        before = row.status.value
        row.status = PaymentInstrumentStatus.ACTIVE
        row.authorization_state = ProviderAuthorizationState.COMPLETED
        self._audit(
            actor,
            "payment_method_verified",
            row.public_identifier,
            {"status": before},
            {"status": row.status.value, "authorization_state": row.authorization_state.value},
        )
        await self._session.commit()
        logger.info("payment_method_verified", public_identifier=row.public_identifier)
        return row

    async def set_default(self, actor: User, public_identifier: str) -> PaymentInstrument:
        row = await self.get_mine(actor, public_identifier)
        if row.status is not PaymentInstrumentStatus.ACTIVE:
            raise InstrumentInvalidError("Only an active payment method can be default")
        await self._clear_default(actor.id)
        await self._session.flush()
        row.is_default = True
        self._audit(
            actor,
            "payment_method_set_default",
            row.public_identifier,
            None,
            {"public_identifier": row.public_identifier},
        )
        await self._session.commit()
        logger.info("payment_method_set_default", public_identifier=row.public_identifier)
        return row

    async def revoke(self, actor: User, public_identifier: str) -> PaymentInstrument:
        row = await self.get_mine(actor, public_identifier)
        if row.status is PaymentInstrumentStatus.REVOKED:
            return row
        adapter = self._registry.get(row.provider.code.value)
        if adapter.capabilities.supports_instrument_remove:
            require_capability(adapter, "instrument_remove")
        row.status = PaymentInstrumentStatus.REVOKED
        row.is_default = False
        row.revoked_at = datetime.now(UTC)
        self._audit(
            actor,
            "payment_method_revoked",
            row.public_identifier,
            None,
            {"status": PaymentInstrumentStatus.REVOKED.value},
        )
        await self._session.commit()
        logger.info("payment_method_revoked", public_identifier=row.public_identifier)
        return row

    async def require_chargeable(self, actor: User, public_identifier: str) -> PaymentInstrument:
        row = await self.get_mine(actor, public_identifier)
        if row.status is PaymentInstrumentStatus.REVOKED:
            raise InstrumentInvalidError("That payment method has been revoked")
        if row.status is not PaymentInstrumentStatus.ACTIVE:
            raise InstrumentInvalidError("That payment method is not active")
        adapter = self._registry.get(row.provider.code.value)
        try:
            require_capability(adapter, "instrument_charge")
        except UnsupportedProviderOperation as exc:
            raise InstrumentInvalidError(str(exc)) from exc
        return row

    async def mark_used(self, instrument: PaymentInstrument) -> None:
        instrument.last_used_at = datetime.now(UTC)
        self._audit(
            None,
            "payment_method_used",
            instrument.public_identifier,
            None,
            {"public_identifier": instrument.public_identifier},
            actor_id=instrument.customer_id,
        )

    async def _clear_default(self, customer_id: uuid.UUID) -> None:
        current = await self._instruments.get_default(customer_id)
        if current is not None:
            current.is_default = False

    def _audit(
        self,
        actor: User | None,
        action: str,
        entity_id: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=actor.id if actor is not None else actor_id,
                merchant_id=actor.merchant_id if actor is not None else None,
                action=action,
                entity_type="payment_instrument",
                entity_id=entity_id,
                before_state=before,
                after_state=after,
            )
        )

    @staticmethod
    def _display_for_enroll(
        instrument_type: PaymentInstrumentType,
        values: dict[str, Any],
        offer: dict[str, Any],
    ) -> tuple[str, str, dict[str, str]]:
        if instrument_type is PaymentInstrumentType.MOBILE_MONEY:
            msisdn = values.get("msisdn")
            if not msisdn:
                raise InstrumentInvalidError("A mobile-money number is required")
            try:
                e164 = normalize_msisdn(str(msisdn))
                masked = mask_msisdn(e164)
            except ValueError as exc:
                raise InstrumentInvalidError(str(exc)) from exc
            return offer["label"], masked, {"channel": "mobile_money"}
        last4 = str(values.get("card_last4") or "")
        expected = (
            SANDBOX_VISA_LAST4
            if instrument_type is PaymentInstrumentType.VISA
            else SANDBOX_MASTERCARD_LAST4
        )
        if last4 != expected:
            raise InstrumentInvalidError(
                f"Sandbox {instrument_type.value} enrollment requires last4 {expected}"
            )
        try:
            masked = mask_card_last4(last4)
        except ValueError as exc:
            raise InstrumentInvalidError(str(exc)) from exc
        return offer["label"], masked, {"brand": instrument_type.value, "last4": last4}


def payment_method_for(instrument: PaymentInstrument) -> str:
    return INSTRUMENT_TO_PAYMENT_METHOD[instrument.instrument_type]
