"""HTTP-level tests for /api/v1/auth/* endpoints.

Unlike tests/test_auth_service.py (SQLite, no external services), these use
the project's existing `client` / `db_session` fixtures from conftest.py,
which require a live PostgreSQL instance (and Redis, for the rate-limit
middleware) — the same requirement tests/test_database.py already has. They
verify HTTP status codes, response schemas, and header handling that the
service-layer tests can't reach (those live in app/api/v1/auth.py and
app/api/deps.py, not in AuthService).

NOTE: these were written against the running application but could not be
executed in the sandbox this milestone was built in — there is no reachable
PostgreSQL/Redis instance here. Run them with `docker compose up -d && pytest
tests/test_auth_api.py -v` before relying on this file.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import pytest

from app.core.security.password import PasswordHasher
from app.models import Role, User


@pytest.fixture
async def seeded_user(db_session: AsyncSession) -> AsyncGenerator[User, None]:
    """Create a user for this test only, and clean it up afterward.

    Uses a unique role code/email per test run (rather than a fixed
    literal) and deletes both rows on teardown — this fixture writes to the
    real, persistent `pompo_test` database (not an in-memory DB, unlike
    tests/test_auth_service.py), so without this the second test run would
    violate `roles.code`'s unique constraint against data left over from
    the first.
    """
    import uuid

    from sqlalchemy import delete

    hasher = PasswordHasher()
    unique = uuid.uuid4().hex[:8]
    role = Role(code=f"cashier_api_test_{unique}", name="Cashier")
    user = User(
        role=role,
        email=f"api-test-{unique}@chikondi.mw",
        full_name="API Test User",
        hashed_password=hasher.hash("correct-horse-battery-staple"),
        is_active=True,
    )
    db_session.add_all([role, user])
    await db_session.commit()

    yield user

    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.execute(delete(Role).where(Role.id == role.id))
    await db_session.commit()


@pytest.mark.asyncio
async def test_login_returns_token_pair(client: AsyncClient, seeded_user: User) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert "hashed_password" not in response.text


@pytest.mark.asyncio
async def test_login_with_wrong_password_returns_generic_401(
    client: AsyncClient, seeded_user: User
) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_with_unknown_email_returns_same_generic_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@chikondi.mw", "password": "whatever"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_malformed_authorization_header_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "NotBearer somejunk"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_token_returns_user(client: AsyncClient, seeded_user: User) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "correct-horse-battery-staple"},
    )
    access_token = login_response.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == seeded_user.email


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(client: AsyncClient, seeded_user: User) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "correct-horse-battery-staple"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert response.json()["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_refresh_replay_returns_401(client: AsyncClient, seeded_user: User) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "correct-horse-battery-staple"},
    )
    refresh_token = login_response.json()["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first.status_code == 200

    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_logout_then_refresh_fails(client: AsyncClient, seeded_user: User) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "correct-horse-battery-staple"},
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout_response.status_code == 204

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 401
