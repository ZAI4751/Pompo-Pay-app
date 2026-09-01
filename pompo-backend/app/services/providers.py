"""Privileged administration of the payment provider catalog."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import AuditLog, PaymentProvider, User
from app.models.enums import ProviderCode, ProviderHealthState, ProviderType
from app.payments.catalog import CATALOG_BY_CODE
from app.payments.config import resolve_provider_runtime_config
from app.payments.contracts import get_authoritative_mapper
from app.payments.credentials import normalize_rail_environment, production_rails_permitted
from app.payments.health import operational_health_state
from app.payments.providers import ProviderAdapter, ProviderCapabilities, ProviderHealth
from app.payments.registry import ProviderRegistry
from app.repositories.payment import PaymentProviderRepository
from app.repositories.rbac import AuthorizationRepository
from app.services.authorization import AuthorizationService

logger = get_logger(__name__)


class ProviderCatalogError(Exception):
    pass


class ProviderCatalogNotFoundError(ProviderCatalogError):
    pass


class ProviderCatalogForbiddenError(ProviderCatalogError):
    pass


class ProviderCatalogConflictError(ProviderCatalogError):
    pass


class ProviderCatalogInvalidError(ProviderCatalogError):
    pass


class ProviderCatalogService:
    def __init__(self, session: AsyncSession, registry: ProviderRegistry | None = None) -> None:
        self._session = session
        self._providers = PaymentProviderRepository(session)
        self._authorization = AuthorizationService(AuthorizationRepository(session))
        self._registry = registry or ProviderRegistry()

    def adapter_codes(self) -> set[str]:
        return {adapter.code for adapter in self._registry.list()}

    def adapter_for(self, code: str) -> ProviderAdapter | None:
        return self._registry.get_optional(code)

    async def list_catalog(self, actor: User) -> list[PaymentProvider]:
        await self._require_any(actor, ("providers:read", "transactions:read"))
        return await self._providers.list_catalog()

    async def get_catalog_entry(self, actor: User, code: str) -> PaymentProvider:
        await self._require_any(actor, ("providers:read", "transactions:read"))
        provider = await self._providers.get_by_code(code)
        if provider is None:
            raise ProviderCatalogNotFoundError("Provider not found")
        return provider

    async def create_catalog_entry(self, actor: User, values: dict[str, Any]) -> PaymentProvider:
        await self._require(actor, "providers:create")
        await self._require_platform_admin(actor)
        try:
            code = ProviderCode(values["code"])
        except ValueError as exc:
            raise ProviderCatalogInvalidError("Unknown provider code") from exc
        if await self._providers.get_by_code(code.value) is not None:
            raise ProviderCatalogConflictError("Provider already exists")

        definition = CATALOG_BY_CODE.get(code)
        adapter = self.adapter_for(code.value)
        provider_type = self._resolve_type(values.get("provider_type"), definition)
        is_simulated = True if definition is None else definition.is_simulated
        if definition is not None:
            is_simulated = definition.is_simulated
        live_ready = adapter is not None and adapter.live_contract_ready
        provider = PaymentProvider(
            code=code,
            display_name=values["display_name"],
            provider_type=provider_type,
            is_active=False,
            is_simulated=is_simulated,
            environment=values.get("environment") or "sandbox",
            health_state=ProviderHealthState.DISABLED,
            priority=values.get("priority") or (definition.priority if definition else 100),
            supported_currencies=values.get("supported_currencies")
            or (list(definition.supported_currencies) if definition else ["MWK"]),
            supported_payment_methods=values.get("supported_payment_methods")
            or (list(definition.supported_payment_methods) if definition else ["mobile_money"]),
            capabilities=asdict(adapter.capabilities)
            if adapter is not None
            else asdict(ProviderCapabilities()),
            config_refs=dict(definition.config_refs) if definition else {},
        )
        if live_ready and values.get("is_active"):
            provider.is_active = True
            provider.health_state = ProviderHealthState.ACTIVE
        self._session.add(provider)
        await self._audit(actor, "provider_created", None, None, {"code": code.value})
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ProviderCatalogConflictError("Provider already exists") from exc
        logger.info("provider_created", provider_code=code.value, live_contract_ready=live_ready)
        return provider

    async def update_catalog_entry(
        self, actor: User, code: str, values: dict[str, Any]
    ) -> PaymentProvider:
        await self._require(actor, "providers:update")
        await self._require_platform_admin(actor)
        forbidden = {"code", "is_simulated", "capabilities", "config_refs", "provider_type"}
        if forbidden.intersection(values):
            raise ProviderCatalogForbiddenError("Privileged provider fields cannot be changed")
        provider = await self._providers.get_by_code(code)
        if provider is None:
            raise ProviderCatalogNotFoundError("Provider not found")
        next_active = values["is_active"] if "is_active" in values else provider.is_active
        next_environment = values["environment"] if "environment" in values else provider.environment
        if next_active:
            original_environment = provider.environment
            provider.environment = next_environment
            try:
                self._assert_can_enable(provider)
            finally:
                provider.environment = original_environment
        before = {key: _safe_value(getattr(provider, key)) for key in values}
        for key, value in values.items():
            setattr(provider, key, value)
        if "is_active" in values:
            provider.health_state = await self._refresh_health_state(provider)
        await self._audit(actor, "provider_updated", provider.id, before, values)
        await self._session.commit()
        logger.info(
            "provider_updated",
            provider_code=provider.code.value,
            is_active=provider.is_active,
            health_state=provider.health_state.value,
        )
        return provider

    async def enable_provider(self, actor: User, code: str) -> PaymentProvider:
        return await self.update_catalog_entry(actor, code, {"is_active": True})

    async def disable_provider(self, actor: User, code: str) -> PaymentProvider:
        return await self.update_catalog_entry(actor, code, {"is_active": False})

    async def inspect_health(self, actor: User, code: str) -> tuple[PaymentProvider, ProviderHealth]:
        provider = await self.get_catalog_entry(actor, code)
        health = await self.adapter_health(provider)
        logger.info(
            "provider_health_observed",
            provider_code=provider.code.value,
            configured=health.configured,
            contract_ready=health.contract_ready,
            supports_health_check=health.supports_health_check,
            reachable=health.reachable,
        )
        return provider, health

    async def adapter_health(self, provider: PaymentProvider) -> ProviderHealth:
        adapter = self.adapter_for(provider.code.value)
        if adapter is None:
            return ProviderHealth(
                configured=False,
                contract_ready=False,
                supports_health_check=False,
                reachable=None,
                message="No adapter is registered",
            )
        return await adapter.health_check()

    async def _refresh_health_state(self, provider: PaymentProvider) -> ProviderHealthState:
        health = await self.adapter_health(provider)
        return operational_health_state(
            is_active=provider.is_active,
            adapter=self.adapter_for(provider.code.value),
            adapter_health=health,
        )

    def capabilities_for(self, provider: PaymentProvider) -> dict[str, bool]:
        adapter = self.adapter_for(provider.code.value)
        if adapter is not None:
            return asdict(adapter.capabilities)
        stored = provider.capabilities or {}
        defaults = asdict(ProviderCapabilities())
        defaults.update({key: bool(value) for key, value in stored.items()})
        return defaults

    def configuration_status(self, provider: PaymentProvider) -> dict[str, Any]:
        runtime = resolve_provider_runtime_config(
            provider.code.value, simulated=provider.is_simulated
        )
        adapter = self.adapter_for(provider.code.value)
        rail_environment = normalize_rail_environment(provider.environment)
        mapper = get_authoritative_mapper(provider.code.value, rail_environment)
        contract_registered = provider.is_simulated or mapper is not None
        production_permitted = production_rails_permitted()
        if provider.is_simulated:
            complete = True
        else:
            complete = (
                runtime.configuration_complete
                and contract_registered
                and adapter is not None
                and adapter.live_contract_ready
            )
        return {
            "base_url_configured": runtime.base_url_configured,
            "timeout_seconds": runtime.timeout_seconds,
            "auth_configured": runtime.secrets_configured,
            "signing_configured": runtime.webhook_signing_configured,
            "configuration_complete": complete,
            "rail_environment": rail_environment,
            "production_rail_permitted": production_permitted,
            "contract_registered": contract_registered,
        }

    def _assert_can_enable(self, provider: PaymentProvider) -> None:
        adapter = self.adapter_for(provider.code.value)
        if adapter is None:
            raise ProviderCatalogConflictError("Cannot enable a provider that has no adapter")
        if not adapter.live_contract_ready:
            raise ProviderCatalogConflictError(
                "Cannot enable a provider whose live contract is not implemented"
            )
        if (
            normalize_rail_environment(provider.environment) == "production"
            and not production_rails_permitted()
        ):
            raise ProviderCatalogConflictError(
                "Production provider rails cannot be enabled outside production"
            )

    def _resolve_type(
        self, raw: str | None, definition
    ) -> ProviderType:
        if raw:
            try:
                return ProviderType(raw)
            except ValueError as exc:
                raise ProviderCatalogInvalidError("Unknown provider type") from exc
        if definition is not None:
            return definition.provider_type
        return ProviderType.SIMULATED

    async def _require_platform_admin(self, actor: User) -> None:
        if not await self._is_platform_admin(actor):
            raise ProviderCatalogForbiddenError(
                "Only platform administrators can change provider configuration"
            )

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
                entity_id=str(entity_id) if entity_id is not None else after.get("code", ""),
                before_state=before,
                after_state=after,
            )
        )


def _safe_value(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    return value
