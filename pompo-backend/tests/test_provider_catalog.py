"""Provider catalog seed, registry consistency, and administration."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
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
    assert "airtel_money" not in service.adapter_codes()


@pytest.mark.asyncio
async def test_cannot_enable_provider_without_adapter(session: AsyncSession) -> None:
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
    assert "airtel_money" not in service.adapter_codes()


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
