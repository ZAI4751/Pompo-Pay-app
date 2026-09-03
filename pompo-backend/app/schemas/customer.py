"""Pydantic schemas for M015 customer product endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CustomerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("full_name is required")
        return stripped

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class CustomerRegisterResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    role_code: str
    phone_verification: str = "not_configured"
    is_email_verified: bool = False
    email_verification: str = "not_configured"


class CustomerProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    preferred_mode: str | None = Field(default=None, max_length=16)

    @field_validator("preferred_mode")
    @classmethod
    def mode_values(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        if value not in {"customer", "merchant"}:
            raise ValueError("preferred_mode must be customer or merchant")
        return value


class PreferenceUpdate(BaseModel):
    notify_payment_success: bool | None = None
    notify_payment_failed: bool | None = None
    notify_payment_updates: bool | None = None
    notify_payment_requests: bool | None = None
    preferred_mode: str | None = Field(default=None, max_length=16)


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notify_payment_success: bool
    notify_payment_failed: bool
    notify_payment_updates: bool
    notify_payment_requests: bool
    preferred_mode: str | None
    phone_verification: str = "not_configured"


class FavoriteCreate(BaseModel):
    merchant_id: uuid.UUID


class FavoriteMerchantResponse(BaseModel):
    merchant_id: uuid.UUID
    merchant_name: str
    is_favorite: bool
    last_paid_at: datetime | None = None
    last_payment_reference: str | None = None
    payment_count: int = 0
    is_active: bool = True


class CustomerInsightsResponse(BaseModel):
    payments_this_week: int
    spent_this_week: Decimal
    payments_this_month: int
    spent_this_month: Decimal
    payment_count: int
    spent_total: Decimal
    most_used_merchants: list[dict]
    disclaimer: str = (
        "These totals are from your completed POMPO payments. This is not a bank statement."
    )


class CustomerStatsResponse(BaseModel):
    customer_count: int
    payment_requests: dict[str, int]
    support_open_count: int


class PaymentRequestCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="MWK", min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=500)
    merchant_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    till_id: uuid.UUID | None = None
    source_payment_reference: str | None = Field(default=None, max_length=64)
    expires_in_seconds: int | None = Field(default=86400, ge=60, le=2592000)
    idempotency_key: str = Field(min_length=1, max_length=128)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        value = value.upper()
        if value != "MWK":
            raise ValueError("currency must be MWK")
        return value


class PaymentRequestPay(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=128)
    payment_method: str = Field(default="mobile_money", min_length=1, max_length=32)
    customer_phone: str | None = Field(default=None, max_length=32)
    provider_code: str | None = Field(default=None, max_length=32)


class SplitParticipant(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    label: str | None = Field(default=None, max_length=100)


class BillSplitCreate(BaseModel):
    total_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="MWK", min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=500)
    merchant_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    till_id: uuid.UUID | None = None
    source_payment_reference: str | None = Field(default=None, max_length=64)
    participants: list[SplitParticipant] = Field(min_length=2, max_length=20)
    expires_in_seconds: int | None = Field(default=86400, ge=60, le=2592000)
    idempotency_key: str = Field(min_length=1, max_length=128)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        value = value.upper()
        if value != "MWK":
            raise ValueError("currency must be MWK")
        return value


class PaymentRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_identifier: str
    share_code: str
    requester_id: uuid.UUID
    requester_name: str | None = None
    payer_user_id: uuid.UUID | None = None
    merchant_id: uuid.UUID
    merchant_name: str | None = None
    branch_name: str | None = None
    till_name: str | None = None
    amount: Decimal
    currency: str
    description: str | None
    status: str
    expires_at: datetime | None
    paid_at: datetime | None
    payment_reference: str | None = None
    bill_split_id: uuid.UUID | None = None
    created_at: datetime | None = None


class BillSplitResponse(BaseModel):
    id: uuid.UUID
    public_identifier: str
    total_amount: Decimal
    currency: str
    description: str | None
    status: str
    merchant_name: str | None = None
    expires_at: datetime | None
    requests: list[PaymentRequestResponse]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_identifier: str
    notification_type: str
    title: str
    body: str
    entity_type: str | None
    entity_id: str | None
    payment_reference: str | None
    read_at: datetime | None
    created_at: datetime | None = None


class NotificationListResponse(BaseModel):
    unread_count: int
    items: list[NotificationResponse]


class SupportRequestCreate(BaseModel):
    category: str = Field(min_length=1, max_length=32)
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)
    payment_reference: str | None = Field(default=None, max_length=64)
    payment_request_id: str | None = Field(default=None, max_length=40)


class SupportRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_identifier: str
    category: str
    subject: str
    message: str
    payment_reference: str | None
    status: str
    created_at: datetime | None = None
