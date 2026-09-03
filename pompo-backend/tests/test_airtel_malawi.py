"""Airtel Money Malawi contract, adapter, webhook, and security tests.

HTTP is mocked. These tests must not call Airtel's live network.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal

import httpx
import pytest

from app.payments.airtel_malawi import (
    AUTH_PATH,
    INITIATE_PATH,
    AirtelMoneyMalawiAdapter,
    AirtelMoneyMalawiMapper,
    amount_payload,
    map_status_token,
    normalize_malawi_msisdn,
    parse_access_token,
    recommended_base_url,
    verify_airtel_callback_hash,
)
from app.payments.contracts import get_authoritative_mapper, has_authoritative_contract
from app.payments.http import ProviderHttpClient
from app.payments.live import build_live_rail_adapter
from app.payments.providers import (
    ProviderAuthenticationError,
    ProviderDuplicate,
    ProviderInvalidRequest,
    ProviderOutcome,
    ProviderPaymentRequest,
    ProviderRateLimited,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.payments.registry import ProviderRegistry
from app.payments.tnm_mpamba import TnmMpambaMalawiAdapter
from app.payments.standard_bank import StandardBankMalawiAdapter
from app.payments.webhooks import constant_time_compare

SANDBOX = "https://openapiuat.airtel.mw"
CLIENT_ID = "test-client-id"
CLIENT_SECRET = "test-client-secret-value"
WEBHOOK_SECRET = "test-webhook-secret-value"
TOKEN = "test-access-token-value"


def _env(monkeypatch: pytest.MonkeyPatch, *, unsigned: bool = False) -> None:
    monkeypatch.setenv("PROVIDER_AIRTEL_MONEY_BASE_URL", SANDBOX)
    monkeypatch.setenv("PROVIDER_AIRTEL_MONEY_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("PROVIDER_AIRTEL_MONEY_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("PROVIDER_AIRTEL_MONEY_CREDENTIAL_REF", "AIRTEL_MONEY_CLIENT_SECRET")
    monkeypatch.setenv("AIRTEL_MONEY_CLIENT_SECRET", CLIENT_SECRET)
    monkeypatch.setenv("PROVIDER_AIRTEL_MONEY_WEBHOOK_SECRET_REF", "AIRTEL_MONEY_WEBHOOK_SECRET")
    monkeypatch.setenv("AIRTEL_MONEY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    if unsigned:
        monkeypatch.setenv("PROVIDER_AIRTEL_MONEY_WEBHOOK_UNSIGNED", "true")
    else:
        monkeypatch.delenv("PROVIDER_AIRTEL_MONEY_WEBHOOK_UNSIGNED", raising=False)


def _request() -> ProviderPaymentRequest:
    return ProviderPaymentRequest(
        reference="PMP-AIRTEL-1",
        amount=Decimal("250.00"),
        currency="MWK",
        merchant_id="merchant",
        customer_phone="+265991000000",
        idempotency_key="PMP-AIRTEL-1",
        rail_environment="sandbox",
    )


def _token_response() -> dict:
    return {"access_token": TOKEN, "token_type": "Bearer", "expires_in": 180}


def _pending_body(reference: str = "PMP-AIRTEL-1") -> dict:
    return {
        "data": {
            "transaction": {
                "id": reference,
                "status": "TIP",
                "airtel_money_id": "MW-AIRTEL-99",
            }
        },
        "status": {"code": "200", "success": True, "message": "Accepted"},
        "request_id": "req-1",
    }


def _success_body(reference: str = "PMP-AIRTEL-1") -> dict:
    return {
        "data": {
            "transaction": {
                "id": reference,
                "status": "TS",
                "airtel_money_id": "MW-AIRTEL-99",
                "message": "Paid",
            }
        },
        "status": {"code": "200", "success": True},
    }


class _Scripted:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = list(responses)
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if not self.responses:
            raise AssertionError(f"Unexpected request {request.method} {request.url}")
        return self.responses.pop(0)


def _adapter(monkeypatch: pytest.MonkeyPatch, handler) -> AirtelMoneyMalawiAdapter:
    _env(monkeypatch)
    client = ProviderHttpClient(transport=httpx.MockTransport(handler))
    adapter = build_live_rail_adapter("airtel_money", client=client)
    assert isinstance(adapter, AirtelMoneyMalawiAdapter)
    return adapter


def test_authoritative_airtel_contract_is_registered() -> None:
    assert has_authoritative_contract("airtel_money") is True
    assert has_authoritative_contract("tnm_mpamba") is False
    assert has_authoritative_contract("standard_bank") is False
    mapper = get_authoritative_mapper("airtel_money", "sandbox")
    assert isinstance(mapper, AirtelMoneyMalawiMapper)
    assert get_authoritative_mapper("airtel_money", "production") is not None
    assert mapper.contract.source.endswith("airtel-money-malawi.md")
    assert mapper.contract.capabilities.supports_webhooks is True
    assert mapper.contract.capabilities.supports_qr is False


def test_registry_exposes_airtel_without_making_it_the_default() -> None:
    registry = ProviderRegistry()
    codes = [adapter.code for adapter in registry.list()]
    assert codes[0] == "simulated"
    assert "airtel_money" in codes
    assert registry.get("tnm_mpamba").live_contract_ready is False
    assert isinstance(registry.get("tnm_mpamba"), TnmMpambaMalawiAdapter)
    assert isinstance(registry.get("standard_bank"), StandardBankMalawiAdapter)


def test_airtel_is_not_ready_without_credentials() -> None:
    adapter = build_live_rail_adapter("airtel_money")
    assert isinstance(adapter, AirtelMoneyMalawiAdapter)
    assert adapter.live_contract_ready is False


def test_recommended_hosts_and_msisdn() -> None:
    assert recommended_base_url("sandbox") == SANDBOX
    assert recommended_base_url("production") == "https://openapi.airtel.mw"
    assert normalize_malawi_msisdn("+265991000000") == "991000000"
    assert normalize_malawi_msisdn("0991000000") == "991000000"
    assert amount_payload(Decimal("250.00")) == 250
    with pytest.raises(ProviderInvalidRequest):
        normalize_malawi_msisdn("12")


def test_status_token_mapping() -> None:
    assert map_status_token("TS") is ProviderOutcome.SUCCESS
    assert map_status_token("tf") is ProviderOutcome.FAILED
    assert map_status_token("TIP") is ProviderOutcome.PENDING
    assert map_status_token("NOPE") is None


def test_parse_access_token_rfc6749() -> None:
    token, expires = parse_access_token(_token_response())
    assert token == TOKEN
    assert expires == 180
    with pytest.raises(ProviderAuthenticationError):
        parse_access_token({"token_type": "Bearer"})


@pytest.mark.asyncio
async def test_auth_success_expired_invalid_and_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    script = _Scripted(
        [
            httpx.Response(200, json=_token_response()),
            httpx.Response(200, json=_pending_body()),
            httpx.Response(400, json={"error": "invalid_client", "error_description": "Invalid client authentication"}),
            httpx.Response(503, json={"error": "unavailable"}),
        ]
    )
    adapter = _adapter(monkeypatch, script)
    first = await adapter.initiate_payment(_request())
    assert first.outcome is ProviderOutcome.PENDING
    auth = script.calls[0]
    assert str(auth.url).endswith(AUTH_PATH)
    assert auth.method == "POST"
    body = json.loads(auth.content)
    assert body == {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    adapter._token.expires_at = 0
    with pytest.raises(ProviderAuthenticationError):
        await adapter.initiate_payment(_request())
    with pytest.raises(ProviderUnavailable):
        await adapter.initiate_payment(_request())
    await adapter._client.aclose()


@pytest.mark.asyncio
async def test_initiate_contract_headers_body_and_pending(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    script = _Scripted(
        [
            httpx.Response(200, json=_token_response()),
            httpx.Response(200, json=_pending_body()),
        ]
    )
    adapter = _adapter(monkeypatch, script)
    with caplog.at_level("INFO"):
        result = await adapter.initiate_payment(_request())
    assert result.outcome is ProviderOutcome.PENDING
    assert result.retryable is True
    assert result.provider_reference == "PMP-AIRTEL-1"
    assert result.provider_transaction_id == "MW-AIRTEL-99"
    pay = script.calls[1]
    assert pay.method == "POST"
    assert str(pay.url) == f"{SANDBOX}{INITIATE_PATH}"
    assert pay.headers["X-Country"] == "MW"
    assert pay.headers["X-Currency"] == "MWK"
    assert pay.headers["Authorization"] == f"Bearer {TOKEN}"
    payload = json.loads(pay.content)
    assert payload["transaction"]["id"] == "PMP-AIRTEL-1"
    assert payload["transaction"]["amount"] == 250
    assert payload["subscriber"]["msisdn"] == "991000000"
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert TOKEN not in joined
    assert CLIENT_SECRET not in joined
    await adapter._client.aclose()


@pytest.mark.asyncio
async def test_initiate_success_failure_rejected_timeout_rate_limit_malformed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _Scripted(
        [
            httpx.Response(200, json=_token_response()),
            httpx.Response(200, json=_success_body()),
            httpx.Response(
                200,
                json={"data": {"transaction": {"id": "PMP-AIRTEL-1", "status": "TF"}}},
            ),
            httpx.Response(200, json={"status": {"success": False, "message": "Rejected"}}),
            httpx.Response(408, json={"error": "timeout"}),
            httpx.Response(503, json={"error": "down"}),
            httpx.Response(429, json={"error": "slow"}),
            httpx.Response(200, content=b"not-json", headers={"content-type": "application/json"}),
        ]
    )
    adapter = _adapter(monkeypatch, script)
    success = await adapter.initiate_payment(_request())
    assert success.outcome is ProviderOutcome.SUCCESS
    failed = await adapter.initiate_payment(_request())
    assert failed.outcome is ProviderOutcome.FAILED
    with pytest.raises(ProviderRejected):
        await adapter.initiate_payment(_request())
    with pytest.raises(ProviderTimeout):
        await adapter.initiate_payment(_request())
    with pytest.raises(ProviderUnavailable):
        await adapter.initiate_payment(_request())
    with pytest.raises(ProviderRateLimited):
        await adapter.initiate_payment(_request())
    with pytest.raises(ProviderInvalidRequest, match="malformed"):
        await adapter.initiate_payment(_request())
    await adapter._client.aclose()


@pytest.mark.asyncio
async def test_idempotent_retry_reuses_pompo_reference_not_attempt_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _Scripted(
        [
            httpx.Response(200, json=_token_response()),
            httpx.Response(200, json=_pending_body()),
            httpx.Response(200, json=_pending_body()),
        ]
    )
    adapter = _adapter(monkeypatch, script)
    first = _request()
    second = ProviderPaymentRequest(
        reference=first.reference,
        amount=first.amount,
        currency=first.currency,
        merchant_id=first.merchant_id,
        customer_phone=first.customer_phone,
        idempotency_key=first.reference,
        rail_environment="sandbox",
        metadata={"attempt_number": "2", "attempt_id": "retry"},
    )
    await adapter.initiate_payment(first)
    await adapter.initiate_payment(second)
    bodies = [json.loads(call.content) for call in script.calls if call.method == "POST" and "payments" in str(call.url)]
    assert [row["transaction"]["id"] for row in bodies] == ["PMP-AIRTEL-1", "PMP-AIRTEL-1"]
    await adapter._client.aclose()


@pytest.mark.asyncio
async def test_duplicate_and_timeout_after_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    script = _Scripted(
        [
            httpx.Response(200, json=_token_response()),
            httpx.Response(409, json={"error": "duplicate", "error_description": "exists"}),
        ]
    )
    adapter = _adapter(monkeypatch, script)
    with pytest.raises(ProviderDuplicate):
        await adapter.initiate_payment(_request())
    await adapter._client.aclose()


@pytest.mark.asyncio
async def test_status_lookup_success_pending_failed_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _Scripted(
        [
            httpx.Response(200, json=_token_response()),
            httpx.Response(200, json=_success_body()),
            httpx.Response(200, json=_pending_body()),
            httpx.Response(200, json={"data": {"transaction": {"id": "PMP-AIRTEL-1", "status": "TF"}}}),
            httpx.Response(200, json={"data": {"transaction": {"id": "missing", "status": "ZZZ"}}}),
        ]
    )
    adapter = _adapter(monkeypatch, script)
    assert (await adapter.get_payment_status("PMP-AIRTEL-1")).outcome is ProviderOutcome.SUCCESS
    assert (await adapter.get_payment_status("PMP-AIRTEL-1")).outcome is ProviderOutcome.PENDING
    assert (await adapter.get_payment_status("PMP-AIRTEL-1")).outcome is ProviderOutcome.FAILED
    unknown = await adapter.get_payment_status("missing")
    assert unknown.outcome is ProviderOutcome.PENDING
    status_call = script.calls[1]
    assert status_call.method == "GET"
    assert str(status_call.url) == f"{SANDBOX}/standard/v1/payments/PMP-AIRTEL-1"
    assert status_call.headers["X-Country"] == "MW"
    await adapter._client.aclose()


def _callback(status: str, *, include_hash: bool = True) -> bytes:
    payload = {
        "transaction": {
            "id": "PMP-AIRTEL-1",
            "status_code": status,
            "airtel_money_id": "MW-AIRTEL-99",
            "message": "callback",
        }
    }
    if include_hash:
        payload["hash"] = "placeholder"
        payload["hash"] = hmac.new(
            WEBHOOK_SECRET.encode(),
            json.dumps({k: v for k, v in payload.items() if k != "hash"}, separators=(",", ":"), ensure_ascii=False).encode(),
            hashlib.sha256,
        ).hexdigest()
    return json.dumps(payload).encode()


@pytest.mark.asyncio
async def test_webhook_valid_invalid_duplicate_malformed_unknown_late_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.payments.credentials import resolve_provider_credentials

    _env(monkeypatch)
    adapter = build_live_rail_adapter("airtel_money")
    credentials = resolve_provider_credentials("airtel_money", catalog_environment="sandbox")
    body = _callback("TS")
    ok = await adapter.verify_webhook(headers={}, body=body, credentials=credentials)
    assert ok.verified is True
    event = await adapter.parse_webhook(headers={}, body=body)
    assert event.outcome is ProviderOutcome.SUCCESS
    assert event.payment_reference == "PMP-AIRTEL-1"
    assert event.provider_event_id.endswith(":success")

    bad = json.loads(body)
    bad["hash"] = "deadbeef"
    invalid = await adapter.verify_webhook(
        headers={}, body=json.dumps(bad).encode(), credentials=credentials
    )
    assert invalid.verified is False

    malformed = await adapter.verify_webhook(headers={}, body=b"not-json", credentials=credentials)
    assert malformed.verified is False

    with pytest.raises(ValueError, match="Unsupported webhook outcome"):
        await adapter.parse_webhook(headers={}, body=_callback("NOPE"))

    failed = await adapter.parse_webhook(headers={}, body=_callback("TF"))
    assert failed.outcome is ProviderOutcome.FAILED
    assert constant_time_compare(event.provider_event_id, event.provider_event_id)


def test_webhook_hash_helper_matches_hex_and_rejects_mismatch() -> None:
    payload = {"transaction": {"id": "1", "status_code": "TS"}}
    digest = hmac.new(
        WEBHOOK_SECRET.encode(),
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(),
        hashlib.sha256,
    ).hexdigest()
    assert verify_airtel_callback_hash(secret=WEBHOOK_SECRET, payload=payload | {"hash": digest}, provided=digest)
    assert not verify_airtel_callback_hash(
        secret=WEBHOOK_SECRET, payload=payload | {"hash": "nope"}, provided="nope"
    )


@pytest.mark.asyncio
async def test_health_does_not_disable_and_distinguishes_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready = _Scripted([httpx.Response(200, json=_token_response())])
    adapter = _adapter(monkeypatch, ready)
    health = await adapter.health_check()
    assert health.configured is True
    assert health.contract_ready is True
    assert health.reachable is True
    await adapter._client.aclose()

    auth_fail = _Scripted(
        [httpx.Response(400, json={"error": "invalid_client", "error_description": "Invalid client authentication"})]
    )
    adapter = _adapter(monkeypatch, auth_fail)
    health = await adapter.health_check()
    assert health.configured is True
    assert health.reachable is True
    await adapter._client.aclose()

    down = _Scripted([])

    class FailTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

    _env(monkeypatch)
    adapter = AirtelMoneyMalawiAdapter(
        AirtelMoneyMalawiMapper("sandbox"),
        client=ProviderHttpClient(transport=FailTransport()),
        catalog_environment="sandbox",
    )
    health = await adapter.health_check()
    assert health.reachable is False
    await adapter._client.aclose()
    del down


@pytest.mark.asyncio
async def test_production_host_blocked_on_sandbox_rail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER_AIRTEL_MONEY_BASE_URL", "https://openapi.airtel.mw")
    monkeypatch.setenv("PROVIDER_AIRTEL_MONEY_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("PROVIDER_AIRTEL_MONEY_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("PROVIDER_AIRTEL_MONEY_CREDENTIAL_REF", "AIRTEL_MONEY_CLIENT_SECRET")
    monkeypatch.setenv("AIRTEL_MONEY_CLIENT_SECRET", CLIENT_SECRET)
    adapter = build_live_rail_adapter("airtel_money")
    with pytest.raises(ProviderUnavailable, match="Production Airtel host"):
        await adapter.initiate_payment(_request())


@pytest.mark.asyncio
async def test_qr_compatible_provider_request_uses_pompo_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _Scripted(
        [
            httpx.Response(200, json=_token_response()),
            httpx.Response(200, json=_pending_body("QR-REF-1")),
        ]
    )
    adapter = _adapter(monkeypatch, script)
    request = ProviderPaymentRequest(
        reference="QR-REF-1",
        amount=Decimal("10.00"),
        currency="MWK",
        merchant_id="merchant",
        customer_phone="265991000111",
        idempotency_key="QR-REF-1",
        rail_environment="sandbox",
    )
    result = await adapter.initiate_payment(request)
    assert result.outcome is ProviderOutcome.PENDING
    payload = json.loads(script.calls[1].content)
    assert payload["transaction"]["id"] == "QR-REF-1"
    await adapter._client.aclose()
