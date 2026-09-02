"""Provider-neutral settlement ingestion contracts.

Real Airtel/TNM/bank settlement formats are deferred until authoritative
documentation exists. The simulated adapter implements a deterministic fixture.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from app.payments.credentials import ProviderCredentials
from app.payments.money import MoneyError, parse_money
from app.payments.webhooks import WebhookVerificationResult, verify_mock_signature


@dataclass(frozen=True)
class NormalizedSettlementRecord:
    provider_settlement_reference: str
    payment_reference: str | None
    provider_transaction_reference: str | None
    gross_amount: Decimal
    provider_fee: Decimal | None
    currency: str
    settlement_date: date
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedSettlementBatch:
    external_batch_reference: str
    settlement_date: date
    currency: str
    records: tuple[NormalizedSettlementRecord, ...]


class SettlementAdapter(Protocol):
    """Optional settlement contract layered on payment provider adapters."""

    async def verify_settlement(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
        credentials: ProviderCredentials,
    ) -> WebhookVerificationResult: ...

    async def parse_settlement(
        self,
        *,
        headers: dict[str, str],
        body: bytes,
    ) -> NormalizedSettlementBatch: ...


def _parse_date(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value.strip():
        return date.fromisoformat(value.strip())
    raise ValueError("Missing or invalid settlement date")


def parse_mock_settlement_body(body: bytes) -> NormalizedSettlementBatch:
    try:
        payload = json.loads(body.decode())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Malformed settlement JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Settlement payload must be a JSON object")

    batch_reference = payload.get("batch_reference") or payload.get("external_batch_reference")
    if not isinstance(batch_reference, str) or not batch_reference.strip():
        raise ValueError("Missing batch reference")

    records_raw = payload.get("records")
    if not isinstance(records_raw, list) or not records_raw:
        raise ValueError("Settlement batch must contain records")

    currency = str(payload.get("currency") or "MWK").upper()
    settlement_date = _parse_date(payload.get("settlement_date"))
    records: list[NormalizedSettlementRecord] = []
    seen_refs: set[str] = set()

    for item in records_raw:
        if not isinstance(item, dict):
            raise ValueError("Each settlement record must be a JSON object")
        reference = item.get("settlement_reference") or item.get("provider_settlement_reference")
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("Missing provider settlement reference")
        ref = reference.strip()
        if ref in seen_refs:
            raise ValueError("Duplicate settlement reference in batch payload")
        seen_refs.add(ref)

        payment_reference = item.get("payment_reference")
        provider_txn = item.get("provider_transaction_id") or item.get(
            "provider_transaction_reference"
        )
        try:
            gross = parse_money(item.get("gross_amount"))
        except (MoneyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid gross amount") from exc
        provider_fee_raw = item.get("provider_fee")
        provider_fee = None
        if provider_fee_raw is not None:
            try:
                provider_fee = parse_money(provider_fee_raw)
            except (MoneyError, TypeError, ValueError) as exc:
                raise ValueError("Invalid provider fee") from exc

        record_currency = str(item.get("currency") or currency).upper()
        record_date = (
            _parse_date(item["settlement_date"]) if item.get("settlement_date") else settlement_date
        )
        metadata: dict[str, str] = {}
        for key, value in item.items():
            if key in {
                "settlement_reference",
                "provider_settlement_reference",
                "payment_reference",
                "provider_transaction_id",
                "provider_transaction_reference",
                "gross_amount",
                "provider_fee",
                "currency",
                "settlement_date",
            }:
                continue
            if isinstance(value, (str, int, bool)):
                metadata[key] = str(value)

        records.append(
            NormalizedSettlementRecord(
                provider_settlement_reference=ref,
                payment_reference=str(payment_reference).strip() if payment_reference else None,
                provider_transaction_reference=str(provider_txn).strip() if provider_txn else None,
                gross_amount=gross,
                provider_fee=provider_fee,
                currency=record_currency,
                settlement_date=record_date,
                metadata=metadata,
            )
        )

    return NormalizedSettlementBatch(
        external_batch_reference=batch_reference.strip(),
        settlement_date=settlement_date,
        currency=currency,
        records=tuple(records),
    )


def verify_mock_settlement(
    *,
    headers: dict[str, str],
    body: bytes,
    secret: str | None,
) -> WebhookVerificationResult:
    return verify_mock_signature(headers=headers, body=body, secret=secret)
