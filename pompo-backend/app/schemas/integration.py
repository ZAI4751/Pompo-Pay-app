"""Public contracts for the M013 integration / POS developer platform."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IntegrationClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    client_type: str = Field(pattern="^(developer|merchant_pos|partner)$")
    environment: str = Field(default="sandbox", pattern="^(sandbox|live)$")
    merchant_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    till_id: uuid.UUID | None = None
    scopes: list[str] | None = None
    webhook_url: str | None = Field(default=None, max_length=1000)
    rate_limit_requests: int | None = Field(default=None, ge=1, le=10000)
    key_expires_at: datetime | None = None


class IntegrationClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    scopes: list[str] | None = None
    webhook_url: str | None = Field(default=None, max_length=1000)
    rate_limit_requests: int | None = Field(default=None, ge=1, le=10000)
    disabled: bool | None = None


class APIKeyRotateRequest(BaseModel):
    expires_at: datetime | None = None
    revoke_others: bool = True


class WebhookEndpointCreate(BaseModel):
    destination_url: str = Field(min_length=8, max_length=1000)


class WebhookEndpointUpdate(BaseModel):
    is_active: bool | None = None
    destination_url: str | None = Field(default=None, min_length=8, max_length=1000)


class WebhookEndpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    destination_url: str
    is_active: bool
    webhook_secret_prefix: str | None = None
    last_delivered_at: datetime | None = None
    last_failure_category: str | None = None
    last_response_status_code: int | None = None
    created_at: datetime


class APIKeyMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class IntegrationClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_id: str
    name: str
    client_type: str
    environment: str
    status: str
    merchant_id: uuid.UUID
    branch_id: uuid.UUID | None
    till_id: uuid.UUID | None
    scopes: list[str]
    webhook_url: str | None
    webhook_secret_prefix: str | None
    rate_limit_requests: int | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    keys: list[APIKeyMetadata] = Field(default_factory=list)
    endpoints: list[WebhookEndpointResponse] = Field(default_factory=list)


class IntegrationClientCreatedResponse(IntegrationClientResponse):
    api_key: str = Field(
        description="Shown once. Never stored in plaintext and never returned by list/get.",
        json_schema_extra={"examples": ["pompo_test_<shown-once>"]},
    )
    webhook_signing_secret: str | None = Field(
        default=None,
        description="Shown once. Derived signing secret; not stored.",
        json_schema_extra={"examples": ["whsec_<shown-once>"]},
    )


class APIKeyCreatedResponse(BaseModel):
    client_id: uuid.UUID
    key_prefix: str
    api_key: str = Field(
        description="Shown once. Never stored in plaintext.",
        json_schema_extra={"examples": ["pompo_test_<shown-once>"]},
    )


class WebhookSecretCreatedResponse(BaseModel):
    client_id: uuid.UUID
    webhook_secret_prefix: str
    webhook_signing_secret: str = Field(
        description="Shown once. Derived signing secret; not stored.",
        json_schema_extra={"examples": ["whsec_<shown-once>"]},
    )


class IntegrationPaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="MWK", min_length=3, max_length=3)
    payment_method: str = Field(default="mobile_money", min_length=1, max_length=32)
    customer_phone: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=500)
    provider_code: str | None = Field(default="simulated", max_length=32)
    idempotency_key: str = Field(min_length=1, max_length=128)
    generate_qr: bool = True
    expires_in_seconds: int = Field(default=900, ge=60, le=86400)
    branch_id: uuid.UUID | None = None
    till_id: uuid.UUID | None = None
    merchant_id: uuid.UUID | None = None

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        value = value.upper()
        if value != "MWK":
            raise ValueError("currency must be MWK")
        return value


class IntegrationQRResponse(BaseModel):
    public_identifier: str
    encoded_payload: str
    qr_type: str
    status: str
    expires_at: datetime | None = None


class IntegrationPaymentResponse(BaseModel):
    reference: str
    status: str
    amount: Decimal
    currency: str
    payment_method: str
    merchant_id: uuid.UUID
    branch_id: uuid.UUID
    till_id: uuid.UUID
    description: str | None = None
    failure_reason: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    qr: IntegrationQRResponse | None = None


class OutboundWebhookDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_event_id: str
    event_type: str
    destination_url: str
    status: str
    attempt_count: int
    first_attempted_at: datetime | None = None
    last_attempted_at: datetime | None = None
    next_retry_at: datetime | None = None
    response_status_code: int | None = None
    failure_category: str | None = None
    created_at: datetime


class IntegrationErrorBody(BaseModel):
    detail: str
    code: str
    request_id: str
