"""Public webhook API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WebhookIngestResponse(BaseModel):
    status: str = Field(description="Acknowledgement status for the provider callback.")
    event_id: str = Field(description="POMPO public webhook event identifier.")
    duplicate: bool = Field(default=False, description="True when the provider event was already received.")


class WebhookEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_identifier: str
    provider_id: uuid.UUID
    provider_event_id: str
    transaction_id: uuid.UUID | None
    payment_attempt_id: uuid.UUID | None
    event_type: str
    event_version: str | None
    payment_reference: str | None
    provider_transaction_reference: str | None
    received_at: datetime
    processed_at: datetime | None
    processing_status: str
    processing_attempts: int
    signature_verified: bool
    timestamp_validated: bool
    failure_category: str | None
    failure_code: str | None
    payload: dict
