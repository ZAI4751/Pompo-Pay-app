"""Provider catalog seed, registry consistency, and administration."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
from app.api.v1 import providers as providers_api
from app.api.v1.payments import get_provider_catalog_service, router
from app.core.config.base import AppEnvironment
from app.models import Permission, Role, RolePermission, User
from app.models.base import Base
from app.models.enums import ProviderCode
from app.models.payment import PaymentProvider
from app.payments.catalog import (
    PROVIDER_CATALOG,
    ProductionCatalogSeedError,
    ensure_non_production_catalog_seed,
    seed_provider_catalog,
)
from app.payments.registry import ProviderRegistry
from app.services.providers import (
    ProviderCatalogConflictError,
    ProviderCatalogForbiddenError,
    ProviderCatalogInvalidError,
    ProviderCatalogNotFoundError,
    ProviderCatalogService,
)


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


async def _actor(session: AsyncSession, role_code: str, permissions: tuple[str, ...]) -> User:
    code = role_code if role_code == "platform_admin" else f"{role_code}_{uuid.uuid4().hex}"
    role = Role(code=code, name=role_code)
    models = [Permission(code=permission) for permission in permissions]
    role.permissions.extend(RolePermission(permission=permission) for permission in models)
    actor = User(
        role=role,
        email=f"{role_code}-{uuid.uuid4().hex}@example.com",
        full_name=role_code,
        hashed_password="hash",
        is_active=True,
    )
    session.add(actor)
    await session.commit()
    return actor


@pytest.mark.asyncio
async def test_provider_seed_is_idempotent_and_matches_registry_codes(
    session: AsyncSession,
) -> None:
    first = await seed_provider_catalog(session)
    await session.commit()
    second = await seed_provider_catalog(session)
    await session.commit()
    service = ProviderCatalogService(session)
    admin = await _actor(session, "platform_admin", ("providers:read", "providers:update"))
    catalog = await service.list_catalog(admin)

    assert first == len(PROVIDER_CATALOG)
    assert second == 0
    codes = [row.code for row in catalog]
    assert codes == [definition.code for definition in sorted(PROVIDER_CATALOG, key=lambda item: item.priority)]
    simulated = next(row for row in catalog if row.code is ProviderCode.SIMULATED)
    assert simulated.is_active is True
    assert simulated.is_simulated is True
    assert simulated.environment == "sandbox"
    airtel = next(row for row in catalog if row.code is ProviderCode.AIRTEL_MONEY)
    assert airtel.is_active is False
    assert airtel.is_simulated is True
    assert {row.code.value for row in catalog} >= {"simulated"}
    assert "simulated" in service.adapter_codes()
    assert "airtel_money" in service.adapter_codes()
    assert service.adapter_for("airtel_money").live_contract_ready is False


@pytest.mark.asyncio
async def test_cannot_enable_provider_without_live_contract(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    await session.commit()
    admin = await _actor(session, "platform_admin", ("providers:read", "providers:update"))
    service = ProviderCatalogService(session)
    with pytest.raises(ProviderCatalogConflictError):
        await service.update_catalog_entry(admin, "airtel_money", {"is_active": True})


@pytest.mark.asyncio
async def test_platform_admin_can_disable_simulated_provider(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    await session.commit()
    admin = await _actor(session, "platform_admin", ("providers:read", "providers:update"))
    service = ProviderCatalogService(session)
    updated = await service.update_catalog_entry(admin, "simulated", {"is_active": False, "priority": 5})
    assert updated.is_active is False
    assert updated.priority == 5


@pytest.mark.asyncio
async def test_non_admin_cannot_mutate_providers(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    await session.commit()
    owner = await _actor(session, "owner", ("providers:read", "providers:update"))
    service = ProviderCatalogService(session)
    with pytest.raises(ProviderCatalogForbiddenError):
        await service.update_catalog_entry(owner, "simulated", {"is_active": False})
    visible = await service.list_catalog(owner)
    assert visible


@pytest.mark.asyncio
async def test_reader_without_permission_is_forbidden(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    await session.commit()
    actor = await _actor(session, "nobody", ("roles:read",))
    service = ProviderCatalogService(session)
    with pytest.raises(ProviderCatalogForbiddenError):
        await service.list_catalog(actor)


def test_catalog_codes_are_provider_code_values() -> None:
    catalog_codes = {definition.code for definition in PROVIDER_CATALOG}
    assert catalog_codes == set(ProviderCode)
    assert ProviderRegistry().get("simulated").code == "simulated"


def test_sandbox_seed_refuses_production() -> None:
    with pytest.raises(ProductionCatalogSeedError):
        ensure_non_production_catalog_seed(AppEnvironment.PRODUCTION)
    ensure_non_production_catalog_seed(AppEnvironment.DEVELOPMENT)
    ensure_non_production_catalog_seed(AppEnvironment.TESTING)


@pytest.mark.asyncio
async def test_provider_code_uniqueness(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    await session.commit()
    session.add(PaymentProvider(code=ProviderCode.SIMULATED, display_name="Duplicate"))
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_capabilities_prefer_adapter_when_configured(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    await session.commit()
    admin = await _actor(session, "platform_admin", ("providers:read",))
    service = ProviderCatalogService(session)
    simulated = await service.get_catalog_entry(admin, "simulated")
    airtel = await service.get_catalog_entry(admin, "airtel_money")
    assert service.capabilities_for(simulated)["supports_cancel"] is True
    assert service.capabilities_for(airtel)["supports_cancel"] is False
    assert "simulated" in service.adapter_codes()
    assert "airtel_money" in service.adapter_codes()
    assert service.adapter_for("airtel_money").live_contract_ready is False


@pytest.mark.asyncio
async def test_provider_api_returns_401_without_authentication() -> None:
    from fastapi import FastAPI

    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[deps.get_auth_service] = lambda: object()
    application.dependency_overrides[get_provider_catalog_service] = lambda: object()
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/payments/providers")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_provider_api_maps_forbidden_to_403() -> None:
    from fastapi import FastAPI

    class ForbiddenService:
        async def list_catalog(self, _actor: User):
            raise ProviderCatalogForbiddenError("Insufficient authority")

    application = FastAPI()
    application.include_router(router)
    actor = User(email="api@example.com", full_name="API", hashed_password="hash")
    application.dependency_overrides[deps.get_current_user] = lambda: actor
    application.dependency_overrides[get_provider_catalog_service] = lambda: ForbiddenService()
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/payments/providers")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_platform_admin_can_enable_and_disable_simulated(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    await session.commit()
    admin = await _actor(session, "platform_admin", ("providers:read", "providers:update"))
    service = ProviderCatalogService(session)
    disabled = await service.disable_provider(admin, "simulated")
    assert disabled.is_active is False
    assert disabled.health_state.value == "disabled"
    enabled = await service.enable_provider(admin, "simulated")
    assert enabled.is_active is True
    assert enabled.health_state.value == "active"
    with pytest.raises(ProviderCatalogConflictError, match="outside production"):
        await service.update_catalog_entry(admin, "simulated", {"environment": "live"})
    await service.update_catalog_entry(admin, "simulated", {"is_active": False, "environment": "live"})
    with pytest.raises(ProviderCatalogConflictError, match="outside production"):
        await service.enable_provider(admin, "simulated")


@pytest.mark.asyncio
async def test_create_provider_rejects_unknown_and_duplicate(session: AsyncSession) -> None:
    await seed_provider_catalog(session)
    await session.commit()
    admin = await _actor(
        session, "platform_admin", ("providers:read", "providers:create", "providers:update")
    )
    service = ProviderCatalogService(session)
    with pytest.raises(ProviderCatalogInvalidError):
        await service.create_catalog_entry(
            admin, {"code": "not_a_rail", "display_name": "Nope"}
        )
    with pytest.raises(ProviderCatalogConflictError):
        await service.create_catalog_entry(
            admin, {"code": "simulated", "display_name": "Again"}
        )


@pytest.mark.asyncio
async def test_provider_management_api_status_codes() -> None:
    from fastapi import FastAPI

    class NotFoundService:
        async def get_catalog_entry(self, _actor: User, _code: str):
            raise ProviderCatalogNotFoundError("Provider not found")

        async def create_catalog_entry(self, _actor: User, _values: dict):
            raise ProviderCatalogConflictError("Provider already exists")

        async def update_catalog_entry(self, _actor: User, _code: str, _values: dict):
            raise ProviderCatalogInvalidError("Unknown provider type")

    application = FastAPI()
    application.include_router(providers_api.router)
    actor = User(email="api@example.com", full_name="API", hashed_password="hash")
    application.dependency_overrides[deps.get_current_user] = lambda: actor
    application.dependency_overrides[providers_api.get_provider_catalog_service] = (
        lambda: NotFoundService()
    )
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        missing = await client.get("/providers/missing")
        duplicate = await client.post(
            "/providers", json={"code": "simulated", "display_name": "Simulated"}
        )
        invalid = await client.patch("/providers/simulated", json={"display_name": "X"})
    assert missing.status_code == 404
    assert duplicate.status_code == 409
    assert invalid.status_code == 422

    bare = FastAPI()
    bare.include_router(providers_api.router)
    bare.dependency_overrides[deps.get_auth_service] = lambda: object()
    async with AsyncClient(transport=ASGITransport(app=bare), base_url="http://test") as client:
        unauthenticated = await client.get("/providers")
    assert unauthenticated.status_code == 401
