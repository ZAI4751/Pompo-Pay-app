"""Standard Bank Malawi adapter — contract-dependency tests.

These tests must not call Standard Bank or N-Genius networks and must not
invent HTTP paths, PAN, or CVV handling.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.payments.contracts import get_authoritative_mapper, has_authoritative_contract
from app.payments.credentials import resolve_provider_credentials
from app.payments.live import build_live_rail_adapter
from app.payments.providers import (
    ProviderPaymentRequest,
    UnsupportedProviderOperation,
)
from app.payments.registry import ProviderRegistry
from app.payments.standard_bank import (
    CONTRACT_MISSING,
    CONTRACT_SOURCE,
    STANDARD_BANK_CAPABILITIES,
    StandardBankMalawiAdapter,
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


def _request() -> ProviderPaymentRequest:
    return ProviderPaymentRequest(
        reference="PMP-SB-1",
        amount=Decimal("250.00"),
        currency="MWK",
        merchant_id="merchant",
        customer_phone="+265888000000",
        idempotency_key="PMP-SB-1",
        rail_environment="sandbox",
    )


def test_standard_bank_http_contract_is_not_registered() -> None:
    assert has_authoritative_contract("standard_bank") is False
    assert get_authoritative_mapper("standard_bank", "sandbox") is None
    assert get_authoritative_mapper("standard_bank", "production") is None
    assert CONTRACT_SOURCE.endswith("standard-bank-malawi.md")


def test_registry_exposes_standard_bank_without_making_it_the_default() -> None:
    registry = ProviderRegistry()
    codes = [adapter.code for adapter in registry.list()]
    assert codes[0] == "simulated"
    assert "standard_bank" in codes
    adapter = registry.get("standard_bank")
    assert isinstance(adapter, StandardBankMalawiAdapter)
    assert adapter.live_contract_ready is False
    assert adapter.capabilities == STANDARD_BANK_CAPABILITIES
    assert adapter.capabilities.supports_push_payment is False
    assert adapter.capabilities.supports_refund is False
    assert adapter.capabilities.supports_webhooks is False
    assert adapter.capabilities.supports_payment_instruments is False
    assert registry.get("airtel_money").code == "airtel_money"
    assert registry.get("tnm_mpamba").live_contract_ready is False
    assert registry.get("simulated").live_contract_ready is True


def test_credentials_do_not_make_standard_bank_live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER_STANDARD_BANK_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("PROVIDER_STANDARD_BANK_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("PROVIDER_STANDARD_BANK_CLIENT_ID", "client-id")
    monkeypatch.setenv("PROVIDER_STANDARD_BANK_CREDENTIAL_REF", "STANDARD_BANK_CLIENT_SECRET")
    monkeypatch.setenv("STANDARD_BANK_CLIENT_SECRET", "must-never-be-logged")
    adapter = build_live_rail_adapter("standard_bank")
    assert isinstance(adapter, StandardBankMalawiAdapter)
    assert adapter.live_contract_ready is False


@pytest.mark.asyncio
async def test_initiate_status_refund_are_blocked_without_http() -> None:
    adapter = StandardBankMalawiAdapter()
    with pytest.raises(UnsupportedProviderOperation, match="initiate"):
        await adapter.initiate_payment(_request())
    with pytest.raises(UnsupportedProviderOperation, match="status_query"):
        await adapter.get_payment_status("PMP-SB-1")
    with pytest.raises(UnsupportedProviderOperation, match="cancel"):
        await adapter.cancel_payment("PMP-SB-1")
    with pytest.raises(UnsupportedProviderOperation, match="refund"):
        await adapter.refund_payment("PMP-SB-1", Decimal("10.00"))


@pytest.mark.asyncio
async def test_health_does_not_probe_and_reports_missing_contract() -> None:
    adapter = StandardBankMalawiAdapter()
    health = await adapter.health_check()
    assert health.contract_ready is False
    assert health.supports_health_check is False
    assert health.reachable is None
    assert health.message == CONTRACT_MISSING


@pytest.mark.asyncio
async def test_webhook_fail_closes_without_invented_signature() -> None:
    adapter = StandardBankMalawiAdapter()
    credentials = resolve_provider_credentials("standard_bank")
    result = await adapter.verify_webhook(
        headers={"x-pompo-signature": "sha256=deadbeef"},
        body=b'{"status":"SUCCESS","cvv":"123","pan":"4111111111111111"}',
        credentials=credentials,
    )
    assert result.verified is False
    assert "not documented" in (result.failure_reason or "")
    with pytest.raises(ValueError, match="not documented"):
        await adapter.parse_webhook(headers={}, body=b"{}")


@pytest.mark.asyncio
async def test_blocked_initiate_log_does_not_include_secrets(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PROVIDER_STANDARD_BANK_CREDENTIAL_REF", "STANDARD_BANK_CLIENT_SECRET")
    monkeypatch.setenv("STANDARD_BANK_CLIENT_SECRET", "super-secret-sb-value")
    adapter = StandardBankMalawiAdapter()
    with caplog.at_level("INFO"):
        with pytest.raises(UnsupportedProviderOperation):
            await adapter.initiate_payment(_request())
    blob = f"{caplog.text} {capsys.readouterr().out}"
    assert "standard_bank_payment_blocked" in blob
    assert "super-secret-sb-value" not in blob
    assert "4111111111111111" not in blob


def test_build_live_rail_prefers_named_standard_bank_adapter() -> None:
    adapter = build_live_rail_adapter("standard_bank")
    assert isinstance(adapter, StandardBankMalawiAdapter)
    assert adapter.live_contract_ready is False


@pytest.mark.asyncio
async def test_webhook_ingest_does_not_persist_undocumented_callbacks(
    session: AsyncSession,
) -> None:
    from sqlalchemy import select

    from app.models import WebhookEvent
    from app.payments.catalog import seed_provider_catalog
    from app.services.webhook import WebhookService, WebhookSignatureError

    await seed_provider_catalog(session)
    await session.commit()
    service = WebhookService(session, sync_processing=True)
    with pytest.raises(WebhookSignatureError, match="not documented"):
        await service.ingest(
            "standard_bank",
            headers={"x-pompo-signature": "sha256=deadbeef"},
            body=b'{"status":"SUCCESS","cvv":"123"}',
        )
    events = list((await session.scalars(select(WebhookEvent))).all())
    assert events == []
