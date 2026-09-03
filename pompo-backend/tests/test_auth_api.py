"""HTTP-level tests for /api/v1/auth/* endpoints.

Unlike tests/test_auth_service.py (SQLite, no external services), these use
the project's existing `client` / `db_session` fixtures from conftest.py,
which require a live PostgreSQL instance (and Redis, for the rate-limit
middleware) — the same requirement tests/test_database.py already has. They
verify HTTP status codes, response schemas, and header handling that the
service-layer tests can't reach (those live in app/api/v1/auth.py and
app/api/deps.py, not in AuthService).

Run them with `docker compose up -d` and either of the two invocations in
docs/testing.md (in-container is authoritative; a locally installed
PostgreSQL on host port 5432 will shadow the container's published port).
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
    body = response.json()
    assert body["email"] == seeded_user.email
    assert "role_code" in body


@pytest.mark.asyncio
async def test_browser_login_flow_carries_cors_headers(
    client: AsyncClient, seeded_user: User
) -> None:
    """Reproduce the admin frontend's exact cross-origin sign-in sequence.

    Regression guard for the defect where the browser could not read the
    backend's responses and the UI reported every failure as "could not reach
    the Pompo backend". Each step must both succeed AND be readable
    cross-origin, so `access-control-allow-origin` is asserted throughout.
    """
    origin = "http://localhost:3000"

    preflight = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin

    login = await client.post(
        "/api/v1/auth/login",
        headers={"Origin": origin},
        json={"email": seeded_user.email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    assert login.headers["access-control-allow-origin"] == origin
    access_token = login.json()["access_token"]

    # A browser preflights /auth/me too, because Authorization is not a
    # CORS-safelisted request header.
    me_preflight = await client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert me_preflight.status_code == 200
    assert me_preflight.headers["access-control-allow-origin"] == origin

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Origin": origin, "Authorization": f"Bearer {access_token}"},
    )
    assert me.status_code == 200
    assert me.headers["access-control-allow-origin"] == origin
    assert me.json()["email"] == seeded_user.email


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


@pytest.mark.asyncio
async def test_change_password_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "x", "new_password": "new-password-123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_rejects_wrong_current_password(
    client: AsyncClient, seeded_user: User
) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "correct-horse-battery-staple"},
    )
    access_token = login_response.json()["access_token"]
    response = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"current_password": "not-the-password", "new_password": "new-password-123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect current password"


@pytest.mark.asyncio
async def test_change_password_revokes_refresh_sessions(
    client: AsyncClient, seeded_user: User
) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "correct-horse-battery-staple"},
    )
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    changed = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": "correct-horse-battery-staple",
            "new_password": "replacement-password-123",
        },
    )
    assert changed.status_code == 204
    assert "password" not in changed.text.lower() or changed.text == ""

    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert replay.status_code == 401

    old_password = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "correct-horse-battery-staple"},
    )
    assert old_password.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "replacement-password-123"},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_logout_all_revokes_refresh_sessions(
    client: AsyncClient, seeded_user: User
) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "correct-horse-battery-staple"},
    )
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    revoked = await client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert revoked.status_code == 204

    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_deactivate_account_revokes_access_and_refresh(
    client: AsyncClient, seeded_user: User
) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "correct-horse-battery-staple"},
    )
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    deactivated = await client.post(
        "/api/v1/auth/deactivate-account",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"current_password": "correct-horse-battery-staple", "confirmation": "DEACTIVATE"},
    )
    assert deactivated.status_code == 204

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 401

    refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh.status_code == 401

    login_again = await client.post(
        "/api/v1/auth/login",
        json={"email": seeded_user.email, "password": "correct-horse-battery-staple"},
    )
    assert login_again.status_code == 403
    assert "deactivated" in login_again.json()["detail"].lower()

