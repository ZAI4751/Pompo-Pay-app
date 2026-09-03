"""TNM Mpamba Malawi adapter — contract-dependency tests.

These tests must not call TNM's network and must not invent HTTP paths.
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
from app.payments.tnm_mpamba import (
    CONTRACT_MISSING,
    CONTRACT_SOURCE,
    TNM_CAPABILITIES,
    TnmMpambaMalawiAdapter,
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
        reference="PMP-TNM-1",
        amount=Decimal("250.00"),
        currency="MWK",
        merchant_id="merchant",
        customer_phone="+265888000000",
        idempotency_key="PMP-TNM-1",
        rail_environment="sandbox",
    )


def test_tnm_http_contract_is_not_registered() -> None:
    assert has_authoritative_contract("tnm_mpamba") is False
    assert get_authoritative_mapper("tnm_mpamba", "sandbox") is None
    assert get_authoritative_mapper("tnm_mpamba", "production") is None
    assert CONTRACT_SOURCE.endswith("tnm-mpamba-malawi.md")


def test_registry_exposes_tnm_without_making_it_the_default() -> None:
    registry = ProviderRegistry()
    codes = [adapter.code for adapter in registry.list()]
    assert codes[0] == "simulated"
    assert "tnm_mpamba" in codes
    adapter = registry.get("tnm_mpamba")
    assert isinstance(adapter, TnmMpambaMalawiAdapter)
    assert adapter.live_contract_ready is False
    assert adapter.capabilities == TNM_CAPABILITIES
    assert adapter.capabilities.supports_push_payment is False
    assert adapter.capabilities.supports_webhooks is False
    assert adapter.capabilities.supports_payment_instruments is False
    assert registry.get("airtel_money").code == "airtel_money"
    assert registry.get("simulated").live_contract_ready is True


def test_credentials_do_not_make_tnm_live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER_TNM_MPAMBA_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("PROVIDER_TNM_MPAMBA_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("PROVIDER_TNM_MPAMBA_CLIENT_ID", "client-id")
    monkeypatch.setenv("PROVIDER_TNM_MPAMBA_CREDENTIAL_REF", "TNM_MPAMBA_CLIENT_SECRET")
    monkeypatch.setenv("TNM_MPAMBA_CLIENT_SECRET", "must-never-be-logged")
    adapter = build_live_rail_adapter("tnm_mpamba")
    assert isinstance(adapter, TnmMpambaMalawiAdapter)
    assert adapter.live_contract_ready is False


@pytest.mark.asyncio
async def test_initiate_and_status_are_blocked_without_http() -> None:
    adapter = TnmMpambaMalawiAdapter()
    with pytest.raises(UnsupportedProviderOperation, match="initiate"):
        await adapter.initiate_payment(_request())
    with pytest.raises(UnsupportedProviderOperation, match="status_query"):
        await adapter.get_payment_status("PMP-TNM-1")
    with pytest.raises(UnsupportedProviderOperation, match="cancel"):
        await adapter.cancel_payment("PMP-TNM-1")
    with pytest.raises(UnsupportedProviderOperation, match="refund"):
        await adapter.refund_payment("PMP-TNM-1", Decimal("10.00"))


@pytest.mark.asyncio
async def test_health_does_not_probe_and_reports_missing_contract() -> None:
    adapter = TnmMpambaMalawiAdapter()
    health = await adapter.health_check()
    assert health.contract_ready is False
    assert health.supports_health_check is False
    assert health.reachable is None
    assert health.message == CONTRACT_MISSING


@pytest.mark.asyncio
async def test_webhook_fail_closes_without_invented_signature() -> None:
    adapter = TnmMpambaMalawiAdapter()
    credentials = resolve_provider_credentials("tnm_mpamba")
    result = await adapter.verify_webhook(
        headers={"x-pompo-signature": "sha256=deadbeef"},
        body=b'{"status":"SUCCESS","pin":"0000","token":"secret"}',
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
    monkeypatch.setenv("PROVIDER_TNM_MPAMBA_CREDENTIAL_REF", "TNM_MPAMBA_CLIENT_SECRET")
    monkeypatch.setenv("TNM_MPAMBA_CLIENT_SECRET", "super-secret-tnm-value")
    adapter = TnmMpambaMalawiAdapter()
    with caplog.at_level("INFO"):
        with pytest.raises(UnsupportedProviderOperation):
            await adapter.initiate_payment(_request())
    blob = f"{caplog.text} {capsys.readouterr().out}"
    assert "tnm_payment_blocked" in blob
    assert "super-secret-tnm-value" not in blob
    assert "0000" not in blob


def test_build_live_rail_prefers_named_tnm_adapter() -> None:
    adapter = build_live_rail_adapter("tnm_mpamba")
    assert isinstance(adapter, TnmMpambaMalawiAdapter)
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
            "tnm_mpamba",
            headers={"x-pompo-signature": "sha256=deadbeef"},
            body=b'{"status":"SUCCESS","pin":"0000"}',
        )
    events = list((await session.scalars(select(WebhookEvent))).all())
    assert events == []

