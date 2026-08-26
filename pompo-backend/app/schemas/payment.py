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
    provider_code: str = Field(default="simulated", min_length=1, max_length=32)
    idempotency_key: str = Field(min_length=1, max_length=128)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        value = value.upper()
        if value != "MWK":
            raise ValueError("currency must be MWK")
        return value


class PaymentAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attempt_number: int
    status: str
    provider_reference: str | None
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
