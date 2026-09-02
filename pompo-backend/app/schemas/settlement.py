"""Public settlement and reconciliation API contracts."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SettlementRecordIn(BaseModel):
    settlement_reference: str = Field(min_length=1, max_length=128)
    payment_reference: str | None = Field(default=None, max_length=64)
    provider_transaction_id: str | None = Field(default=None, max_length=128)
    gross_amount: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    provider_fee: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    settlement_date: date | None = None

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class SettlementIngestRequest(BaseModel):
    provider_code: str = Field(min_length=1, max_length=32)
    batch_reference: str = Field(min_length=1, max_length=128)
    settlement_date: date
    currency: str = Field(default="MWK", min_length=3, max_length=3)
    records: list[SettlementRecordIn] = Field(min_length=1)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        value = value.upper()
        if value != "MWK":
            raise ValueError("currency must be MWK")
        return value


class SettlementIngestResponse(BaseModel):
    status: str
    batch_id: str
    duplicate: bool = False
    record_count: int


class ReconciliationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_identifier: str
    settlement_id: uuid.UUID | None
    transaction_id: uuid.UUID | None
    status: str
    mismatch_category: str | None
    expected_amount: Decimal | None
    actual_amount: Decimal | None
    variance: Decimal | None
    expected_provider_fee: Decimal | None
    actual_provider_fee: Decimal | None
    expected_pompo_fee: Decimal | None
    actual_pompo_fee: Decimal | None
    expected_currency: str | None
    actual_currency: str | None
    pompo_reference: str | None
    provider_reference: str | None
    detected_at: datetime
    resolved_at: datetime | None
    resolution_note: str | None


class SettlementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_identifier: str
    batch_id: uuid.UUID
    provider_id: uuid.UUID
    provider_settlement_reference: str
    transaction_id: uuid.UUID | None
    payment_attempt_id: uuid.UUID | None
    merchant_id: uuid.UUID | None
    branch_id: uuid.UUID | None
    payment_reference: str | None
    provider_transaction_reference: str | None
    gross_amount: Decimal
    provider_fee: Decimal
    pompo_fee: Decimal
    merchant_net: Decimal
    currency: str
    status: str
    settlement_date: date
    received_at: datetime
    created_at: datetime
    updated_at: datetime
    reconciliation: ReconciliationResponse | None = None


class SettlementBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_identifier: str
    provider_id: uuid.UUID
    external_batch_reference: str
    settlement_date: date
    currency: str
    record_count: int
    total_gross: Decimal
    total_provider_fees: Decimal
    total_pompo_fees: Decimal
    total_merchant_net: Decimal
    status: str
    created_at: datetime
    processed_at: datetime | None


class SettlementSummaryResponse(BaseModel):
    total_settlements: int
    total_gross: Decimal
    total_provider_fees: Decimal
    total_pompo_fees: Decimal
    total_merchant_net: Decimal


class ReconciliationSummaryResponse(BaseModel):
    total_settlements: int
    total_gross: Decimal
    total_provider_fees: Decimal
    total_pompo_fees: Decimal
    total_merchant_net: Decimal
    matched: int = 0
    partial_match: int = 0
    unmatched: int = 0
    discrepancy: int = 0
    investigation: int = 0
    resolved: int = 0
    matched_rate: str
    unmatched_count: int
    discrepancy_total: Decimal


class ReconciliationRunCreate(BaseModel):
    provider_code: str | None = Field(default=None, max_length=32)
    window_start: datetime
    window_end: datetime


class ReconciliationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_identifier: str
    provider_id: uuid.UUID | None
    window_start: datetime
    window_end: datetime
    records_examined: int
    matched_count: int
    unmatched_count: int
    discrepancy_count: int
    partial_count: int
    investigation_count: int
    total_expected: Decimal
    total_actual: Decimal
    total_variance: Decimal
    status: str
    started_at: datetime | None
    finished_at: datetime | None


class ReconciliationResolveRequest(BaseModel):
    note: str = Field(min_length=1, max_length=1000)
