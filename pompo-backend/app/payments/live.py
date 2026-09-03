"""HTTP-backed live adapter used only when an authoritative mapper exists."""

from __future__ import annotations

from decimal import Decimal

from app.payments.airtel_malawi import AirtelMoneyMalawiAdapter, AirtelMoneyMalawiMapper
from app.payments.contracts import get_authoritative_mapper
from app.payments.tnm_mpamba import TnmMpambaMalawiAdapter
from app.payments.credentials import (
    ProviderEnvironmentError,
    normalize_rail_environment,
    resolve_provider_credentials,
)
from app.payments.http import ProviderHttpClient
from app.payments.providers import (
    ProviderCapabilities,
    ProviderError,
    ProviderHealth,
    ProviderPaymentRequest,
    ProviderResult,
    ProviderUnavailable,
    UnsupportedProviderOperation,
    require_capability,
)
from app.payments.stubs import PLANNED_CAPABILITIES, UnconfiguredRailAdapter


class ContractBoundHttpAdapter:
    """Executes mapped HTTP calls. Never mutates transaction state."""

    def __init__(
        self,
        code: str,
        mapper: ProviderHttpMapper,
        *,
        client: ProviderHttpClient | None = None,
        catalog_environment: str = "sandbox",
    ) -> None:
        self.code = code
        self.capabilities = mapper.contract.capabilities
        self._mapper = mapper
        self._client = client or ProviderHttpClient()
        self._catalog_environment = catalog_environment

    @property
    def live_contract_ready(self) -> bool:
        try:
            credentials = resolve_provider_credentials(
                self.code, catalog_environment=self._catalog_environment
            )
        except ProviderEnvironmentError:
            return False
        return credentials.configuration_complete

    async def initiate_payment(self, request: ProviderPaymentRequest) -> ProviderResult:
        require_capability(self, "initiate")
        credentials = self._require_credentials(request.rail_environment)
        spec = self._mapper.initiate(request, credentials.base_url or "", credentials.secret() or "")
        response = await self._client.send_or_raise(spec)
        return self._mapper.parse_initiate(response)

    async def get_payment_status(self, provider_reference: str) -> ProviderResult:
        require_capability(self, "status_query")
        credentials = self._require_credentials()
        spec = self._mapper.status(provider_reference, credentials.base_url or "", credentials.secret() or "")
        response = await self._client.send_or_raise(spec)
        return self._mapper.parse_status(response)

    async def cancel_payment(self, provider_reference: str) -> ProviderResult:
        require_capability(self, "cancel")
        raise UnsupportedProviderOperation("cancel")

    async def refund_payment(self, provider_reference: str, amount: Decimal) -> ProviderResult:
        require_capability(self, "refund")
        raise UnsupportedProviderOperation("refund")

    async def health_check(self) -> ProviderHealth:
        try:
            credentials = resolve_provider_credentials(
                self.code, catalog_environment=self._catalog_environment
            )
        except ProviderEnvironmentError:
            return ProviderHealth(
                configured=False,
                contract_ready=False,
                supports_health_check=False,
                reachable=None,
                message="Production rail blocked outside production",
            )
        ready = credentials.configuration_complete
        if not ready:
            return ProviderHealth(
                configured=False,
                contract_ready=False,
                supports_health_check=self._mapper.contract.health_path is not None,
                reachable=None,
                message="Live credentials are not configured",
            )
        probe = self._mapper.health(credentials.base_url or "", credentials.secret() or "")
        if probe is None:
            return ProviderHealth(
                configured=ready,
                contract_ready=ready,
                supports_health_check=False,
                reachable=None,
                message="Authoritative contract has no health endpoint",
            )
        try:
            response = await self._client.send_or_raise(probe)
        except ProviderError:
            return ProviderHealth(
                configured=ready,
                contract_ready=ready,
                supports_health_check=True,
                reachable=False,
                message="Provider health endpoint was not reachable",
            )
        return ProviderHealth(
            configured=ready,
            contract_ready=ready,
            supports_health_check=True,
            reachable=response.status_code < 400,
            message=None,
        )

    def _require_credentials(self, rail_environment: str | None = None):
        credentials = resolve_provider_credentials(
            self.code,
            catalog_environment=rail_environment or self._catalog_environment,
        )
        if not credentials.configuration_complete:
            raise ProviderUnavailable(f"Live {self.code} credentials are not configured")
        return credentials


def build_live_rail_adapter(
    code: str,
    *,
    catalog_environment: str = "sandbox",
    client: ProviderHttpClient | None = None,
    capabilities: ProviderCapabilities | None = None,
) -> UnconfiguredRailAdapter | ContractBoundHttpAdapter | AirtelMoneyMalawiAdapter | TnmMpambaMalawiAdapter:
    if code == "tnm_mpamba":
        mapper = get_authoritative_mapper(code, normalize_rail_environment(catalog_environment))
        if mapper is None:
            return TnmMpambaMalawiAdapter(catalog_environment=catalog_environment)
    mapper = get_authoritative_mapper(code, normalize_rail_environment(catalog_environment))
    if mapper is None:
        return UnconfiguredRailAdapter(code, capabilities or PLANNED_CAPABILITIES)
    if isinstance(mapper, AirtelMoneyMalawiMapper):
        return AirtelMoneyMalawiAdapter(
            mapper, client=client, catalog_environment=catalog_environment
        )
    return ContractBoundHttpAdapter(
        code, mapper, client=client, catalog_environment=catalog_environment
    )
