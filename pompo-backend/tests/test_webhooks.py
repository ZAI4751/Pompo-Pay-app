"""M010 webhook ingestion, deduplication, and payment correlation tests."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
from app.api.v1.webhooks import get_webhook_service, router
from app.models import (
    Branch,
    Merchant,
    PaymentAttempt,
    PaymentProvider,
    Permission,
    Role,
    RolePermission,
    Till,
    Transaction,
    User,
    WebhookEvent,
)
from app.models.base import Base
from app.models.enums import (
    PaymentAttemptStatus,
    ProviderCode,
    TransactionStatus,
    WebhookProcessingStatus,
)
from app.payments.webhooks import compute_mock_signature
from app.services.webhook import WebhookService

WEBHOOK_SECRET = "test-webhook-secret-value"
WEBHOOK_SECRET_ENV = "SIMULATED_WEBHOOK_SECRET"


@pytest.fixture(autouse=True)
def webhook_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER_SIMULATED_WEBHOOK_SECRET_REF", WEBHOOK_SECRET_ENV)
    monkeypatch.setenv(WEBHOOK_SECRET_ENV, WEBHOOK_SECRET)


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


async def _fixture(session: AsyncSession) -> tuple[User, Transaction, PaymentProvider]:
    read_perm = Permission(code="webhooks:read")
    role = Role(code=f"webhook_admin_{uuid.uuid4().hex}", name="Webhook admin")
    role.permissions.append(RolePermission(permission=read_perm))
    merchant = Merchant(
        name="Merchant",
        contact_email=f"{uuid.uuid4().hex}@example.com",
        contact_phone="+265991000000",
    )
    branch = Branch(merchant=merchant, name="Main")
    till = Till(branch=branch, code="T1", name="Counter")
    actor = User(
        merchant=merchant,
        branch=branch,
        role=role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Admin",
        hashed_password="hash",
    )
    provider = PaymentProvider(code=ProviderCode.SIMULATED, display_name="Simulated")
    session.add_all([read_perm, role, merchant, branch, till, actor, provider])
    await session.flush()

    transaction = Transaction(
        merchant_id=merchant.id,
        branch_id=branch.id,
        till_id=till.id,
        cashier_id=actor.id,
        provider_id=provider.id,
        reference=f"PMP-{uuid.uuid4().hex.upper()}",
        idempotency_key=f"order-{uuid.uuid4().hex}",
        request_fingerprint=uuid.uuid4().hex,
        amount=Decimal("100.00"),
        currency="MWK",
        payment_method="mobile_money",
        status=TransactionStatus.PENDING,
    )
    attempt = PaymentAttempt(
        transaction=transaction,
        provider_id=provider.id,
        attempt_number=1,
        status=PaymentAttemptStatus.PENDING,
        provider_reference=f"simulated-{transaction.reference}",
        provider_response={"provider_transaction_id": f"simulated-{transaction.reference}"},
        initiated_at=datetime.now(UTC),
    )
    session.add_all([transaction, attempt])
    await session.commit()
    await session.refresh(transaction, attribute_names=["attempts"])
    return actor, transaction, provider


def _signed_payload(
    *,
    event_id: str,
    event_type: str,
    payment_reference: str,
    outcome: str,
    provider_transaction_id: str | None = None,
) -> tuple[bytes, dict[str, str]]:
    timestamp = str(int(time.time()))
    payload = {
        "event_id": event_id,
        "event_type": event_type,
        "event_version": "1",
        "payment_reference": payment_reference,
        "provider_transaction_id": provider_transaction_id or f"simulated-{payment_reference}",
        "outcome": outcome,
    }
    body = json.dumps(payload).encode()
    signature = compute_mock_signature(WEBHOOK_SECRET, timestamp, body)
    headers = {
        "X-Pompo-Signature": signature,
        "X-Pompo-Timestamp": timestamp,
        "Content-Type": "application/json",
    }
    return body, headers


@pytest.mark.asyncio
async def test_webhook_model_unique_provider_event(session: AsyncSession) -> None:
    _, transaction, provider = await _fixture(session)
    first = WebhookEvent(
        public_identifier="WHK-AAA",
        provider_id=provider.id,
        provider_event_id="evt-1",
        event_type="payment.success",
        payload={"event_id": "evt-1"},
        signature_verified=True,
        timestamp_validated=True,
        received_at=datetime.now(UTC),
        transaction_id=transaction.id,
    )
    duplicate = WebhookEvent(
        public_identifier="WHK-BBB",
        provider_id=provider.id,
        provider_event_id="evt-1",
        event_type="payment.success",
        payload={"event_id": "evt-1"},
        signature_verified=True,
        timestamp_validated=True,
        received_at=datetime.now(UTC),
    )
    session.add(first)
    await session.commit()
    session.add(duplicate)
    with pytest.raises(Exception):
        await session.commit()


@pytest.mark.asyncio
async def test_ingest_valid_webhook_updates_payment(session: AsyncSession) -> None:
    _, transaction, _ = await _fixture(session)
    service = WebhookService(session, sync_processing=True)
    body, headers = _signed_payload(
        event_id="evt-success-1",
        event_type="payment.success",
        payment_reference=transaction.reference,
        outcome="success",
    )
    event = await service.ingest("simulated", headers=headers, body=body)
    await session.refresh(transaction)
    assert event.processing_status is WebhookProcessingStatus.PROCESSED
    assert transaction.status is TransactionStatus.SUCCESS


@pytest.mark.asyncio
async def test_duplicate_webhook_has_no_duplicate_financial_effect(session: AsyncSession) -> None:
    _, transaction, _ = await _fixture(session)
    service = WebhookService(session, sync_processing=True)
    body, headers = _signed_payload(
        event_id="evt-dup-1",
        event_type="payment.success",
        payment_reference=transaction.reference,
        outcome="success",
    )
    await service.ingest("simulated", headers=headers, body=body)
    await session.refresh(transaction)
    assert transaction.status is TransactionStatus.SUCCESS

    from app.services.webhook import WebhookDuplicateError

    with pytest.raises(WebhookDuplicateError):
        await service.ingest("simulated", headers=headers, body=body)
    await session.refresh(transaction)
    assert transaction.status is TransactionStatus.SUCCESS


@pytest.mark.asyncio
async def test_invalid_signature_rejected(session: AsyncSession) -> None:
    _, transaction, _ = await _fixture(session)
    service = WebhookService(session, sync_processing=True)
    body, headers = _signed_payload(
        event_id="evt-bad-sig",
        event_type="payment.success",
        payment_reference=transaction.reference,
        outcome="success",
    )
    headers["X-Pompo-Signature"] = "sha256=deadbeef"
    from app.services.webhook import WebhookSignatureError

    with pytest.raises(WebhookSignatureError):
        await service.ingest("simulated", headers=headers, body=body)
    await session.refresh(transaction)
    assert transaction.status is TransactionStatus.PENDING


@pytest.mark.asyncio
async def test_malformed_payload_rejected(session: AsyncSession) -> None:
    service = WebhookService(session, sync_processing=True)
    timestamp = str(int(time.time()))
    body = b"{not-json"
    signature = compute_mock_signature(WEBHOOK_SECRET, timestamp, body)
    headers = {"X-Pompo-Signature": signature, "X-Pompo-Timestamp": timestamp}
    from app.services.webhook import WebhookInvalidError

    with pytest.raises(WebhookInvalidError):
        await service.ingest("simulated", headers=headers, body=body)


@pytest.mark.asyncio
async def test_unknown_provider_rejected(session: AsyncSession) -> None:
    service = WebhookService(session, sync_processing=True)
    from app.services.webhook import WebhookInvalidError

    with pytest.raises(WebhookInvalidError):
        await service.ingest("unknown_provider", headers={}, body=b"{}")


@pytest.mark.asyncio
async def test_late_success_after_terminal_failure_routes_to_reconciliation(
    session: AsyncSession,
) -> None:
    _, transaction, _ = await _fixture(session)
    transaction.status = TransactionStatus.FAILED
    transaction.completed_at = datetime.now(UTC)
    await session.commit()

    service = WebhookService(session, sync_processing=True)
    body, headers = _signed_payload(
        event_id="evt-late-success",
        event_type="payment.success",
        payment_reference=transaction.reference,
        outcome="success",
    )
    event = await service.ingest("simulated", headers=headers, body=body)
    await session.refresh(transaction)
    assert event.processing_status is WebhookProcessingStatus.RECONCILIATION
    assert transaction.status is TransactionStatus.FAILED


@pytest.mark.asyncio
async def test_timeout_result_webhook(session: AsyncSession) -> None:
    _, transaction, _ = await _fixture(session)
    transaction.status = TransactionStatus.PROCESSING
    await session.commit()

    service = WebhookService(session, sync_processing=True)
    body, headers = _signed_payload(
        event_id="evt-timeout",
        event_type="payment.timeout",
        payment_reference=transaction.reference,
        outcome="timeout",
    )
    event = await service.ingest("simulated", headers=headers, body=body)
    await session.refresh(transaction)
    assert event.processing_status is WebhookProcessingStatus.PROCESSED
    assert transaction.status is TransactionStatus.TIMEOUT


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_admin_api_lists_webhook_events(session: AsyncSession) -> None:
    actor, transaction, _ = await _fixture(session)
    service = WebhookService(session, sync_processing=True)
    body, headers = _signed_payload(
        event_id="evt-admin-list",
        event_type="payment.success",
        payment_reference=transaction.reference,
        outcome="success",
    )
    await service.ingest("simulated", headers=headers, body=body)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def override_user() -> User:
        return actor

    async def override_session():
        yield session

    app.dependency_overrides[deps.get_current_user] = override_user
    app.dependency_overrides[deps.get_db_session] = override_session
    app.dependency_overrides[get_webhook_service] = lambda: WebhookService(session, sync_processing=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/webhooks")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["payment_reference"] == transaction.reference


@pytest.mark.asyncio
async def test_http_ingest_endpoint_acknowledges_duplicate(session: AsyncSession) -> None:
    _, transaction, _ = await _fixture(session)
    body, headers = _signed_payload(
        event_id="evt-http-dup",
        event_type="payment.success",
        payment_reference=transaction.reference,
        outcome="success",
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_webhook_service] = lambda: WebhookService(session, sync_processing=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/api/v1/webhooks/simulated", content=body, headers=headers)
        second = await client.post("/api/v1/webhooks/simulated", content=body, headers=headers)
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["duplicate"] is True
