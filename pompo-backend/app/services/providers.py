"""Privileged administration of the payment provider catalog."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, PaymentProvider, User
from app.payments.providers import ProviderCapabilities
from app.payments.registry import ProviderRegistry
from app.repositories.payment import PaymentProviderRepository
from app.repositories.rbac import AuthorizationRepository
from app.services.authorization import AuthorizationService


class ProviderCatalogError(Exception):
    pass


class ProviderCatalogNotFoundError(ProviderCatalogError):
    pass


class ProviderCatalogForbiddenError(ProviderCatalogError):
    pass


class ProviderCatalogConflictError(ProviderCatalogError):
    pass


class ProviderCatalogService:
    def __init__(self, session: AsyncSession, registry: ProviderRegistry | None = None) -> None:
        self._session = session
        self._providers = PaymentProviderRepository(session)
        self._authorization = AuthorizationService(AuthorizationRepository(session))
        self._registry = registry or ProviderRegistry()

    def adapter_codes(self) -> set[str]:
        return {adapter.code for adapter in self._registry.list()}

    async def list_catalog(self, actor: User) -> list[PaymentProvider]:
        await self._require_any(actor, ("providers:read", "transactions:read"))
        return await self._providers.list_catalog()

    async def get_catalog_entry(self, actor: User, code: str) -> PaymentProvider:
        await self._require_any(actor, ("providers:read", "transactions:read"))
        provider = await self._providers.get_by_code(code)
        if provider is None:
            raise ProviderCatalogNotFoundError("Provider not found")
        return provider

    async def update_catalog_entry(
        self, actor: User, code: str, values: dict[str, Any]
    ) -> PaymentProvider:
        await self._require(actor, "providers:update")
        if not await self._is_platform_admin(actor):
            raise ProviderCatalogForbiddenError(
                "Only platform administrators can change provider configuration"
            )
        forbidden = {"code", "is_simulated", "environment", "capabilities", "display_name"}
        if forbidden.intersection(values):
            raise ProviderCatalogForbiddenError("Privileged provider fields cannot be changed")
        provider = await self._providers.get_by_code(code)
        if provider is None:
            raise ProviderCatalogNotFoundError("Provider not found")
        if values.get("is_active") is True and provider.code.value not in self.adapter_codes():
            raise ProviderCatalogConflictError(
                "Cannot enable a provider that has no sandbox adapter"
            )
        before = {key: getattr(provider, key) for key in values}
        for key, value in values.items():
            setattr(provider, key, value)
        await self._audit(actor, "provider_updated", provider.id, before, values)
        await self._session.commit()
        return provider

    def capabilities_for(self, provider: PaymentProvider) -> dict[str, bool]:
        if provider.code.value in self.adapter_codes():
            return asdict(self._registry.capabilities(provider.code.value))
        stored = provider.capabilities or {}
        defaults = asdict(ProviderCapabilities())
        defaults.update({key: bool(value) for key, value in stored.items()})
        return defaults

    async def _is_platform_admin(self, actor: User) -> bool:
        role = await self._authorization.get_user_role(actor)
        return role is not None and role.code == "platform_admin"

    async def _require(self, actor: User, permission: str) -> None:
        if not await self._authorization.has_permission(actor, permission):
            raise ProviderCatalogForbiddenError("Insufficient authority")

    async def _require_any(self, actor: User, permissions: tuple[str, ...]) -> None:
        for permission in permissions:
            if await self._authorization.has_permission(actor, permission):
                return
        raise ProviderCatalogForbiddenError("Insufficient authority")

    async def _audit(
        self,
        actor: User,
        action: str,
        entity_id,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=actor.id,
                merchant_id=actor.merchant_id,
                action=action,
                entity_type="provider",
                entity_id=str(entity_id),
                before_state=before,
                after_state=after,
            )
        )
