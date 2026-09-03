"""Customer payment-method API contracts. Never include token_reference."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PaymentMethodCreate(BaseModel):
    provider_code: str = Field(min_length=1, max_length=32)
    instrument_type: str = Field(min_length=1, max_length=32)
    display_name: str | None = Field(default=None, max_length=120)
    msisdn: str | None = Field(default=None, max_length=32)
    card_last4: str | None = Field(default=None, max_length=4)
    make_default: bool = False

    @model_validator(mode="before")
    @classmethod
    def reject_secrets(cls, data: object) -> object:
        if isinstance(data, dict):
            from app.payments.instrument_tokens import reject_secret_fields

            reject_secret_fields(data)
        return data


class PaymentMethodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_code: str
    provider_display_name: str
    instrument_type: str
    display_name: str
    masked_identifier: str
    status: str
    authorization_state: str
    is_default: bool
    is_sandbox: bool
    last_used_at: datetime | None = None
    created_at: datetime
    enrollment_available: bool = True
    unavailable_reason: str | None = None
    customer_email: str | None = None


class PaymentMethodCatalogItem(BaseModel):
    provider_code: str
    instrument_type: str
    label: str
    available: bool
    is_sandbox: bool
    reason: str | None = None
    authorization_state: str
