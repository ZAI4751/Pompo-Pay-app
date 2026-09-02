"""Integration client lifecycle, API-key authentication, and POS context."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.base import get_settings
from app.core.logging import get_logger
from app.integrations.errors import IntegrationAPIError
from app.integrations.keys import (
    derive_webhook_secret,
    dummy_api_key_hash,
    generate_api_key,
    generate_client_public_id,
    hash_secret,
    key_prefix,
    looks_like_api_key,
    webhook_secret_prefix,
)
from app.integrations.scopes import (
    DEFAULT_DEVELOPER_SCOPES,
    DEFAULT_PARTNER_SCOPES,
    DEFAULT_POS_SCOPES,
    has_scope,
    normalize_scopes,
)
from app.models import APIKey, AuditLog, Branch, IntegrationClient, Merchant, Till, User
from app.models.enums import APIClientEnvironment, APIClientStatus, APIClientType
from app.payments.webhooks import constant_time_compare
from app.repositories.integration import APIKeyRepository, IntegrationClientRepository
from app.repositories.rbac import AuthorizationRepository
from app.services.authorization import AuthorizationService

logger = get_logger(__name__)


@dataclass(frozen=True)
class APIClientPrincipal:
    """Authenticated machine identity resolved from an API key."""

    client: IntegrationClient
    api_key: APIKey

    @property
    def scopes(self) -> list[str]:
        return list(self.client.scopes or [])

    def has_scope(self, required: frozenset[str] | str) -> bool:
        return has_scope(self.scopes, required)


class IntegrationError(Exception):
    pass


class IntegrationNotFoundError(IntegrationError):
    pass


class IntegrationForbiddenError(IntegrationError):
    pass


class IntegrationInvalidError(IntegrationError):
    pass


class IntegrationConflictError(IntegrationError):
    pass


def _default_scopes_for(client_type: APIClientType) -> tuple[str, ...]:
    if client_type is APIClientType.MERCHANT_POS:
        return DEFAULT_POS_SCOPES
    if client_type is APIClientType.PARTNER:
        return DEFAULT_PARTNER_SCOPES
    return DEFAULT_DEVELOPER_SCOPES


class IntegrationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._clients = IntegrationClientRepository(session)
        self._keys = APIKeyRepository(session)
        self._authorization = AuthorizationService(AuthorizationRepository(session))
        self._settings = get_settings()

    async def authenticate_api_key(self, raw_key: str | None) -> APIClientPrincipal:
        presented = (raw_key or "").strip()
        hashed = hash_secret(self._settings.secret_key, presented or "missing")
        dummy = dummy_api_key_hash(self._settings.secret_key)
        if not looks_like_api_key(presented):
            constant_time_compare(hashed, dummy)
            raise IntegrationAPIError("invalid_api_key", "Invalid API key")

        record = await self._keys.get_by_hashed_key(hashed)
        if record is None:
            constant_time_compare(hashed, dummy)
            raise IntegrationAPIError("invalid_api_key", "Invalid API key")
        if not constant_time_compare(record.hashed_key, hashed):
            raise IntegrationAPIError("invalid_api_key", "Invalid API key")
        if record.key_prefix != key_prefix(presented):
            raise IntegrationAPIError("invalid_api_key", "Invalid API key")
        if record.revoked_at is not None or not record.is_active:
            raise IntegrationAPIError("api_key_revoked", "API key has been revoked")
        if record.expires_at is not None:
            expires = record.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if expires <= datetime.now(UTC):
                raise IntegrationAPIError("api_key_expired", "API key has expired")

        client = record.client
        if client is None and record.client_id is not None:
            client = await self._clients.get_by_id(record.client_id)
        if client is None:
            raise IntegrationAPIError("invalid_api_key", "Invalid API key")
        if client.status is APIClientStatus.REVOKED or client.revoked_at is not None:
            raise IntegrationAPIError("api_key_revoked", "API key has been revoked")
        if client.status is not APIClientStatus.ACTIVE:
            raise IntegrationAPIError("api_key_inactive", "Integration client is disabled")

        now = datetime.now(UTC)
        record.last_used_at = now
        client.last_used_at = now
        await self._session.flush()
        logger.info(
            "integration_authenticated",
            client_id=str(client.id),
            client_public_id=client.public_id,
            key_prefix=record.key_prefix,
        )
        return APIClientPrincipal(client=client, api_key=record)

    async def create_client(self, actor: User, values: dict[str, Any]) -> tuple[IntegrationClient, str, str]:
        await self._require_admin(actor, "api_keys:create")
        client_type = self._parse_client_type(values["client_type"])
        environment = self._parse_environment(values.get("environment", "sandbox"))
        merchant, branch, till = await self._validate_context(
            actor,
            values["merchant_id"],
            values.get("branch_id"),
            values.get("till_id"),
            client_type=client_type,
        )
        try:
            scopes = normalize_scopes(values.get("scopes"), default=_default_scopes_for(client_type))
        except ValueError as exc:
            raise IntegrationInvalidError(str(exc)) from exc

        webhook_url = self._normalize_webhook_url(values.get("webhook_url"))
        client = IntegrationClient(
            public_id=generate_client_public_id(),
            name=values["name"].strip(),
            client_type=client_type,
            environment=environment,
            status=APIClientStatus.ACTIVE,
            merchant_id=merchant.id,
            branch_id=branch.id if branch else None,
            till_id=till.id if till else None,
            scopes=scopes,
            webhook_url=webhook_url,
            webhook_secret_version=1,
            created_by_user_id=actor.id,
            rate_limit_requests=values.get("rate_limit_requests"),
        )
        self._session.add(client)
        await self._session.flush()
        signing_secret = derive_webhook_secret(
            self._settings.secret_key, client.id, client.webhook_secret_version
        )
        client.webhook_secret_prefix = webhook_secret_prefix(signing_secret)
        raw_key, api_key = self._issue_key(client, name="primary")
        await self._audit(
            actor,
            "api_client_created",
            client.id,
            None,
            {
                "public_id": client.public_id,
                "client_type": client.client_type.value,
                "merchant_id": str(merchant.id),
                "scopes": scopes,
                "key_prefix": api_key.key_prefix,
            },
            merchant_id=merchant.id,
        )
        await self._session.commit()
        await self._session.refresh(client, attribute_names=["api_keys", "merchant", "branch", "till"])
        logger.info(
            "api_client_created",
            client_id=str(client.id),
            client_public_id=client.public_id,
            key_prefix=api_key.key_prefix,
        )
        return client, raw_key, signing_secret

    async def list_clients(
        self, actor: User, *, merchant_id: uuid.UUID | None = None, limit: int = 50, offset: int = 0
    ) -> list[IntegrationClient]:
        await self._require_admin(actor, "api_keys:read")
        scoped_merchant = merchant_id
        if not await self._is_platform_admin(actor):
            if actor.merchant_id is None:
                raise IntegrationForbiddenError("Merchant context is required")
            if merchant_id is not None and merchant_id != actor.merchant_id:
                raise IntegrationForbiddenError("Resource is outside actor scope")
            scoped_merchant = actor.merchant_id
        return await self._clients.list_clients(
            merchant_id=scoped_merchant, limit=min(limit, 100), offset=max(offset, 0)
        )

    async def get_client(self, actor: User, client_id: uuid.UUID) -> IntegrationClient:
        await self._require_admin(actor, "api_keys:read")
        client = await self._clients.get_with_keys(client_id)
        if client is None:
            raise IntegrationNotFoundError("Integration client not found")
        await self._assert_client_scope(actor, client)
        return client

    async def update_client(
        self, actor: User, client_id: uuid.UUID, values: dict[str, Any]
    ) -> IntegrationClient:
        await self._require_admin(actor, "api_keys:create")
        client = await self.get_client(actor, client_id)
        before = {
            "name": client.name,
            "scopes": list(client.scopes or []),
            "webhook_url": client.webhook_url,
            "status": client.status.value,
        }
        if "name" in values and values["name"]:
            client.name = values["name"].strip()
        if "scopes" in values and values["scopes"] is not None:
            try:
                client.scopes = normalize_scopes(
                    values["scopes"], default=_default_scopes_for(client.client_type)
                )
            except ValueError as exc:
                raise IntegrationInvalidError(str(exc)) from exc
        if "webhook_url" in values:
            client.webhook_url = self._normalize_webhook_url(values["webhook_url"], allow_empty=True)
        if "rate_limit_requests" in values:
            client.rate_limit_requests = values["rate_limit_requests"]
        if values.get("disabled") is True and client.status is APIClientStatus.ACTIVE:
            client.status = APIClientStatus.DISABLED
        if values.get("disabled") is False and client.status is APIClientStatus.DISABLED:
            client.status = APIClientStatus.ACTIVE
        await self._audit(
            actor,
            "integration_updated",
            client.id,
            before,
            {
                "name": client.name,
                "scopes": list(client.scopes or []),
                "webhook_url": client.webhook_url,
                "status": client.status.value,
            },
            merchant_id=client.merchant_id,
        )
        if client.status is APIClientStatus.DISABLED and before["status"] == "active":
            await self._audit(
                actor,
                "integration_disabled",
                client.id,
                {"status": "active"},
                {"status": "disabled"},
                merchant_id=client.merchant_id,
            )
        await self._session.commit()
        logger.info("integration_updated", client_id=str(client.id), client_public_id=client.public_id)
        return client

    async def rotate_key(
        self, actor: User, client_id: uuid.UUID, *, revoke_others: bool = True
    ) -> tuple[IntegrationClient, str]:
        await self._require_admin(actor, "api_keys:create")
        client = await self.get_client(actor, client_id)
        if client.status is APIClientStatus.REVOKED:
            raise IntegrationInvalidError("Revoked clients cannot issue keys")
        if revoke_others:
            now = datetime.now(UTC)
            for existing in client.api_keys:
                if existing.is_active and existing.revoked_at is None:
                    existing.is_active = False
                    existing.revoked_at = now
        raw_key, api_key = self._issue_key(client, name="rotated")
        await self._audit(
            actor,
            "api_key_rotated",
            client.id,
            None,
            {"key_prefix": api_key.key_prefix, "revoke_others": revoke_others},
            merchant_id=client.merchant_id,
        )
        await self._session.commit()
        logger.info(
            "api_key_rotated",
            client_id=str(client.id),
            client_public_id=client.public_id,
            key_prefix=api_key.key_prefix,
        )
        return client, raw_key

    async def revoke_key(self, actor: User, client_id: uuid.UUID, key_id: uuid.UUID) -> IntegrationClient:
        await self._require_admin(actor, "api_keys:revoke")
        client = await self.get_client(actor, client_id)
        target = next((key for key in client.api_keys if key.id == key_id), None)
        if target is None:
            raise IntegrationNotFoundError("API key not found")
        target.is_active = False
        target.revoked_at = datetime.now(UTC)
        await self._audit(
            actor,
            "api_key_revoked",
            client.id,
            None,
            {"key_prefix": target.key_prefix},
            merchant_id=client.merchant_id,
        )
        await self._session.commit()
        logger.info(
            "api_key_revoked",
            client_id=str(client.id),
            client_public_id=client.public_id,
            key_prefix=target.key_prefix,
        )
        return client

    async def revoke_client(self, actor: User, client_id: uuid.UUID) -> IntegrationClient:
        await self._require_admin(actor, "api_keys:revoke")
        client = await self.get_client(actor, client_id)
        now = datetime.now(UTC)
        client.status = APIClientStatus.REVOKED
        client.revoked_at = now
        for key in client.api_keys:
            key.is_active = False
            key.revoked_at = key.revoked_at or now
        await self._audit(
            actor,
            "integration_revoked",
            client.id,
            None,
            {"status": "revoked"},
            merchant_id=client.merchant_id,
        )
        await self._session.commit()
        logger.info("integration_revoked", client_id=str(client.id), client_public_id=client.public_id)
        return client

    async def rotate_webhook_secret(self, actor: User, client_id: uuid.UUID) -> tuple[IntegrationClient, str]:
        await self._require_admin(actor, "api_keys:create")
        client = await self.get_client(actor, client_id)
        client.webhook_secret_version += 1
        secret = derive_webhook_secret(
            self._settings.secret_key, client.id, client.webhook_secret_version
        )
        client.webhook_secret_prefix = webhook_secret_prefix(secret)
        await self._audit(
            actor,
            "webhook_secret_rotated",
            client.id,
            None,
            {"webhook_secret_prefix": client.webhook_secret_prefix},
            merchant_id=client.merchant_id,
        )
        await self._session.commit()
        logger.info("webhook_secret_rotated", client_id=str(client.id), client_public_id=client.public_id)
        return client, secret

    def resolve_pos_context(
        self,
        principal: APIClientPrincipal,
        *,
        branch_id: uuid.UUID | None = None,
        till_id: uuid.UUID | None = None,
        merchant_id: uuid.UUID | None = None,
    ) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
        """Derive merchant/branch/till from the authenticated client.

        Client-supplied identifiers are accepted only as a consistency check.
        """

        client = principal.client
        if merchant_id is not None and merchant_id != client.merchant_id:
            raise IntegrationAPIError("invalid_till", "Merchant is outside client scope")
        resolved_branch = client.branch_id or branch_id
        resolved_till = client.till_id or till_id
        if client.branch_id is not None and branch_id is not None and branch_id != client.branch_id:
            raise IntegrationAPIError("invalid_till", "Branch is outside client scope")
        if client.till_id is not None and till_id is not None and till_id != client.till_id:
            raise IntegrationAPIError("invalid_till", "Till is outside client scope")
        if resolved_branch is None or resolved_till is None:
            raise IntegrationAPIError(
                "invalid_till",
                "Till context is required for this client",
            )
        return client.merchant_id, resolved_branch, resolved_till

    def require_scope(self, principal: APIClientPrincipal, required: frozenset[str] | str) -> None:
        if not principal.has_scope(required):
            raise IntegrationAPIError("insufficient_scope", "Insufficient scope")

    def _issue_key(self, client: IntegrationClient, *, name: str) -> tuple[str, APIKey]:
        raw = generate_api_key(client.environment)
        record = APIKey(
            merchant_id=client.merchant_id,
            client_id=client.id,
            name=name,
            key_prefix=key_prefix(raw),
            hashed_key=hash_secret(self._settings.secret_key, raw),
            scopes=list(client.scopes or []),
            is_active=True,
        )
        self._session.add(record)
        return raw, record

    async def _validate_context(
        self,
        actor: User,
        merchant_id: uuid.UUID,
        branch_id: uuid.UUID | None,
        till_id: uuid.UUID | None,
        *,
        client_type: APIClientType,
    ) -> tuple[Merchant, Branch | None, Till | None]:
        if not await self._is_platform_admin(actor):
            if actor.merchant_id != merchant_id:
                raise IntegrationForbiddenError("Resource is outside actor scope")
            if actor.branch_id is not None and branch_id is not None and actor.branch_id != branch_id:
                raise IntegrationForbiddenError("Resource is outside actor scope")
        merchant = await self._session.get(Merchant, merchant_id)
        if merchant is None or merchant.deleted_at is not None or not merchant.is_active:
            raise IntegrationInvalidError("Merchant is unavailable")
        branch = None
        till = None
        if branch_id is not None:
            branch = await self._session.get(Branch, branch_id)
            if (
                branch is None
                or branch.deleted_at is not None
                or not branch.is_active
                or branch.merchant_id != merchant.id
            ):
                raise IntegrationInvalidError("Branch is unavailable")
        if till_id is not None:
            till = await self._session.get(Till, till_id)
            if till is None or till.deleted_at is not None or not till.is_active:
                raise IntegrationInvalidError("Till is unavailable")
            if branch is None:
                branch = await self._session.get(Branch, till.branch_id)
            if branch is None or till.branch_id != branch.id or branch.merchant_id != merchant.id:
                raise IntegrationInvalidError("Till is unavailable")
        if client_type is APIClientType.MERCHANT_POS and (branch is None or till is None):
            raise IntegrationInvalidError("POS clients must be bound to merchant, branch, and till")
        return merchant, branch, till

    def _parse_client_type(self, value: str) -> APIClientType:
        try:
            return APIClientType(value)
        except ValueError as exc:
            raise IntegrationInvalidError("Invalid client type") from exc

    def _parse_environment(self, value: str) -> APIClientEnvironment:
        try:
            return APIClientEnvironment(value)
        except ValueError as exc:
            raise IntegrationInvalidError("Invalid environment") from exc

    def _normalize_webhook_url(self, value: str | None, *, allow_empty: bool = False) -> str | None:
        if value is None or not str(value).strip():
            if allow_empty:
                return None
            return None
        url = str(value).strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise IntegrationInvalidError("Webhook URL must be an absolute http(s) URL")
        if parsed.scheme == "http" and self._settings.app_env.value == "production":
            raise IntegrationInvalidError("Production webhook URLs must use HTTPS")
        return url

    async def _assert_client_scope(self, actor: User, client: IntegrationClient) -> None:
        if await self._is_platform_admin(actor):
            return
        if actor.merchant_id != client.merchant_id:
            raise IntegrationForbiddenError("Resource is outside actor scope")

    async def _is_platform_admin(self, actor: User) -> bool:
        role = await self._authorization.get_user_role(actor)
        return role is not None and role.code == "platform_admin"

    async def _require_admin(self, actor: User, permission: str) -> None:
        if not await self._authorization.has_permission(actor, permission):
            raise IntegrationForbiddenError("Insufficient authority")

    async def _audit(
        self,
        actor: User,
        action: str,
        entity_id: uuid.UUID,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        *,
        merchant_id: uuid.UUID | None,
    ) -> None:
        self._session.add(
            AuditLog(
                created_at=datetime.now(UTC),
                actor_user_id=actor.id,
                api_client_id=entity_id if action.startswith("api_") or action.startswith("integration") else None,
                merchant_id=merchant_id or actor.merchant_id,
                action=action,
                entity_type="integration_client",
                entity_id=str(entity_id),
                before_state=before,
                after_state=after,
            )
        )
