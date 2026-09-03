"""Public QR payment API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StaticQRCreate(BaseModel):
    merchant_id: uuid.UUID
    branch_id: uuid.UUID
    till_id: uuid.UUID


class DynamicQRCreate(BaseModel):
    merchant_id: uuid.UUID
    branch_id: uuid.UUID
    till_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="MWK", min_length=3, max_length=3)
    payment_method: str = Field(default="mobile_money", min_length=1, max_length=32)
    provider_code: str | None = Field(default="simulated", max_length=32)
    customer_phone: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=500)
    expires_in_seconds: int = Field(default=900, ge=60, le=86400)
    idempotency_key: str = Field(min_length=1, max_length=128)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        value = value.upper()
        if value != "MWK":
            raise ValueError("currency must be MWK")
        return value


class PaymentFromQRRequest(BaseModel):
    payload: str | None = Field(default=None, min_length=10, max_length=2000)
    public_identifier: str | None = Field(default=None, min_length=8, max_length=40)
    idempotency_key: str = Field(min_length=1, max_length=128)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    payment_method: str = Field(default="mobile_money", min_length=1, max_length=32)
    provider_code: str | None = Field(default="simulated", max_length=32)
    payment_instrument_id: str | None = Field(default=None, max_length=40)
    customer_phone: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_payload_or_identifier(self) -> PaymentFromQRRequest:
        if not self.payload and not self.public_identifier:
            raise ValueError("payload or public_identifier is required")
        return self


class QRInspectResponse(BaseModel):
    """Safe public view for scan preview — no secrets or internal IDs beyond context."""

    public_identifier: str
    qr_type: str
    version: int
    status: str
    merchant_name: str
    branch_name: str
    till_name: str
    amount: Decimal | None = None
    currency: str
    payment_reference: str | None = None
    expires_at: datetime | None = None
    payment_url: str | None = None


class QRResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_identifier: str
    qr_type: str
    version: int
    status: str
    encoded_payload: str
    payment_url: str | None = None
    merchant_id: uuid.UUID
    branch_id: uuid.UUID
    till_id: uuid.UUID
    merchant_name: str
    branch_name: str
    till_name: str
    amount: Decimal | None = None
    currency: str
    payment_reference: str | None = None
    expires_at: datetime | None = None
    created_at: datetime
    revoked_at: datetime | None = None
