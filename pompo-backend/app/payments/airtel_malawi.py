"""Airtel Money Malawi Collection adapter.

HTTP paths and OAuth error schema were confirmed against Airtel-owned hosts.
Request/callback field names that were not in public swagger are isolated here
and documented in docs/providers/airtel-money-malawi.md. This module never logs
tokens or secrets.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

from app.core.logging import get_logger
from app.payments.credentials import ProviderCredentials, resolve_provider_credentials
from app.payments.http import ProviderHttpClient, ProviderHttpRequest, ProviderHttpResponse
from app.payments.providers import (
    ProviderAuthenticationError,
    ProviderCapabilities,
    ProviderDuplicate,
    ProviderError,
    ProviderErrorCode,
    ProviderHealth,
    ProviderInvalidRequest,
    ProviderOutcome,
    ProviderPaymentRequest,
    ProviderRateLimited,
    ProviderRejected,
    ProviderResult,
    ProviderTimeout,
    ProviderUnavailable,
    ProviderUnknownError,
    UnsupportedProviderOperation,
    require_capability,
    retry_class_for,
)
from app.payments.webhooks import (
    NormalizedWebhookEvent,
    WebhookVerificationResult,
    constant_time_compare,
    normalize_headers,
)

logger = get_logger(__name__)

PROVIDER_CODE = "airtel_money"
COUNTRY = "MW"
CURRENCY = "MWK"
SANDBOX_HOST = "openapiuat.airtel.mw"
PRODUCTION_HOST = "openapi.airtel.mw"
AUTH_PATH = "/auth/oauth2/token"
INITIATE_PATH = "/merchant/v1/payments/"
STATUS_PATH = "/standard/v1/payments/{transaction_id}"
TOKEN_SKEW_SECONDS = 30
TOKEN_DEFAULT_TTL_SECONDS = 60
CONTRACT_SOURCE = "docs/providers/airtel-money-malawi.md"

AIRTEL_CAPABILITIES = ProviderCapabilities(
    supports_push_payment=True,
    supports_status_query=True,
    supports_cancel=False,
    supports_refund=False,
    supports_webhooks=True,
    supports_qr=False,
)

_SUCCESS_TOKENS = frozenset({"TS", "SUCCESS"})
_FAILED_TOKENS = frozenset({"TF", "TE", "FAILED", "FAILURE"})
_PENDING_TOKENS = frozenset({"TIP", "TA", "PENDING", "IN_PROGRESS"})


@dataclass
class _CachedToken:
    value: str
    expires_at: float


def recommended_base_url(rail_environment: str) -> str:
    if rail_environment == "production":
        return f"https://{PRODUCTION_HOST}"
    return f"https://{SANDBOX_HOST}"


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def assert_base_url_matches_rail(base_url: str, rail_environment: str) -> None:
    host = _host(base_url)
    if not host:
        raise ProviderInvalidRequest("Airtel base URL is missing a host")
    if rail_environment == "production" and host == SANDBOX_HOST:
        raise ProviderUnavailable("Sandbox Airtel host cannot be used on a production rail")
    if rail_environment != "production" and host == PRODUCTION_HOST:
        raise ProviderUnavailable("Production Airtel host cannot be used on a sandbox rail")


def normalize_malawi_msisdn(raw: str | None) -> str:
    if not raw or not raw.strip():
        raise ProviderInvalidRequest("Customer phone is required for Airtel Money")
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("265") and len(digits) > 9:
        digits = digits[3:]
    if digits.startswith("0") and len(digits) == 10:
        digits = digits[1:]
    if len(digits) < 8:
        raise ProviderInvalidRequest("Customer phone is not a usable Malawi MSISDN")
    return digits


def amount_payload(amount: Decimal) -> int | float:
    quantized = amount.quantize(Decimal("1")) if amount == amount.to_integral_value() else amount
    if quantized == quantized.to_integral_value():
        return int(quantized)
    return float(quantized)


def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _json_object(response: ProviderHttpResponse) -> dict[str, Any]:
    body = response.json_body
    if isinstance(body, dict):
        return body
    return {}


def _status_token(raw: Any) -> str:
    if raw is None:
        return ""
    return str(raw).strip().upper()


def map_status_token(raw: Any) -> ProviderOutcome | None:
    token = _status_token(raw)
    if not token:
        return None
    if token in _SUCCESS_TOKENS:
        return ProviderOutcome.SUCCESS
    if token in _FAILED_TOKENS:
        return ProviderOutcome.FAILED
    if token in _PENDING_TOKENS:
        return ProviderOutcome.PENDING
    return None


def _transaction_block(payload: dict[str, Any]) -> dict[str, Any]:
    data = _as_mapping(payload.get("data"))
    for candidate in (
        payload.get("transaction"),
        data.get("transaction"),
        data,
        payload,
    ):
        block = _as_mapping(candidate)
        if block.get("id") or block.get("airtel_money_id") or block.get("status") or block.get("status_code"):
            return block
    return {}


def _provider_refs(block: dict[str, Any], fallback: str | None = None) -> tuple[str | None, str | None]:
    txn_id = block.get("id") or block.get("transaction_id")
    money_id = block.get("airtel_money_id") or block.get("airtelMoneyId")
    provider_reference = str(txn_id).strip() if txn_id else fallback
    provider_transaction_id = str(money_id).strip() if money_id else provider_reference
    return provider_reference, provider_transaction_id


def _oauth_error_code(payload: dict[str, Any]) -> str:
    return str(payload.get("error") or payload.get("error_description") or "").strip().lower()


def translate_airtel_http(response: ProviderHttpResponse, *, operation: str) -> ProviderError:
    payload = _json_object(response)
    oauth = _oauth_error_code(payload)
    message = str(payload.get("error_description") or payload.get("message") or f"Airtel {operation} failed")
    if response.status_code in {401, 403} or oauth in {"invalid_client", "invalid_token", "unauthorized"}:
        return ProviderAuthenticationError(message)
    if response.status_code == 429:
        return ProviderRateLimited(message)
    if response.status_code == 409 or oauth == "duplicate":
        return ProviderDuplicate(message)
    if response.status_code in {408, 504}:
        return ProviderTimeout(message)
    if response.status_code in {400, 404, 422} or oauth == "invalid_request":
        return ProviderInvalidRequest(message)
    if response.status_code >= 500:
        return ProviderUnavailable(message)
    return ProviderUnknownError(message)


def parse_access_token(payload: dict[str, Any]) -> tuple[str, int]:
    token = payload.get("access_token")
    nested = _as_mapping(payload.get("data"))
    if not token:
        token = nested.get("access_token")
    if not isinstance(token, str) or not token.strip():
        raise ProviderAuthenticationError("Airtel token response did not include access_token")
    expires_raw = payload.get("expires_in", nested.get("expires_in"))
    try:
        expires_in = int(expires_raw) if expires_raw is not None else TOKEN_DEFAULT_TTL_SECONDS
    except (TypeError, ValueError):
        expires_in = TOKEN_DEFAULT_TTL_SECONDS
    return token.strip(), max(1, expires_in)


def _strip_hash_for_signature(payload: dict[str, Any]) -> bytes:
    cleaned = dict(payload)
    cleaned.pop("hash", None)
    return json.dumps(cleaned, separators=(",", ":"), ensure_ascii=False).encode()


def verify_airtel_callback_hash(*, secret: str, payload: dict[str, Any], provided: str) -> bool:
    """PLACEHOLDER signing: HMAC-SHA256 over canonical JSON without `hash`."""

    digest = hmac.new(secret.encode(), _strip_hash_for_signature(payload), hashlib.sha256).digest()
    hex_sig = digest.hex()
    b64_sig = base64.b64encode(digest).decode()
    candidate = provided.strip()
    if candidate.lower().startswith("sha256="):
        candidate = candidate[7:]
    return constant_time_compare(candidate, hex_sig) or constant_time_compare(candidate, b64_sig)


def unsigned_callbacks_allowed() -> bool:
    return os.environ.get("PROVIDER_AIRTEL_MONEY_WEBHOOK_UNSIGNED", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


class AirtelMoneyMalawiMapper:
    """Maps POMPO requests onto the captured Malawi Collection contract."""

    def __init__(self, rail_environment: str) -> None:
        from app.payments.contracts import ProviderHttpContract

        self.contract = ProviderHttpContract(
            code=PROVIDER_CODE,
            rail_environment=rail_environment,
            source=CONTRACT_SOURCE,
            capabilities=AIRTEL_CAPABILITIES,
            idempotency_header=None,
            health_path=None,
        )

    def authenticate(self, base_url: str, client_id: str, client_secret: str) -> ProviderHttpRequest:
        return ProviderHttpRequest(
            method="POST",
            url=f"{base_url.rstrip('/')}{AUTH_PATH}",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json_body={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            },
            retry_safe=False,
        )

    def initiate(
        self, request: ProviderPaymentRequest, base_url: str, secret: str
    ) -> ProviderHttpRequest:
        if request.currency.upper() != CURRENCY:
            raise ProviderInvalidRequest("Airtel Money Malawi only accepts MWK")
        body = {
            "reference": request.reference,
            "subscriber": {
                "country": COUNTRY,
                "currency": CURRENCY,
                "msisdn": normalize_malawi_msisdn(request.customer_phone),
            },
            "transaction": {
                "amount": amount_payload(request.amount),
                "country": COUNTRY,
                "currency": CURRENCY,
                "id": request.reference,
            },
        }
        return ProviderHttpRequest(
            method="POST",
            url=f"{base_url.rstrip('/')}{INITIATE_PATH}",
            headers={
                "Authorization": f"Bearer {secret}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Country": COUNTRY,
                "X-Currency": CURRENCY,
            },
            json_body=body,
            retry_safe=False,
        )

    def parse_initiate(self, response: ProviderHttpResponse) -> ProviderResult:
        return self._parse_payment_response(response, default_pending=True)

    def status(self, provider_reference: str, base_url: str, secret: str) -> ProviderHttpRequest:
        path = STATUS_PATH.format(transaction_id=provider_reference)
        return ProviderHttpRequest(
            method="GET",
            url=f"{base_url.rstrip('/')}{path}",
            headers={
                "Authorization": f"Bearer {secret}",
                "Accept": "application/json",
                "X-Country": COUNTRY,
                "X-Currency": CURRENCY,
            },
            retry_safe=True,
        )

    def parse_status(self, response: ProviderHttpResponse) -> ProviderResult:
        return self._parse_payment_response(response, default_pending=True)

    def health(self, base_url: str, secret: str) -> ProviderHttpRequest | None:
        return None

    def _parse_payment_response(
        self, response: ProviderHttpResponse, *, default_pending: bool
    ) -> ProviderResult:
        payload = _json_object(response)
        if response.status_code >= 400:
            raise translate_airtel_http(response, operation="payment")
        if not payload:
            raise ProviderInvalidRequest("Airtel returned a malformed payment response")

        envelope = _as_mapping(payload.get("status"))
        if envelope.get("success") is False or str(envelope.get("code") or "") in {"400", "401", "403"}:
            raise ProviderRejected(str(envelope.get("message") or "Airtel rejected the payment"))

        block = _transaction_block(payload)
        token = block.get("status_code") or block.get("status") or envelope.get("result_code")
        outcome = map_status_token(token)
        if outcome is None:
            outcome = ProviderOutcome.PENDING if default_pending else ProviderOutcome.FAILED
        reference, transaction_id = _provider_refs(block)
        message = block.get("message") or envelope.get("message")
        retryable = outcome is ProviderOutcome.PENDING
        error_code = None
        if outcome in {ProviderOutcome.FAILED, ProviderOutcome.REJECTED, ProviderOutcome.TIMEOUT}:
            error_code = ProviderErrorCode.REJECTED if outcome is ProviderOutcome.REJECTED else ProviderErrorCode.UNKNOWN
            retryable = False
        return ProviderResult(
            outcome=outcome,
            provider_reference=reference,
            provider_status=_status_token(token) or outcome.value,
            provider_transaction_id=transaction_id,
            correlation_id=str(payload["request_id"]) if payload.get("request_id") else None,
            message=str(message) if message is not None else None,
            retryable=retryable,
            error_code=error_code,
        )


class AirtelMoneyMalawiAdapter:
    """OAuth-backed Malawi Collection adapter. Never mutates transactions."""

    code = PROVIDER_CODE
    capabilities = AIRTEL_CAPABILITIES

    def __init__(
        self,
        mapper: AirtelMoneyMalawiMapper,
        *,
        client: ProviderHttpClient | None = None,
        catalog_environment: str = "sandbox",
    ) -> None:
        self._mapper = mapper
        self._client = client or ProviderHttpClient()
        self._catalog_environment = catalog_environment
        self._token: _CachedToken | None = None

    @property
    def live_contract_ready(self) -> bool:
        try:
            credentials = self._credentials()
        except Exception:
            return False
        return bool(credentials.configuration_complete and credentials.client_id)

    async def initiate_payment(self, request: ProviderPaymentRequest) -> ProviderResult:
        require_capability(self, "initiate")
        credentials = self._require_credentials(request.rail_environment)
        token = await self._access_token(credentials)
        spec = self._mapper.initiate(request, credentials.base_url or "", token)
        started = time.monotonic()
        try:
            result = await self._send_payment(spec)
        except ProviderAuthenticationError:
            self._token = None
            token = await self._access_token(credentials, force=True)
            spec = self._mapper.initiate(request, credentials.base_url or "", token)
            result = await self._send_payment(spec)
        logger.info(
            "airtel_payment_initiated",
            provider=PROVIDER_CODE,
            transaction_reference=request.reference,
            outcome=result.outcome.value,
            provider_status=result.provider_status,
            latency_ms=int((time.monotonic() - started) * 1000),
            retryable=result.retryable,
            failure_category=result.error_code.value if result.error_code else None,
        )
        return result

    async def get_payment_status(self, provider_reference: str) -> ProviderResult:
        require_capability(self, "status_query")
        credentials = self._require_credentials()
        token = await self._access_token(credentials)
        spec = self._mapper.status(provider_reference, credentials.base_url or "", token)
        try:
            return await self._send_payment(spec)
        except ProviderAuthenticationError:
            self._token = None
            token = await self._access_token(credentials, force=True)
            spec = self._mapper.status(provider_reference, credentials.base_url or "", token)
            return await self._send_payment(spec)

    async def cancel_payment(self, provider_reference: str) -> ProviderResult:
        raise UnsupportedProviderOperation("cancel")

    async def refund_payment(self, provider_reference: str, amount: Decimal) -> ProviderResult:
        raise UnsupportedProviderOperation("refund")

    async def health_check(self) -> ProviderHealth:
        try:
            credentials = self._credentials()
        except Exception as exc:
            return ProviderHealth(
                configured=False,
                contract_ready=False,
                supports_health_check=True,
                reachable=None,
                message=str(exc),
            )
        ready = bool(credentials.configuration_complete and credentials.client_id)
        if not ready:
            return ProviderHealth(
                configured=False,
                contract_ready=False,
                supports_health_check=True,
                reachable=None,
                message="Airtel client id, secret, and base URL are not all configured",
            )
        try:
            await self._access_token(credentials, force=True)
        except ProviderAuthenticationError as exc:
            return ProviderHealth(
                configured=True,
                contract_ready=True,
                supports_health_check=True,
                reachable=True,
                message=str(exc),
            )
        except ProviderError as exc:
            retryable = retry_class_for(exc.code).value
            logger.warning(
                "airtel_health_probe_failed",
                provider=PROVIDER_CODE,
                failure_category=exc.code.value,
                retryable=retryable == "retryable",
            )
            return ProviderHealth(
                configured=True,
                contract_ready=True,
                supports_health_check=True,
                reachable=False,
                message="Airtel token endpoint was not reachable",
            )
        return ProviderHealth(
            configured=True,
            contract_ready=True,
            supports_health_check=True,
            reachable=True,
            message=None,
        )

    async def verify_webhook(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
        credentials: ProviderCredentials,
    ) -> WebhookVerificationResult:
        del headers
        secret = credentials.webhook_secret()
        try:
            payload = json.loads(body.decode())
        except (UnicodeDecodeError, json.JSONDecodeError):
            return WebhookVerificationResult(False, failure_reason="Malformed webhook JSON")
        if not isinstance(payload, dict):
            return WebhookVerificationResult(False, failure_reason="Webhook payload must be a JSON object")
        provided = payload.get("hash")
        if secret:
            if not isinstance(provided, str) or not provided.strip():
                return WebhookVerificationResult(False, failure_reason="Missing Airtel callback hash")
            if not verify_airtel_callback_hash(secret=secret, payload=payload, provided=provided):
                return WebhookVerificationResult(False, failure_reason="Invalid Airtel callback hash")
            return WebhookVerificationResult(True, timestamp_validated=False)
        if unsigned_callbacks_allowed():
            return WebhookVerificationResult(True, timestamp_validated=False)
        return WebhookVerificationResult(False, failure_reason="Webhook secret not configured")

    async def parse_webhook(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> NormalizedWebhookEvent:
        del headers
        try:
            payload = json.loads(body.decode())
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Malformed webhook JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("Webhook payload must be a JSON object")
        block = _transaction_block(payload)
        payment_reference = block.get("id") or payload.get("id")
        if not payment_reference:
            raise ValueError("Missing provider event identifier")
        status_raw = block.get("status_code") or block.get("status")
        outcome = map_status_token(status_raw)
        if outcome is None:
            raise ValueError(f"Unsupported webhook outcome: {status_raw}")
        money_id = block.get("airtel_money_id")
        event_id = str(money_id or payment_reference).strip() + ":" + outcome.value
        event_type = f"payment.{outcome.value}"
        return NormalizedWebhookEvent(
            provider_event_id=event_id,
            event_type=event_type,
            event_version="collection-callback",
            payment_reference=str(payment_reference).strip(),
            provider_transaction_reference=str(money_id).strip() if money_id else str(payment_reference).strip(),
            outcome=outcome,
            message=str(block["message"]) if block.get("message") is not None else None,
            metadata={"provider": PROVIDER_CODE, "country": COUNTRY},
        )

    def _credentials(self, rail_environment: str | None = None) -> ProviderCredentials:
        return resolve_provider_credentials(
            PROVIDER_CODE,
            catalog_environment=rail_environment or self._catalog_environment,
        )

    def _require_credentials(self, rail_environment: str | None = None) -> ProviderCredentials:
        credentials = self._credentials(rail_environment)
        if not credentials.base_url or not credentials.secret() or not credentials.client_id:
            raise ProviderUnavailable("Live airtel_money credentials are not configured")
        assert_base_url_matches_rail(credentials.base_url, credentials.rail_environment)
        return credentials

    async def _access_token(self, credentials: ProviderCredentials, *, force: bool = False) -> str:
        now = time.monotonic()
        if not force and self._token is not None and self._token.expires_at > now:
            return self._token.value
        spec = self._mapper.authenticate(
            credentials.base_url or "",
            credentials.client_id or "",
            credentials.secret() or "",
        )
        started = time.monotonic()
        response = await self._client.send(spec)
        latency_ms = int((time.monotonic() - started) * 1000)
        if response.status_code >= 400:
            logger.warning(
                "airtel_auth_failed",
                provider=PROVIDER_CODE,
                status_code=response.status_code,
                latency_ms=latency_ms,
                failure_category=translate_airtel_http(response, operation="auth").code.value,
            )
            raise translate_airtel_http(response, operation="auth")
        token, expires_in = parse_access_token(_json_object(response))
        ttl = max(1, expires_in - TOKEN_SKEW_SECONDS)
        self._token = _CachedToken(token, time.monotonic() + ttl)
        logger.info(
            "airtel_auth_succeeded",
            provider=PROVIDER_CODE,
            latency_ms=latency_ms,
            expires_in=expires_in,
        )
        return token

    async def _send_payment(self, spec: ProviderHttpRequest) -> ProviderResult:
        response = await self._client.send(spec)
        if spec.method.upper() == "GET":
            return self._mapper.parse_status(response)
        return self._mapper.parse_initiate(response)


def airtel_malawi_mappers() -> dict[tuple[str, str], AirtelMoneyMalawiMapper]:
    return {
        (PROVIDER_CODE, "sandbox"): AirtelMoneyMalawiMapper("sandbox"),
        (PROVIDER_CODE, "production"): AirtelMoneyMalawiMapper("production"),
    }
