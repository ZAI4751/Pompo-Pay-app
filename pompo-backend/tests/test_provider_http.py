"""Live-provider HTTP infrastructure. Uses a POMPO test protocol, not a real rail."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from app.core.config.base import AppEnvironment
from app.payments.contracts import (
    AUTHORITATIVE_CONTRACTS,
    ProviderHttpContract,
    get_authoritative_mapper,
    has_authoritative_contract,
)
from app.payments.credentials import (
    ProviderEnvironmentError,
    normalize_rail_environment,
    production_rails_permitted,
    resolve_provider_credentials,
)
from app.payments.http import (
    ProviderHttpClient,
    ProviderHttpRequest,
    ProviderTimeouts,
    translate_http_status,
)
from app.payments.live import ContractBoundHttpAdapter, build_live_rail_adapter
from app.payments.providers import (
    ProviderAuthenticationError,
    ProviderCapabilities,
    ProviderDuplicate,
    ProviderInvalidRequest,
    ProviderOutcome,
    ProviderPaymentRequest,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.payments.registry import ProviderRegistry
from app.payments.stubs import UnconfiguredRailAdapter


class PompoTestHttpMapper:
    """Explicit test-only HTTP mapping. This is not Airtel, TNM, or a bank."""

    contract = ProviderHttpContract(
        code="test_rail",
        rail_environment="sandbox",
        source="tests/test_provider_http.py",
        capabilities=ProviderCapabilities(
            supports_push_payment=True,
            supports_status_query=True,
        ),
        idempotency_header="Idempotency-Key",
        health_path="/health",
    )

    def initiate(self, request: ProviderPaymentRequest, base_url: str, secret: str) -> ProviderHttpRequest:
        return ProviderHttpRequest(
            method="POST",
            url=f"{base_url.rstrip('/')}/payments",
            headers={
                "Authorization": f"Bearer {secret}",
                "Idempotency-Key": request.idempotency_key,
            },
            json_body={
                "reference": request.reference,
                "amount": str(request.amount),
                "currency": request.currency,
                "idempotency_key": request.idempotency_key,
            },
            retry_safe=False,
        )

    def parse_initiate(self, response):
        body = response.json_body
        if not isinstance(body, dict) or "outcome" not in body:
            raise ProviderInvalidRequest("Test protocol response was missing outcome")
        outcome = ProviderOutcome(str(body["outcome"]))
        return _result(outcome, body)

    def status(self, provider_reference: str, base_url: str, secret: str) -> ProviderHttpRequest:
        return ProviderHttpRequest(
            method="GET",
            url=f"{base_url.rstrip('/')}/payments/{provider_reference}",
            headers={"Authorization": f"Bearer {secret}"},
            retry_safe=True,
        )

    def parse_status(self, response):
        return self.parse_initiate(response)

    def health(self, base_url: str, secret: str) -> ProviderHttpRequest:
        return ProviderHttpRequest(
            method="GET",
            url=f"{base_url.rstrip('/')}/health",
            headers={"Authorization": f"Bearer {secret}"},
            retry_safe=True,
        )


def _result(outcome: ProviderOutcome, body: dict):
    from app.payments.providers import ProviderResult

    return ProviderResult(
        outcome=outcome,
        provider_reference=body.get("provider_reference"),
        provider_transaction_id=body.get("provider_transaction_id"),
        correlation_id=body.get("correlation_id"),
        provider_status=outcome.value,
        retryable=outcome is ProviderOutcome.PENDING,
    )


def _payment_request() -> ProviderPaymentRequest:
    return ProviderPaymentRequest(
        reference="POMPO-TEST-1",
        amount=Decimal("10.00"),
        currency="MWK",
        merchant_id="merchant",
        idempotency_key="POMPO-TEST-1",
        rail_environment="sandbox",
    )


def _credential_env(monkeypatch: pytest.MonkeyPatch, *, production: bool = False) -> None:
    monkeypatch.setenv("PROVIDER_TEST_RAIL_BASE_URL", "https://provider.test")
    monkeypatch.setenv("PROVIDER_TEST_RAIL_CREDENTIAL_REF", "TEST_RAIL_SECRET")
    monkeypatch.setenv("TEST_RAIL_SECRET", "test-only-secret-value")
    monkeypatch.setenv(
        "PROVIDER_TEST_RAIL_ENVIRONMENT",
        "production" if production else "sandbox",
    )


def test_authoritative_contract_registry_is_empty() -> None:
    assert AUTHORITATIVE_CONTRACTS == {}
    assert get_authoritative_mapper("airtel_money", "sandbox") is None
    assert has_authoritative_contract("airtel_money") is False
    assert has_authoritative_contract("tnm_mpamba") is False


def test_live_catalog_codes_remain_unconfigured_stubs() -> None:
    adapter = build_live_rail_adapter("airtel_money")
    assert isinstance(adapter, UnconfiguredRailAdapter)
    assert adapter.live_contract_ready is False
    registry = ProviderRegistry()
    assert registry.get("airtel_money").live_contract_ready is False
    assert registry.get("tnm_mpamba").live_contract_ready is False
    assert registry.get("national_bank").live_contract_ready is False


def test_rail_environment_normalization() -> None:
    assert normalize_rail_environment("live") == "production"
    assert normalize_rail_environment("sandbox") == "sandbox"
    assert production_rails_permitted(AppEnvironment.TESTING) is False
    assert production_rails_permitted(AppEnvironment.DEVELOPMENT) is False
    assert production_rails_permitted(AppEnvironment.PRODUCTION) is True


def test_sandbox_credential_resolution_does_not_leak_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _credential_env(monkeypatch)
    credentials = resolve_provider_credentials("test_rail", catalog_environment="sandbox")
    assert credentials.configuration_complete is True
    assert credentials.secret_configured is True
    rendered = repr(credentials)
    assert "test-only-secret-value" not in rendered
    assert credentials.secret() == "test-only-secret-value"


def test_production_credentials_are_blocked_outside_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROVIDER_AIRTEL_MONEY_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("PROVIDER_AIRTEL_MONEY_CREDENTIAL_REF", "AIRTEL_MONEY_CLIENT_SECRET")
    monkeypatch.setenv("AIRTEL_MONEY_CLIENT_SECRET", "must-not-be-used")
    with pytest.raises(ProviderEnvironmentError):
        resolve_provider_credentials(
            "airtel_money",
            catalog_environment="live",
            app_env=AppEnvironment.TESTING,
        )


def test_http_status_translation() -> None:
    assert isinstance(translate_http_status(401), ProviderAuthenticationError)
    assert isinstance(translate_http_status(429), ProviderRateLimited)
    assert isinstance(translate_http_status(409), ProviderDuplicate)
    assert isinstance(translate_http_status(503), ProviderUnavailable)
    assert isinstance(translate_http_status(408), ProviderTimeout)
    assert isinstance(translate_http_status(400), ProviderInvalidRequest)


@pytest.mark.asyncio
async def test_http_client_rejects_retry_safe_unsafe_method() -> None:
    client = ProviderHttpClient()
    with pytest.raises(ProviderInvalidRequest, match="cannot be marked retry-safe"):
        await client.send(
            ProviderHttpRequest(
                method="POST",
                url="https://provider.test/payments",
                retry_safe=True,
            )
        )
    await client.aclose()


@pytest.mark.asyncio
async def test_http_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    class TimeoutTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("read timed out")

    client = ProviderHttpClient(transport=TimeoutTransport(), timeouts=ProviderTimeouts(0.1, 0.1, 0.1, 0.1))
    with pytest.raises(ProviderTimeout):
        await client.send(ProviderHttpRequest(method="GET", url="https://provider.test/health", retry_safe=True))
    await client.aclose()


@pytest.mark.asyncio
async def test_http_connection_failure() -> None:
    class FailTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

    client = ProviderHttpClient(transport=FailTransport())
    with pytest.raises(ProviderUnavailable, match="connection failed"):
        await client.send(ProviderHttpRequest(method="GET", url="https://provider.test/health", retry_safe=True))
    await client.aclose()


@pytest.mark.asyncio
async def test_http_malformed_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json", headers={"content-type": "application/json"})

    client = ProviderHttpClient(transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderInvalidRequest, match="malformed"):
        await client.send(ProviderHttpRequest(method="GET", url="https://provider.test/health", retry_safe=True))
    await client.aclose()


@pytest.mark.asyncio
async def test_http_rate_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "slow down"})

    client = ProviderHttpClient(transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderRateLimited):
        await client.send_or_raise(
            ProviderHttpRequest(method="GET", url="https://provider.test/health", retry_safe=True)
        )
    await client.aclose()


def _adapter(monkeypatch: pytest.MonkeyPatch, handler) -> ContractBoundHttpAdapter:
    _credential_env(monkeypatch)
    client = ProviderHttpClient(transport=httpx.MockTransport(handler))
    return ContractBoundHttpAdapter(
        "test_rail",
        PompoTestHttpMapper(),
        client=client,
        catalog_environment="sandbox",
    )


@pytest.mark.asyncio
async def test_contract_bound_success_and_idempotency_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "outcome": "success",
                "provider_reference": "prov-1",
                "provider_transaction_id": "txn-1",
                "correlation_id": "corr-1",
            },
        )

    adapter = _adapter(monkeypatch, handler)
    assert adapter.live_contract_ready is True
    result = await adapter.initiate_payment(_payment_request())
    assert result.outcome is ProviderOutcome.SUCCESS
    assert result.provider_reference == "prov-1"
    assert result.provider_transaction_id == "txn-1"
    assert captured[0].headers["Idempotency-Key"] == "POMPO-TEST-1"
    assert captured[0].headers["Authorization"] == "Bearer test-only-secret-value"
    await adapter._client.aclose()


@pytest.mark.asyncio
async def test_contract_bound_pending_and_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def pending(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"outcome": "pending", "provider_reference": "prov-p"})

    adapter = _adapter(monkeypatch, pending)
    result = await adapter.initiate_payment(_payment_request())
    assert result.outcome is ProviderOutcome.PENDING
    assert result.retryable is True
    await adapter._client.aclose()

    def rejected(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "rejected"})

    adapter = _adapter(monkeypatch, rejected)
    with pytest.raises(ProviderInvalidRequest):
        await adapter.initiate_payment(_payment_request())
    await adapter._client.aclose()


@pytest.mark.asyncio
async def test_contract_bound_health_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    adapter = _adapter(monkeypatch, handler)
    health = await adapter.health_check()
    assert health.configured is True
    assert health.contract_ready is True
    assert health.reachable is True
    await adapter._client.aclose()


@pytest.mark.asyncio
async def test_unconfigured_live_adapter_is_not_ready() -> None:
    adapter = build_live_rail_adapter("airtel_money")
    health = await adapter.health_check()
    assert health.contract_ready is False
    assert adapter.live_contract_ready is False
    with pytest.raises(ProviderUnavailable):
        await adapter.initiate_payment(_payment_request())
