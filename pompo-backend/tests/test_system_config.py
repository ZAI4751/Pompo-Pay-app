"""Authenticated read-only platform configuration."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.base import get_settings
from app.core.security.password import PasswordHasher
from app.models import Role, User
from app.schemas.system import PlatformConfigResponse


@pytest.fixture
async def seeded_user(db_session: AsyncSession) -> AsyncGenerator[User, None]:
    hasher = PasswordHasher()
    unique = __import__("uuid").uuid4().hex[:8]
    role = Role(code=f"settings_cfg_{unique}", name="Settings config tester")
    user = User(
        role=role,
        email=f"settings-config-{unique}@pompo.mw",
        full_name="Settings Config Tester",
        hashed_password=hasher.hash("correct-horse-battery-staple"),
        is_active=True,
    )
    db_session.add_all([role, user])
    await db_session.commit()
    yield user
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.execute(delete(Role).where(Role.id == role.id))
    await db_session.commit()


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_platform_config_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/system/config")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_platform_config_returns_running_settings(
    client: AsyncClient, seeded_user: User
) -> None:
    token = await _login(client, seeded_user.email)
    response = await client.get(
        "/api/v1/system/config",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    settings = get_settings()
    assert body["writable"] is False
    assert body["configuration_source"] == "environment"
    assert body["app_name"] == settings.app_name
    assert body["app_version"] == settings.app_version
    assert body["app_env"] == settings.app_env.value
    assert body["debug"] is settings.debug
    assert body["api_v1_prefix"] == settings.api_v1_prefix
    assert body["allowed_hosts"] == settings.allowed_hosts_list
    assert body["cors_origins"] == settings.cors_origins_list
    assert body["database_pool_size"] == settings.database_pool_size
    assert body["jwt_algorithm"] == settings.jwt_algorithm
    assert body["jwt_access_token_expire_minutes"] == settings.jwt_access_token_expire_minutes
    assert body["jwt_refresh_token_expire_days"] == settings.jwt_refresh_token_expire_days
    assert body["rate_limit_requests"] == settings.rate_limit_requests
    assert body["rate_limit_window_seconds"] == settings.rate_limit_window_seconds
    assert body["rate_limit_auth_failures"] == settings.rate_limit_auth_failures
    assert body["outbound_webhook_timeout_seconds"] == settings.outbound_webhook_timeout_seconds
    assert body["outbound_webhook_max_attempts"] == settings.outbound_webhook_max_attempts
    assert body["log_level"] == settings.log_level
    assert body["log_json"] is settings.log_json


@pytest.mark.asyncio
async def test_platform_config_omits_secrets(client: AsyncClient, seeded_user: User) -> None:
    token = await _login(client, seeded_user.email)
    response = await client.get(
        "/api/v1/system/config",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    serialized = response.text.lower()
    for name in PlatformConfigResponse.secret_field_names():
        assert name.lower() not in serialized
    assert "postgres" not in serialized
    assert "redis://" not in serialized
    assert "change-me" not in serialized


@pytest.mark.asyncio
async def test_platform_config_rejects_writes(client: AsyncClient, seeded_user: User) -> None:
    token = await _login(client, seeded_user.email)
    headers = {"Authorization": f"Bearer {token}"}
    patch = await client.patch("/api/v1/system/config", headers=headers, json={"debug": True})
    put = await client.put("/api/v1/system/config", headers=headers, json={"debug": True})
    post = await client.post("/api/v1/system/config", headers=headers, json={"debug": True})
    assert patch.status_code == 405
    assert put.status_code == 405
    assert post.status_code == 405
