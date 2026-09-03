"""Authoritative live-provider HTTP contracts.

Insert a contract here only when POMPO has approved provider documentation
in the repository (endpoints, auth, payloads, signatures). TNM Mpamba Malawi
is documented as a contract dependency in docs/providers/tnm-mpamba-malawi.md
and is not registered. Bank rails remain unregistered. Airtel Money Malawi is
registered from docs/providers/airtel-money-malawi.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.payments.http import ProviderHttpRequest, ProviderHttpResponse
from app.payments.providers import ProviderCapabilities, ProviderPaymentRequest, ProviderResult


@dataclass(frozen=True)
class ProviderHttpContract:
    """Metadata describing an approved integration. Paths are relative."""

    code: str
    rail_environment: str
    source: str
    capabilities: ProviderCapabilities
    idempotency_header: str | None = None
    health_path: str | None = None


class ProviderHttpMapper(Protocol):
    """Translates POMPO requests to a provider's documented HTTP contract."""

    contract: ProviderHttpContract

    def initiate(
        self, request: ProviderPaymentRequest, base_url: str, secret: str
    ) -> ProviderHttpRequest: ...

    def parse_initiate(self, response: ProviderHttpResponse) -> ProviderResult: ...

    def status(self, provider_reference: str, base_url: str, secret: str) -> ProviderHttpRequest: ...

    def parse_status(self, response: ProviderHttpResponse) -> ProviderResult: ...

    def health(self, base_url: str, secret: str) -> ProviderHttpRequest | None: ...


# Keyed by (provider_code, rail_environment). Populate only from approved docs.
AUTHORITATIVE_CONTRACTS: dict[tuple[str, str], ProviderHttpMapper] = {}


def _register_approved_contracts() -> None:
    from app.payments.airtel_malawi import airtel_malawi_mappers

    AUTHORITATIVE_CONTRACTS.update(airtel_malawi_mappers())


_register_approved_contracts()


def get_authoritative_mapper(code: str, rail_environment: str) -> ProviderHttpMapper | None:
    return AUTHORITATIVE_CONTRACTS.get((code, rail_environment))


def has_authoritative_contract(code: str) -> bool:
    return any(key[0] == code for key in AUTHORITATIVE_CONTRACTS)
