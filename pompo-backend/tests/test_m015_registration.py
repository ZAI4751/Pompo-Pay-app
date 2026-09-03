"""HTTP registration contract tests (sqlite — no host Postgres required)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_auth_service
from app.api.v1.auth import router as auth_router
from app.api.v1.customers import get_customer_service, router as customers_router
from app.core.security.jwt import JWTConfig
from app.core.security.password import PasswordHasher
import app.models  # noqa: F401 — register ORM tables for sqlite create_all
from app.models import Base, Role
from app.services.auth import AuthService
from app.services.customer import CustomerService
from tests.test_m015_customer_product import _seed_customer_role


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


def _jwt() -> JWTConfig:
    from app.core.config.base import get_settings

    return JWTConfig(get_settings())


@pytest.mark.asyncio
async def test_customer_register_login_and_duplicate(session: AsyncSession) -> None:
    await _seed_customer_role(session)
    assert await session.scalar(select(Role).where(Role.code == "customer")) is not None

    application = FastAPI()
    application.include_router(customers_router, prefix="/api/v1")
    application.include_router(auth_router, prefix="/api/v1")
    hasher = PasswordHasher()
    jwt_config = _jwt()
    customer_service = CustomerService(session, jwt_config=jwt_config, password_hasher=hasher)
    auth_service = AuthService(session, jwt_config=jwt_config, password_hasher=hasher)
    application.dependency_overrides[get_customer_service] = lambda: customer_service
    application.dependency_overrides[get_auth_service] = lambda: auth_service

    email = f"m015-{uuid.uuid4().hex[:10]}@chikondi.mw"
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/customers/register",
            json={
                "email": email,
                "password": "correct-horse-battery",
                "full_name": "M015 Customer",
                "phone": f"+26599{uuid.uuid4().hex[:7]}",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["role_code"] == "customer"
        assert body["phone_verification"] == "not_configured"
        assert "hashed_password" not in response.text

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "correct-horse-battery"},
        )
        assert login.status_code == 200, login.text

        duplicate = await client.post(
            "/api/v1/customers/register",
            json={
                "email": email,
                "password": "another-password",
                "full_name": "Someone Else",
            },
        )
        assert duplicate.status_code == 409

        invalid = await client.post(
            "/api/v1/customers/register",
            json={"email": "not-an-email", "password": "short", "full_name": "X"},
        )
        assert invalid.status_code == 422
