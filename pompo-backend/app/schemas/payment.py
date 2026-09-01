"""Public payment-core API contracts."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentCreate(BaseModel):
    merchant_id: uuid.UUID
    branch_id: uuid.UUID
    till_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="MWK", min_length=3, max_length=3)
    payment_method: str = Field(min_length=1, max_length=32)
    customer_phone: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=500)
    provider_code: str | None = Field(default="simulated", max_length=32)
    idempotency_key: str = Field(min_length=1, max_length=128)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        value = value.upper()
        if value != "MWK":
            raise ValueError("currency must be MWK")
        return value

    @field_validator("provider_code")
    @classmethod
    def normalize_provider_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class PaymentAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attempt_number: int
    status: str
    provider_reference: str | None
    provider_status: str | None = None
    duration_ms: int | None = None
    failure_code: str | None = None
    retryable: bool | None = None
    failure_reason: str | None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    merchant_id: uuid.UUID
    branch_id: uuid.UUID
    till_id: uuid.UUID
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    description: str | None
    failure_reason: str | None
    attempts: list[PaymentAttemptResponse] = Field(default_factory=list)


class PaymentTransition(BaseModel):
    status: str
    failure_reason: str | None = Field(default=None, max_length=500)


class ProviderCapabilityResponse(BaseModel):
    supports_push_payment: bool
    supports_status_query: bool
    supports_cancel: bool
    supports_refund: bool
    supports_webhooks: bool
    supports_qr: bool


class ProviderHealthResponse(BaseModel):
    configured: bool
    reachable: bool | None
    supports_health_check: bool
    contract_ready: bool = False
    message: str | None = None


class ProviderConfigurationStatus(BaseModel):
    """Secret-free view of whether referenced configuration exists."""

    base_url_configured: bool
    timeout_seconds: int
    auth_configured: bool
    signing_configured: bool
    configuration_complete: bool
    rail_environment: str
    production_rail_permitted: bool
    contract_registered: bool


class ProviderCatalogResponse(BaseModel):
    code: str
    display_name: str
    provider_type: str
    is_active: bool
    is_simulated: bool
    environment: str
    health_state: str
    priority: int
    supported_currencies: list[str]
    supported_payment_methods: list[str]
    capabilities: ProviderCapabilityResponse
    adapter_configured: bool
    live_contract_ready: bool
    configuration: ProviderConfigurationStatus
    health: ProviderHealthResponse


class ProviderCatalogCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    display_name: str = Field(min_length=1, max_length=255)
    provider_type: str | None = Field(default=None, max_length=32)
    environment: str = Field(default="sandbox", pattern="^(sandbox|live)$")
    priority: int = Field(default=100, ge=1, le=1000)
    supported_currencies: list[str] = Field(default_factory=lambda: ["MWK"])
    supported_payment_methods: list[str] = Field(default_factory=lambda: ["mobile_money"])


class ProviderCatalogUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    environment: str | None = Field(default=None, pattern="^(sandbox|live)$")
    priority: int | None = Field(default=None, ge=1, le=1000)
    supported_currencies: list[str] | None = None
    supported_payment_methods: list[str] | None = None
