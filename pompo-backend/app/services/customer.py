"""Customer registration, profile, favorites, insights, and preferences."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security.jwt import JWTConfig
from app.core.security.password import PasswordHasher
from app.models import AuditLog, Merchant, User
from app.models.customer import CustomerPreference, MerchantFavorite
from app.models.enums import TransactionStatus
from app.models.payment import Transaction
from app.repositories.customer import (
    CustomerAnalyticsRepository,
    CustomerPreferenceRepository,
    MerchantFavoriteRepository,
    PaymentRequestRepository,
    SupportRequestRepository,
)
from app.repositories.payment import TransactionRepository
from app.repositories.rbac import RoleRepository
from app.repositories.user import UserRepository
from app.services.auth import AuthService, AuthTokens

logger = get_logger(__name__)

PHONE_VERIFICATION_STATUS = "not_configured"


class CustomerError(Exception):
    pass


class CustomerConflictError(CustomerError):
    pass


class CustomerInvalidError(CustomerError):
    pass


class CustomerNotFoundError(CustomerError):
    pass


class CustomerForbiddenError(CustomerError):
    pass


class CustomerService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        jwt_config: JWTConfig,
        password_hasher: PasswordHasher,
    ) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._roles = RoleRepository(session)
        self._favorites = MerchantFavoriteRepository(session)
        self._preferences = CustomerPreferenceRepository(session)
        self._requests = PaymentRequestRepository(session)
        self._support = SupportRequestRepository(session)
        self._analytics = CustomerAnalyticsRepository(session)
        self._transactions = TransactionRepository(session)
        self._auth = AuthService(session, jwt_config, password_hasher)
        self._hasher = password_hasher

    async def register(
        self,
        values: dict[str, Any],
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[AuthTokens, User]:
        email = str(values["email"]).strip().lower()
        full_name = str(values["full_name"]).strip()
        phone = values.get("phone")
        password = values["password"]
        if await self._users.get_by_email(email) is not None:
            raise CustomerConflictError("An account with these details already exists")
        if phone and await self._users.get_by_phone(phone) is not None:
            raise CustomerConflictError("An account with these details already exists")
        role = await self._roles.get_by_code("customer")
        if role is None:
            raise CustomerInvalidError("Customer role is not configured")
        user = User(
            merchant_id=None,
            branch_id=None,
            role_id=role.id,
            email=email,
            phone=phone,
            full_name=full_name,
            hashed_password=self._hasher.hash(password),
            is_active=True,
            account_status="active",
            is_email_verified=False,
            email_verified_at=None,
            last_login_at=datetime.now(UTC),
        )
        user.role = role
        self._session.add(user)
        await self._session.flush()
        prefs = CustomerPreference(user_id=user.id, preferred_mode="customer")
        self._session.add(prefs)
        await self._auth.request_email_verification(
            user, user_agent=user_agent, ip_address=ip_address
        )
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=user.id,
                merchant_id=None,
                action="customer_registered",
                entity_type="user",
                entity_id=str(user.id),
                before_state=None,
                after_state={"email": email, "role_code": "customer", "is_email_verified": False},
            )
        )
        tokens = await self._auth.issue_session_tokens(
            user, user_agent=user_agent, ip_address=ip_address
        )
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise CustomerConflictError("An account with these details already exists") from exc
        logger.info("customer_registered", user_id=str(user.id))
        return tokens, user

    async def update_profile(self, actor: User, values: dict[str, Any]) -> User:
        if "full_name" in values and values["full_name"] is not None:
            actor.full_name = str(values["full_name"]).strip()
        if "phone" in values:
            phone = values["phone"]
            if phone:
                existing = await self._users.get_by_phone(phone)
                if existing is not None and existing.id != actor.id:
                    raise CustomerConflictError("An account with this phone already exists")
            actor.phone = phone
        if values.get("preferred_mode") is not None:
            prefs = await self._ensure_preferences(actor)
            prefs.preferred_mode = values["preferred_mode"]
        await self._session.commit()
        await self._session.refresh(actor, attribute_names=["role"])
        return actor

    async def get_preferences(self, actor: User) -> CustomerPreference:
        return await self._ensure_preferences(actor)

    async def update_preferences(self, actor: User, values: dict[str, Any]) -> CustomerPreference:
        prefs = await self._ensure_preferences(actor)
        for field in (
            "notify_payment_success",
            "notify_payment_failed",
            "notify_payment_updates",
            "notify_payment_requests",
            "preferred_mode",
        ):
            if field in values and values[field] is not None:
                setattr(prefs, field, values[field])
        await self._session.commit()
        return prefs

    async def list_merchants(self, actor: User) -> list[dict[str, Any]]:
        favorites = await self._favorites.list_for_user(actor.id)
        favorite_ids = {row.merchant_id for row in favorites}
        recent = await self._recent_merchant_rows(actor.id)
        by_id: dict[uuid.UUID, dict[str, Any]] = {}
        for merchant, last_paid, count, last_reference in recent:
            by_id[merchant.id] = {
                "merchant_id": merchant.id,
                "merchant_name": merchant.name,
                "is_favorite": merchant.id in favorite_ids,
                "last_paid_at": last_paid,
                "last_payment_reference": last_reference,
                "payment_count": count,
                "is_active": merchant.is_active,
            }
        for fav in favorites:
            merchant = fav.merchant
            if merchant is None:
                continue
            if merchant.id in by_id:
                by_id[merchant.id]["is_favorite"] = True
                continue
            by_id[merchant.id] = {
                "merchant_id": merchant.id,
                "merchant_name": merchant.name,
                "is_favorite": True,
                "last_paid_at": None,
                "last_payment_reference": None,
                "payment_count": 0,
                "is_active": merchant.is_active,
            }
        return sorted(
            by_id.values(),
            key=lambda item: (
                0 if item["is_favorite"] else 1,
                item["last_paid_at"] is None,
                -(item["last_paid_at"].timestamp() if item["last_paid_at"] else 0),
            ),
        )

    async def add_favorite(self, actor: User, merchant_id: uuid.UUID) -> MerchantFavorite:
        existing = await self._favorites.get_for_user_merchant(actor.id, merchant_id)
        if existing is not None:
            return existing
        merchant = await self._session.get(Merchant, merchant_id)
        if merchant is None or merchant.deleted_at is not None:
            raise CustomerNotFoundError("Merchant not found")
        favorite = MerchantFavorite(user_id=actor.id, merchant_id=merchant_id)
        self._session.add(favorite)
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=actor.id,
                merchant_id=merchant_id,
                action="favorite_created",
                entity_type="merchant_favorite",
                entity_id=str(merchant_id),
                before_state=None,
                after_state={"merchant_id": str(merchant_id)},
            )
        )
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            existing = await self._favorites.get_for_user_merchant(actor.id, merchant_id)
            if existing is not None:
                return existing
            raise
        logger.info("favorite_created", user_id=str(actor.id), merchant_id=str(merchant_id))
        return favorite

    async def remove_favorite(self, actor: User, merchant_id: uuid.UUID) -> None:
        existing = await self._favorites.get_for_user_merchant(actor.id, merchant_id)
        if existing is None:
            return
        await self._session.delete(existing)
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=actor.id,
                merchant_id=merchant_id,
                action="favorite_removed",
                entity_type="merchant_favorite",
                entity_id=str(merchant_id),
                before_state={"merchant_id": str(merchant_id)},
                after_state=None,
            )
        )
        await self._session.commit()
        logger.info("favorite_removed", user_id=str(actor.id), merchant_id=str(merchant_id))

    async def insights(self, actor: User) -> dict[str, Any]:
        now = datetime.now(UTC)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        payload = await self._transactions.customer_insights(
            actor.id, week_start=week_start, month_start=month_start
        )
        payload["disclaimer"] = (
            "These totals are from your completed POMPO payments. This is not a bank statement."
        )
        return payload

    async def platform_stats(self, actor: User) -> dict[str, Any]:
        role = actor.role
        if role is None or role.code != "platform_admin":
            raise CustomerForbiddenError("Insufficient authority")
        counts = await self._requests.count_by_status()
        return {
            "customer_count": await self._analytics.count_customers(),
            "payment_requests": counts,
            "support_open_count": await self._support.open_count(),
        }

    async def _ensure_preferences(self, actor: User) -> CustomerPreference:
        prefs = await self._preferences.get_by_user_id(actor.id)
        if prefs is not None:
            return prefs
        prefs = CustomerPreference(user_id=actor.id)
        self._session.add(prefs)
        await self._session.flush()
        return prefs

    async def _recent_merchant_rows(
        self, cashier_id: uuid.UUID
    ) -> list[tuple[Merchant, datetime | None, int, str | None]]:
        from sqlalchemy import func

        last_paid = func.max(Transaction.completed_at).label("last_paid")
        payment_count = func.count().label("payment_count")
        result = await self._session.execute(
            select(Merchant, last_paid, payment_count)
            .join(Transaction, Transaction.merchant_id == Merchant.id)
            .where(
                Transaction.cashier_id == cashier_id,
                Transaction.deleted_at.is_(None),
                Transaction.status == TransactionStatus.SUCCESS,
                Merchant.deleted_at.is_(None),
            )
            .group_by(Merchant.id)
            .order_by(last_paid.desc())
            .limit(20)
        )
        rows = [(row[0], row[1], int(row[2])) for row in result.all()]
        if not rows:
            return []
        merchant_ids = [merchant.id for merchant, _paid, _count in rows]
        latest = await self._session.execute(
            select(Transaction.merchant_id, Transaction.reference, Transaction.completed_at)
            .where(
                Transaction.cashier_id == cashier_id,
                Transaction.merchant_id.in_(merchant_ids),
                Transaction.deleted_at.is_(None),
                Transaction.status == TransactionStatus.SUCCESS,
            )
            .order_by(Transaction.completed_at.desc())
        )
        last_reference: dict[uuid.UUID, str] = {}
        for merchant_id, reference, _completed in latest.all():
            if merchant_id not in last_reference:
                last_reference[merchant_id] = reference
        return [
            (merchant, paid, count, last_reference.get(merchant.id))
            for merchant, paid, count in rows
        ]
