"""Docker-backed HTTP coverage for the operational payment chain.

Requires PostgreSQL and Redis (conftest `client` / `db_session`).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.password import PasswordHasher
from app.models import (
    PaymentAttempt,
    Permission,
    Role,
    RolePermission,
    Transaction,
    User,
)
from app.payments.catalog import seed_provider_catalog


PERMISSION_CODES = (
    "merchants:create",
    "merchants:read",
    "merchants:delete",
    "branches:create",
    "branches:read",
    "branches:delete",
    "tills:create",
    "tills:read",
    "tills:update",
    "tills:delete",
    "providers:read",
    "providers:update",
    "transactions:create",
    "transactions:read",
    "transactions:update",
    "transactions:cancel",
)


@pytest.fixture
async def platform_admin(db_session: AsyncSession) -> AsyncGenerator[User, None]:
    hasher = PasswordHasher()
    unique = uuid.uuid4().hex[:8]
    role = await db_session.scalar(select(Role).where(Role.code == "platform_admin"))
    if role is None:
        role = Role(code="platform_admin", name="Platform administrator")
        db_session.add(role)
        await db_session.flush()

    for code in PERMISSION_CODES:
        permission = await db_session.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code, description=code)
            db_session.add(permission)
            await db_session.flush()
        grant = await db_session.scalar(
            select(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id,
            )
        )
        if grant is None:
            db_session.add(RolePermission(role_id=role.id, permission_id=permission.id))

    user = User(
        role=role,
        email=f"ops-admin-{unique}@pompo.mw",
        full_name="Ops Admin",
        hashed_password=hasher.hash("correct-horse-battery-staple"),
        is_active=True,
    )
    db_session.add(user)
    await seed_provider_catalog(db_session)
    await db_session.commit()
    yield user

    txn_ids = list(
        await db_session.scalars(select(Transaction.id).where(Transaction.cashier_id == user.id))
    )
    if txn_ids:
        await db_session.execute(
            delete(PaymentAttempt).where(PaymentAttempt.transaction_id.in_(txn_ids))
        )
        await db_session.execute(delete(Transaction).where(Transaction.id.in_(txn_ids)))
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.commit()


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_http_operational_chain_merchant_branch_till_provider_payment(
    client: AsyncClient, platform_admin: User
) -> None:
    token = await _login(client, platform_admin.email)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]

    merchant_response = await client.post(
        "/api/v1/organization/merchants",
        headers=headers,
        json={
            "name": f"Ops Merchant {suffix}",
            "contact_email": f"ops-merchant-{suffix}@example.com",
            "contact_phone": "+265991000000",
        },
    )
    assert merchant_response.status_code == 201, merchant_response.text
    merchant_id = merchant_response.json()["id"]

    branch_response = await client.post(
        f"/api/v1/organization/merchants/{merchant_id}/branches",
        headers=headers,
        json={"name": "Lilongwe"},
    )
    assert branch_response.status_code == 201, branch_response.text
    branch_id = branch_response.json()["id"]

    till_response = await client.post(
        f"/api/v1/organization/branches/{branch_id}/tills",
        headers=headers,
        json={"code": "POS-1", "name": "Counter 1"},
    )
    assert till_response.status_code == 201, till_response.text
    till = till_response.json()
    assert till["merchant_id"] == merchant_id
    till_id = till["id"]

    listed = await client.get(
        f"/api/v1/organization/branches/{branch_id}/tills", headers=headers
    )
    assert listed.status_code == 200
    assert listed.json()[0]["code"] == "POS-1"

    missing = await client.get(
        f"/api/v1/organization/tills/{uuid.uuid4()}", headers=headers
    )
    assert missing.status_code == 404

    providers = await client.get("/api/v1/payments/providers", headers=headers)
    assert providers.status_code == 200, providers.text
    body = providers.json()
    assert {row["code"] for row in body} >= {"simulated"}
    simulated = next(row for row in body if row["code"] == "simulated")
    assert simulated["is_simulated"] is True
    assert simulated["adapter_configured"] is True
    serialized = str(body).lower()
    assert "secret" not in serialized
    assert "credential" not in serialized
    assert "password" not in serialized

    blocked = await client.patch(
        "/api/v1/payments/providers/airtel_money",
        headers=headers,
        json={"is_active": True},
    )
    assert blocked.status_code == 409

    payload = {
        "merchant_id": merchant_id,
        "branch_id": branch_id,
        "till_id": till_id,
        "amount": "25.00",
        "currency": "MWK",
        "payment_method": "mobile_money",
        "provider_code": "simulated",
        "idempotency_key": f"ops-{suffix}",
    }
    payment_response = await client.post("/api/v1/payments", headers=headers, json=payload)
    assert payment_response.status_code == 201, payment_response.text
    payment = payment_response.json()
    replay = await client.post("/api/v1/payments", headers=headers, json=payload)
    assert replay.status_code == 201
    assert replay.json()["id"] == payment["id"]

    processed = await client.post(
        f"/api/v1/payments/{payment['reference']}/process", headers=headers
    )
    assert processed.status_code == 200, processed.text
    assert processed.json()["status"] == "success"
    assert processed.json()["attempts"]

    fetched = await client.get(f"/api/v1/payments/{payment['reference']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["till_id"] == till_id

    await client.delete(f"/api/v1/organization/tills/{till_id}", headers=headers)
    await client.delete(f"/api/v1/organization/branches/{branch_id}", headers=headers)
    await client.delete(f"/api/v1/organization/merchants/{merchant_id}", headers=headers)


@pytest.mark.asyncio
async def test_http_tills_and_providers_require_authentication(client: AsyncClient) -> None:
    till = await client.get(f"/api/v1/organization/tills/{uuid.uuid4()}")
    providers = await client.get("/api/v1/payments/providers")
    assert till.status_code == 401
    assert providers.status_code == 401
