"""M013 POS + developer platform HTTP and security tests."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.password import PasswordHasher
from app.integrations.keys import hash_secret, looks_like_api_key
from app.integrations.scopes import DEFAULT_POS_SCOPES, FORBIDDEN_INTEGRATION_SCOPES, normalize_scopes
from app.models import (
    APIKey,
    IntegrationClient,
    OutboundWebhookDelivery,
    PaymentAttempt,
    Permission,
    Role,
    RolePermission,
    Transaction,
    User,
)
from app.payments.catalog import seed_provider_catalog
from app.payments.webhooks import SIGNATURE_HEADER, TIMESTAMP_HEADER, compute_mock_signature


PERMISSION_CODES = (
    "merchants:create",
    "merchants:read",
    "merchants:delete",
    "branches:create",
    "branches:read",
    "branches:delete",
    "tills:create",
    "tills:read",
    "tills:delete",
    "api_keys:read",
    "api_keys:create",
    "api_keys:revoke",
    "transactions:create",
    "transactions:read",
    "transactions:update",
)


@pytest.fixture
async def platform_admin(db_session: AsyncSession) -> AsyncGenerator[User, None]:
    hasher = PasswordHasher()
    unique = uuid.uuid4().hex[:8]
    role = await db_session.scalar(select(Role).where(Role.code == "platform_admin"))
    if role is None:
        role = Role(code="platform_admin", name="Platform administrator", is_system_role=True)
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
        email=f"int-admin-{unique}@pompo.mw",
        full_name="Integration Admin",
        hashed_password=hasher.hash("correct-horse-battery-staple"),
        is_active=True,
    )
    db_session.add(user)
    await seed_provider_catalog(db_session)
    await db_session.commit()
    user_id = user.id
    yield user
    await db_session.rollback()
    client_ids = list(
        await db_session.scalars(
            select(IntegrationClient.id).where(IntegrationClient.created_by_user_id == user_id)
        )
    )
    if client_ids:
        await db_session.execute(
            delete(OutboundWebhookDelivery).where(OutboundWebhookDelivery.client_id.in_(client_ids))
        )
        txn_ids = list(
            await db_session.scalars(select(Transaction.id).where(Transaction.api_client_id.in_(client_ids)))
        )
        if txn_ids:
            await db_session.execute(delete(PaymentAttempt).where(PaymentAttempt.transaction_id.in_(txn_ids)))
            await db_session.execute(delete(Transaction).where(Transaction.id.in_(txn_ids)))
        await db_session.execute(delete(APIKey).where(APIKey.client_id.in_(client_ids)))
        await db_session.execute(delete(IntegrationClient).where(IntegrationClient.id.in_(client_ids)))
    await db_session.execute(delete(User).where(User.id == user_id))
    await db_session.commit()


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def _merchant_tree(client: AsyncClient, headers: dict[str, str], suffix: str) -> tuple[str, str, str]:
    merchant = await client.post(
        "/api/v1/organization/merchants",
        headers=headers,
        json={
            "name": f"Int Merchant {suffix}",
            "contact_email": f"int-merchant-{suffix}@example.com",
            "contact_phone": "+265991000000",
        },
    )
    assert merchant.status_code == 201, merchant.text
    merchant_id = merchant.json()["id"]
    branch = await client.post(
        f"/api/v1/organization/merchants/{merchant_id}/branches",
        headers=headers,
        json={"name": "Lilongwe"},
    )
    assert branch.status_code == 201, branch.text
    branch_id = branch.json()["id"]
    till = await client.post(
        f"/api/v1/organization/branches/{branch_id}/tills",
        headers=headers,
        json={"code": "POS-INT", "name": "Counter"},
    )
    assert till.status_code == 201, till.text
    return merchant_id, branch_id, till.json()["id"]


def test_scopes_reject_privileged_codes() -> None:
    with pytest.raises(ValueError, match="Forbidden"):
        normalize_scopes(["payments:create", "providers:manage"], default=DEFAULT_POS_SCOPES)
    assert "providers:manage" in FORBIDDEN_INTEGRATION_SCOPES


def test_api_key_format_and_hash_are_not_plaintext() -> None:
    raw = "pompo_test_" + "ab" * 24
    assert looks_like_api_key(raw)
    digest = hash_secret("test-secret-key-minimum-32-characters-long-for-testing", raw)
    assert digest != raw
    assert len(digest) == 64


@pytest.mark.asyncio
async def test_create_client_shows_secret_once_and_never_persists_plaintext(
    client: AsyncClient, platform_admin: User, db_session: AsyncSession
) -> None:
    token = await _login(client, platform_admin.email)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    merchant_id, branch_id, till_id = await _merchant_tree(client, headers, suffix)

    created = await client.post(
        "/api/v1/integrations/clients",
        headers=headers,
        json={
            "name": "Shop POS",
            "client_type": "merchant_pos",
            "environment": "sandbox",
            "merchant_id": merchant_id,
            "branch_id": branch_id,
            "till_id": till_id,
            "webhook_url": "https://pos.example.test/hooks",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    raw_key = body["api_key"]
    webhook_secret = body["webhook_signing_secret"]
    assert raw_key.startswith("pompo_test_")
    assert webhook_secret.startswith("whsec_")
    assert "hashed_key" not in body
    listed = await client.get("/api/v1/integrations/clients", headers=headers)
    assert listed.status_code == 200
    listed_body = listed.json()
    assert raw_key not in json.dumps(listed_body)
    assert webhook_secret not in json.dumps(listed_body)
    stored = await db_session.scalar(select(APIKey).where(APIKey.key_prefix == raw_key[:16]))
    assert stored is not None
    assert stored.hashed_key != raw_key
    assert raw_key not in stored.hashed_key


@pytest.mark.asyncio
async def test_pos_payment_qr_status_idempotency_and_scopes(
    client: AsyncClient, platform_admin: User
) -> None:
    token = await _login(client, platform_admin.email)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    merchant_id, branch_id, till_id = await _merchant_tree(client, headers, suffix)
    created = await client.post(
        "/api/v1/integrations/clients",
        headers=headers,
        json={
            "name": "POS A",
            "client_type": "merchant_pos",
            "merchant_id": merchant_id,
            "branch_id": branch_id,
            "till_id": till_id,
        },
    )
    raw_key = created.json()["api_key"]
    api_headers = {"X-API-Key": raw_key}
    payload = {
        "amount": "50.00",
        "currency": "MWK",
        "payment_method": "mobile_money",
        "idempotency_key": f"pos-{suffix}",
        "generate_qr": True,
    }
    first = await client.post("/api/v1/integrations/payments", headers=api_headers, json=payload)
    assert first.status_code == 201, first.text
    payment = first.json()
    assert payment["qr"]["encoded_payload"].startswith("POMPO:1:dynamic:")
    assert payment["status"] in {"created", "qr_generated"}
    replay = await client.post("/api/v1/integrations/payments", headers=api_headers, json=payload)
    assert replay.status_code == 201
    assert replay.json()["reference"] == payment["reference"]

    conflict = await client.post(
        "/api/v1/integrations/payments",
        headers=api_headers,
        json={**payload, "amount": "75.00"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"

    other = await client.post(
        "/api/v1/integrations/payments",
        headers=api_headers,
        json={**payload, "idempotency_key": f"pos-{suffix}-b", "amount": "60.00"},
    )
    assert other.status_code == 201
    assert other.json()["reference"] != payment["reference"]

    status = await client.get(
        f"/api/v1/integrations/payments/{payment['reference']}", headers=api_headers
    )
    assert status.status_code == 200
    assert status.json()["reference"] == payment["reference"]
    assert "attempts" not in status.json()

    invalid = await client.get("/api/v1/integrations/payments/PMP-MISSING", headers={"X-API-Key": "not-a-key"})
    assert invalid.status_code == 401
    assert invalid.json()["code"] == "invalid_api_key"


@pytest.mark.asyncio
async def test_revoked_expired_and_insufficient_scope(
    client: AsyncClient, platform_admin: User, db_session: AsyncSession
) -> None:
    token = await _login(client, platform_admin.email)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    merchant_id, branch_id, till_id = await _merchant_tree(client, headers, suffix)
    created = await client.post(
        "/api/v1/integrations/clients",
        headers=headers,
        json={
            "name": "Limited",
            "client_type": "developer",
            "merchant_id": merchant_id,
            "branch_id": branch_id,
            "till_id": till_id,
            "scopes": ["payments:read"],
        },
    )
    assert created.status_code == 201, created.text
    raw_key = created.json()["api_key"]
    client_id = created.json()["id"]
    denied = await client.post(
        "/api/v1/integrations/payments",
        headers={"X-API-Key": raw_key},
        json={
            "amount": "10.00",
            "currency": "MWK",
            "payment_method": "mobile_money",
            "idempotency_key": f"denied-{suffix}",
            "generate_qr": False,
        },
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "insufficient_scope"

    rotated = await client.post(
        f"/api/v1/integrations/clients/{client_id}/keys",
        headers=headers,
    )
    assert rotated.status_code == 201
    new_key = rotated.json()["api_key"]
    revoked = await client.post(
        "/api/v1/integrations/payments",
        headers={"X-API-Key": raw_key},
        json={
            "amount": "10.00",
            "currency": "MWK",
            "payment_method": "mobile_money",
            "idempotency_key": f"revoked-{suffix}",
            "generate_qr": False,
        },
    )
    assert revoked.status_code == 401
    assert revoked.json()["code"] == "api_key_revoked"

    await client.post(f"/api/v1/integrations/clients/{client_id}/revoke", headers=headers)
    dead = await client.get(
        "/api/v1/integrations/payments/PMP-X", headers={"X-API-Key": new_key}
    )
    assert dead.status_code == 401


@pytest.mark.asyncio
async def test_merchant_and_till_isolation(client: AsyncClient, platform_admin: User) -> None:
    token = await _login(client, platform_admin.email)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    merchant_a, branch_a, till_a = await _merchant_tree(client, headers, suffix + "a")
    merchant_b, branch_b, till_b = await _merchant_tree(client, headers, suffix + "b")
    client_a = await client.post(
        "/api/v1/integrations/clients",
        headers=headers,
        json={
            "name": "POS A",
            "client_type": "merchant_pos",
            "merchant_id": merchant_a,
            "branch_id": branch_a,
            "till_id": till_a,
        },
    )
    client_b = await client.post(
        "/api/v1/integrations/clients",
        headers=headers,
        json={
            "name": "POS B",
            "client_type": "merchant_pos",
            "merchant_id": merchant_b,
            "branch_id": branch_b,
            "till_id": till_b,
        },
    )
    key_a = client_a.json()["api_key"]
    key_b = client_b.json()["api_key"]
    created = await client.post(
        "/api/v1/integrations/payments",
        headers={"X-API-Key": key_a},
        json={
            "amount": "20.00",
            "currency": "MWK",
            "payment_method": "mobile_money",
            "idempotency_key": f"iso-{suffix}",
            "generate_qr": False,
        },
    )
    assert created.status_code == 201, created.text
    reference = created.json()["reference"]
    foreign = await client.get(
        f"/api/v1/integrations/payments/{reference}", headers={"X-API-Key": key_b}
    )
    assert foreign.status_code == 404
    assert foreign.json()["code"] == "payment_not_found"
    hijack = await client.post(
        "/api/v1/integrations/payments",
        headers={"X-API-Key": key_a},
        json={
            "amount": "20.00",
            "currency": "MWK",
            "payment_method": "mobile_money",
            "idempotency_key": f"hijack-{suffix}",
            "till_id": till_b,
            "merchant_id": merchant_b,
            "generate_qr": False,
        },
    )
    assert hijack.status_code == 422
    assert hijack.json()["code"] == "invalid_till"


@pytest.mark.asyncio
async def test_concurrent_idempotency_one_financial_result(
    client: AsyncClient, platform_admin: User
) -> None:
    token = await _login(client, platform_admin.email)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    merchant_id, branch_id, till_id = await _merchant_tree(client, headers, suffix)
    created = await client.post(
        "/api/v1/integrations/clients",
        headers=headers,
        json={
            "name": "POS concurrent",
            "client_type": "merchant_pos",
            "merchant_id": merchant_id,
            "branch_id": branch_id,
            "till_id": till_id,
        },
    )
    raw_key = created.json()["api_key"]
    payload = {
        "amount": "33.00",
        "currency": "MWK",
        "payment_method": "mobile_money",
        "idempotency_key": f"conc-{suffix}",
        "generate_qr": False,
    }

    async def submit() -> str:
        response = await client.post(
            "/api/v1/integrations/payments", headers={"X-API-Key": raw_key}, json=payload
        )
        assert response.status_code == 201, response.text
        return response.json()["reference"]

    first, second = await asyncio.gather(submit(), submit())
    assert first == second


@pytest.mark.asyncio
async def test_outbound_webhook_signing_delivery_duplicate_and_retry(
    client: AsyncClient, platform_admin: User, db_session: AsyncSession
) -> None:
    token = await _login(client, platform_admin.email)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    merchant_id, branch_id, till_id = await _merchant_tree(client, headers, suffix)
    created = await client.post(
        "/api/v1/integrations/clients",
        headers=headers,
        json={
            "name": "Webhook POS",
            "client_type": "merchant_pos",
            "merchant_id": merchant_id,
            "branch_id": branch_id,
            "till_id": till_id,
            "webhook_url": "https://pos.example.test/hooks",
        },
    )
    raw_key = created.json()["api_key"]
    webhook_secret = created.json()["webhook_signing_secret"]
    client_id = created.json()["id"]
    payment = await client.post(
        "/api/v1/integrations/payments",
        headers={"X-API-Key": raw_key},
        json={
            "amount": "40.00",
            "currency": "MWK",
            "payment_method": "mobile_money",
            "idempotency_key": f"wh-{suffix}",
            "generate_qr": False,
        },
    )
    assert payment.status_code == 201, payment.text
    await db_session.commit()
    delivery = await db_session.scalar(
        select(OutboundWebhookDelivery).where(OutboundWebhookDelivery.client_id == uuid.UUID(client_id))
    )
    assert delivery is not None
    body = json.dumps(delivery.payload, separators=(",", ":"), sort_keys=True).encode()
    timestamp = str(int(time.time()))
    expected = compute_mock_signature(webhook_secret, timestamp, body)
    assert expected.startswith("sha256=")
    tampered = hmac.new(b"other", b"x", hashlib.sha256).hexdigest()
    assert not hmac.compare_digest(expected, f"sha256={tampered}")

    from app.services.outbound_webhook import OutboundWebhookService
    import httpx

    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        assert SIGNATURE_HEADER in {k.lower(): v for k, v in request.headers.items()} or request.headers.get(
            "x-pompo-signature"
        )
        assert request.headers.get(TIMESTAMP_HEADER) or request.headers.get("x-pompo-timestamp")
        if calls["count"] == 1:
            return httpx.Response(503, json={"error": "busy"})
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        service = OutboundWebhookService(db_session, http_client=http)
        with pytest.raises(Exception):
            await service.deliver(delivery.id)
        await db_session.refresh(delivery)
        assert delivery.status.value == "retrying"
        await service.deliver(delivery.id)
        await db_session.refresh(delivery)
        assert delivery.status.value == "sent"

    duplicate = OutboundWebhookDelivery(
        public_event_id=delivery.public_event_id,
        client_id=delivery.client_id,
        transaction_id=delivery.transaction_id,
        event_type=delivery.event_type,
        destination_url=delivery.destination_url,
        payload=delivery.payload,
    )
    db_session.add(duplicate)
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_invalid_destination_fails_without_retry_forever(
    db_session: AsyncSession,
) -> None:
    from app.models import Branch, Merchant, Till
    from app.models.enums import APIClientEnvironment, APIClientStatus, APIClientType
    from app.services.outbound_webhook import OutboundWebhookService

    merchant = Merchant(
        name="Dest Merchant",
        contact_email=f"{uuid.uuid4().hex}@example.com",
        contact_phone="+265991000000",
    )
    branch = Branch(merchant=merchant, name="Main")
    till = Till(branch=branch, code="T1", name="Till")
    client_row = IntegrationClient(
        public_id=f"app_{uuid.uuid4().hex[:8]}",
        name="Bad hook",
        client_type=APIClientType.DEVELOPER,
        environment=APIClientEnvironment.SANDBOX,
        status=APIClientStatus.ACTIVE,
        merchant=merchant,
        branch=branch,
        till=till,
        scopes=["payments:read"],
        webhook_url="not-a-url",
    )
    db_session.add_all([merchant, branch, till, client_row])
    await db_session.commit()
    from app.models.enums import TransactionStatus
    from decimal import Decimal

    txn = Transaction(
        merchant_id=merchant.id,
        branch_id=branch.id,
        till_id=till.id,
        api_client_id=client_row.id,
        reference=f"PMP-{uuid.uuid4().hex[:10].upper()}",
        idempotency_key=f"dest-{uuid.uuid4().hex}",
        request_fingerprint="abc",
        amount=Decimal("1.00"),
        currency="MWK",
        payment_method="mobile_money",
        status=TransactionStatus.SUCCESS,
    )
    db_session.add(txn)
    await db_session.commit()
    from app.models.enums import OutboundWebhookStatus

    delivery = OutboundWebhookDelivery(
        public_event_id=f"evt_{txn.reference}_success",
        client_id=client_row.id,
        transaction_id=txn.id,
        event_type="payment.success",
        destination_url="not-a-url",
        payload={"event_id": "x"},
        status=OutboundWebhookStatus.PENDING,
        max_attempts=2,
    )
    db_session.add(delivery)
    await db_session.commit()
    service = OutboundWebhookService(db_session)
    result = await service.deliver(delivery.id)
    assert result.status.value == "failed"
    assert result.failure_category.value == "invalid_destination"


@pytest.mark.asyncio
async def test_expired_key_invalid_amount_currency_rate_limit_and_openapi(
    client: AsyncClient, platform_admin: User, db_session: AsyncSession
) -> None:
    token = await _login(client, platform_admin.email)
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    merchant_id, branch_id, till_id = await _merchant_tree(client, headers, suffix)
    created = await client.post(
        "/api/v1/integrations/clients",
        headers=headers,
        json={
            "name": "Limited POS",
            "client_type": "merchant_pos",
            "merchant_id": merchant_id,
            "branch_id": branch_id,
            "till_id": till_id,
        },
    )
    assert created.status_code == 201, created.text
    raw_key = created.json()["api_key"]
    api_headers = {"X-API-Key": raw_key}

    limited_client = await client.post(
        "/api/v1/integrations/clients",
        headers=headers,
        json={
            "name": "Rate limited POS",
            "client_type": "merchant_pos",
            "merchant_id": merchant_id,
            "branch_id": branch_id,
            "till_id": till_id,
            "rate_limit_requests": 1,
        },
    )
    assert limited_client.status_code == 201, limited_client.text
    limited_key = limited_client.json()["api_key"]

    bad_amount = await client.post(
        "/api/v1/integrations/payments",
        headers=api_headers,
        json={
            "amount": "0.00",
            "currency": "MWK",
            "payment_method": "mobile_money",
            "idempotency_key": f"zero-{suffix}",
        },
    )
    assert bad_amount.status_code == 422
    assert bad_amount.json()["code"] == "invalid_amount"

    bad_currency = await client.post(
        "/api/v1/integrations/payments",
        headers=api_headers,
        json={
            "amount": "10.00",
            "currency": "USD",
            "payment_method": "mobile_money",
            "idempotency_key": f"usd-{suffix}",
        },
    )
    assert bad_currency.status_code == 422
    assert bad_currency.json()["code"] == "unsupported_currency"

    first = await client.post(
        "/api/v1/integrations/payments",
        headers={"X-API-Key": limited_key},
        json={
            "amount": "12.00",
            "currency": "MWK",
            "payment_method": "mobile_money",
            "idempotency_key": f"rl-{suffix}",
            "generate_qr": False,
        },
    )
    assert first.status_code == 201, first.text
    limited = await client.post(
        "/api/v1/integrations/payments",
        headers={"X-API-Key": limited_key},
        json={
            "amount": "13.00",
            "currency": "MWK",
            "payment_method": "mobile_money",
            "idempotency_key": f"rl2-{suffix}",
            "generate_qr": False,
        },
    )
    assert limited.status_code == 429
    assert limited.json()["code"] == "rate_limited"
    assert "retry-after" in {k.lower() for k in limited.headers}

    stored = await db_session.scalar(select(APIKey).where(APIKey.key_prefix == raw_key[:16]))
    assert stored is not None
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()
    expired = await client.get(
        "/api/v1/integrations/payments/PMP-X", headers={"X-API-Key": raw_key}
    )
    assert expired.status_code == 401
    assert expired.json()["code"] == "api_key_expired"

    from fastapi import FastAPI

    from app.api.v1.router import api_v1_router

    app = FastAPI()
    app.include_router(api_v1_router, prefix="/api/v1")
    spec = app.openapi()
    paths = spec["paths"]
    assert "/api/v1/integrations/payments" in paths
    assert "post" in paths["/api/v1/integrations/payments"]
    assert "/api/v1/integrations/payments/{reference}" in paths
    assert "/api/v1/integrations/clients" in paths
    dumped = json.dumps(spec)
    assert "hashed_key" not in dumped.lower()
    assert "SECRET_KEY" not in dumped
    assert "pompo_live_" + "a" * 24 not in dumped
    assert spec["paths"]["/api/v1/integrations/payments"]["post"].get("tags") == ["Integrations"]
