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
from app.middleware.exception_handler import register_exception_handlers
from app.models import Base, Role, User
from app.services.auth import AuthService
from app.services.customer import CustomerService
from tests.test_m015_customer_product import _seed_customer_role

SENTINEL_PASSWORD = "sentinel-value-must-not-be-echoed"


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


def _registration_app(session: AsyncSession) -> FastAPI:
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(customers_router, prefix="/api/v1")
    application.include_router(auth_router, prefix="/api/v1")
    hasher = PasswordHasher()
    jwt_config = _jwt()
    customer_service = CustomerService(session, jwt_config=jwt_config, password_hasher=hasher)
    auth_service = AuthService(session, jwt_config=jwt_config, password_hasher=hasher)
    application.dependency_overrides[get_customer_service] = lambda: customer_service
    application.dependency_overrides[get_auth_service] = lambda: auth_service
    return application


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "email": f"m015-{uuid.uuid4().hex[:10]}@chikondi.mw",
        "password": "correct-horse-battery",
        "full_name": "M015 Customer",
        "phone": f"+26599{uuid.uuid4().hex[:7]}",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_customer_register_login_and_duplicate(session: AsyncSession) -> None:
    await _seed_customer_role(session)
    assert await session.scalar(select(Role).where(Role.code == "customer")) is not None

    application = _registration_app(session)
    payload = _valid_payload()
    email = str(payload["email"])
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/customers/register", json=payload)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["role_code"] == "customer"
        assert body["phone_verification"] == "not_configured"
        assert body["is_email_verified"] is False
        assert body["email_verification"] == "not_configured"
        assert body["email"] == email
        assert body["full_name"] == "M015 Customer"
        assert "hashed_password" not in response.text
        assert SENTINEL_PASSWORD not in response.text

        created = await session.scalar(select(User).where(User.email == email))
        assert created is not None
        assert created.is_email_verified is False
        assert created.email_verified_at is None
        assert created.hashed_password != payload["password"]

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "correct-horse-battery"},
        )
        assert login.status_code == 200, login.text
        assert login.json()["is_email_verified"] is False

        duplicate = await client.post(
            "/api/v1/customers/register",
            json={
                "email": email,
                "password": "another-password",
                "full_name": "Someone Else",
            },
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"] == "An account with these details already exists"

        verify_request = await client.post(
            "/api/v1/auth/verify-email/request",
            json={"email": email},
        )
        assert verify_request.status_code == 200, verify_request.text
        verify_body = verify_request.json()
        assert verify_body["email_delivery"] == "not_configured"
        assert created.is_email_verified is False


@pytest.mark.asyncio
async def test_customer_register_invalid_email(session: AsyncSession) -> None:
    await _seed_customer_role(session)
    application = _registration_app(session)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/customers/register",
            json=_valid_payload(email="not-an-email"),
        )
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Email address is invalid"
    assert SENTINEL_PASSWORD not in response.text
    assert any(error["loc"][-1] == "email" for error in body["errors"])


@pytest.mark.asyncio
async def test_customer_register_invalid_password(session: AsyncSession) -> None:
    await _seed_customer_role(session)
    application = _registration_app(session)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/customers/register",
            json=_valid_payload(password="abcde"),
        )
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Password does not meet requirements"
    assert "abcde" not in response.text
    assert any(error["loc"][-1] == "password" for error in body["errors"])


@pytest.mark.asyncio
async def test_customer_register_missing_required_field(session: AsyncSession) -> None:
    await _seed_customer_role(session)
    application = _registration_app(session)
    transport = ASGITransport(app=application)
    payload = _valid_payload()
    del payload["full_name"]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/customers/register", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Full name is required"
    assert any(error["type"] == "missing" for error in body["errors"])


@pytest.mark.asyncio
async def test_customer_register_without_phone_creates_unverified_account(
    session: AsyncSession,
) -> None:
    await _seed_customer_role(session)
    application = _registration_app(session)
    payload = _valid_payload()
    del payload["phone"]
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/customers/register", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["phone"] is None
    assert body["is_email_verified"] is False
    assert body["email_verification"] == "not_configured"
    assert body["access_token"]
    assert body["refresh_token"]
