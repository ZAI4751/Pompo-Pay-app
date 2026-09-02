"""Deterministic matching of settlements to POMPO payments.

Never fuzzy-match. Ambiguous or unsafe identity becomes INVESTIGATION/UNMATCHED.
Does not mutate payment records.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import MismatchCategory, ReconciliationStatus, TransactionStatus
from app.models.payment import PaymentAttempt, Transaction
from app.models.settlement import Settlement
from app.payments.money import ZERO_MONEY, parse_money
from app.payments.pricing import FeeBreakdown


@dataclass(frozen=True)
class MatchIdentity:
    transaction: Transaction | None
    attempt: PaymentAttempt | None
    method: str | None
    ambiguous: bool


@dataclass(frozen=True)
class ReconciliationDecision:
    status: ReconciliationStatus
    category: MismatchCategory | None
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


def decide_identity(
    *,
    settlement: Settlement,
    by_payment_reference: Transaction | None,
    by_provider_reference: list[PaymentAttempt],
    existing_settlements_for_transaction: int,
) -> MatchIdentity:
    """Apply the matching hierarchy. Does not guess."""

    distinct_attempts = by_provider_reference
    distinct_tx_ids = {attempt.transaction_id for attempt in distinct_attempts}

    if by_payment_reference is not None:
        attempt = None
        matching_attempts = [
            item
            for item in distinct_attempts
            if item.transaction_id == by_payment_reference.id
        ]
        if matching_attempts:
            attempt = matching_attempts[0]
        elif by_payment_reference.attempts:
            attempt = by_payment_reference.attempts[-1]
        if len(distinct_tx_ids) > 1 and any(
            tx_id != by_payment_reference.id for tx_id in distinct_tx_ids
        ):
            return MatchIdentity(by_payment_reference, attempt, "payment_reference", True)
        return MatchIdentity(by_payment_reference, attempt, "payment_reference", False)

    if len(distinct_tx_ids) > 1:
        return MatchIdentity(None, None, "provider_reference", True)
    if len(distinct_tx_ids) == 1:
        attempt = distinct_attempts[0]
        return MatchIdentity(attempt.transaction, attempt, "provider_reference", False)

    if settlement.transaction_id is not None:
        return MatchIdentity(settlement.transaction, settlement.payment_attempt, "explicit_link", False)

    _ = existing_settlements_for_transaction
    return MatchIdentity(None, None, None, False)


def classify(
    *,
    settlement: Settlement,
    identity: MatchIdentity,
    expected: FeeBreakdown,
    payment_success_required: bool = True,
) -> ReconciliationDecision:
    actual_amount = parse_money(settlement.gross_amount)
    actual_provider_fee = parse_money(settlement.provider_fee)
    actual_pompo_fee = parse_money(settlement.pompo_fee)
    actual_currency = settlement.currency
    pompo_reference = identity.transaction.reference if identity.transaction else settlement.payment_reference
    provider_reference = (
        settlement.provider_transaction_reference or settlement.provider_settlement_reference
    )

    if identity.ambiguous:
        expected_amount = parse_money(identity.transaction.amount) if identity.transaction else None
        variance = (
            parse_money(actual_amount - expected_amount) if expected_amount is not None else None
        )
        return ReconciliationDecision(
            status=ReconciliationStatus.INVESTIGATION,
            category=MismatchCategory.PROVIDER_REFERENCE_MISMATCH,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            variance=variance,
            expected_provider_fee=expected.provider_cost,
            actual_provider_fee=actual_provider_fee,
            expected_pompo_fee=expected.pompo_fee,
            actual_pompo_fee=actual_pompo_fee,
            expected_currency=identity.transaction.currency if identity.transaction else None,
            actual_currency=actual_currency,
            pompo_reference=pompo_reference,
            provider_reference=provider_reference,
        )

    if identity.transaction is None:
        return ReconciliationDecision(
            status=ReconciliationStatus.UNMATCHED,
            category=MismatchCategory.MISSING_POMPO_TRANSACTION,
            expected_amount=None,
            actual_amount=actual_amount,
            variance=None,
            expected_provider_fee=expected.provider_cost,
            actual_provider_fee=actual_provider_fee,
            expected_pompo_fee=expected.pompo_fee,
            actual_pompo_fee=actual_pompo_fee,
            expected_currency=None,
            actual_currency=actual_currency,
            pompo_reference=settlement.payment_reference,
            provider_reference=provider_reference,
        )

    transaction = identity.transaction
    expected_amount = parse_money(transaction.amount)
    variance = parse_money(actual_amount - expected_amount)
    expected_currency = transaction.currency
    fee_mismatch = (
        actual_provider_fee != expected.provider_cost or actual_pompo_fee != expected.pompo_fee
    )
    amount_mismatch = actual_amount != expected_amount
    currency_mismatch = actual_currency != expected_currency
    status_ok = transaction.status is TransactionStatus.SUCCESS or not payment_success_required

    if amount_mismatch:
        return ReconciliationDecision(
            status=ReconciliationStatus.DISCREPANCY,
            category=MismatchCategory.AMOUNT_MISMATCH,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            variance=variance,
            expected_provider_fee=expected.provider_cost,
            actual_provider_fee=actual_provider_fee,
            expected_pompo_fee=expected.pompo_fee,
            actual_pompo_fee=actual_pompo_fee,
            expected_currency=expected_currency,
            actual_currency=actual_currency,
            pompo_reference=transaction.reference,
            provider_reference=provider_reference,
        )
    if currency_mismatch:
        return ReconciliationDecision(
            status=ReconciliationStatus.DISCREPANCY,
            category=MismatchCategory.CURRENCY_MISMATCH,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            variance=variance,
            expected_provider_fee=expected.provider_cost,
            actual_provider_fee=actual_provider_fee,
            expected_pompo_fee=expected.pompo_fee,
            actual_pompo_fee=actual_pompo_fee,
            expected_currency=expected_currency,
            actual_currency=actual_currency,
            pompo_reference=transaction.reference,
            provider_reference=provider_reference,
        )
    if fee_mismatch:
        return ReconciliationDecision(
            status=ReconciliationStatus.PARTIAL_MATCH,
            category=MismatchCategory.FEE_MISMATCH,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            variance=ZERO_MONEY,
            expected_provider_fee=expected.provider_cost,
            actual_provider_fee=actual_provider_fee,
            expected_pompo_fee=expected.pompo_fee,
            actual_pompo_fee=actual_pompo_fee,
            expected_currency=expected_currency,
            actual_currency=actual_currency,
            pompo_reference=transaction.reference,
            provider_reference=provider_reference,
        )
    if not status_ok:
        category = (
            MismatchCategory.TIMING_DISCREPANCY
            if transaction.status
            in {TransactionStatus.PENDING, TransactionStatus.PROCESSING, TransactionStatus.CREATED}
            else MismatchCategory.STATUS_MISMATCH
        )
        return ReconciliationDecision(
            status=ReconciliationStatus.PARTIAL_MATCH,
            category=category,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            variance=ZERO_MONEY,
            expected_provider_fee=expected.provider_cost,
            actual_provider_fee=actual_provider_fee,
            expected_pompo_fee=expected.pompo_fee,
            actual_pompo_fee=actual_pompo_fee,
            expected_currency=expected_currency,
            actual_currency=actual_currency,
            pompo_reference=transaction.reference,
            provider_reference=provider_reference,
        )
    return ReconciliationDecision(
        status=ReconciliationStatus.MATCHED,
        category=None,
        expected_amount=expected_amount,
        actual_amount=actual_amount,
        variance=ZERO_MONEY,
        expected_provider_fee=expected.provider_cost,
        actual_provider_fee=actual_provider_fee,
        expected_pompo_fee=expected.pompo_fee,
        actual_pompo_fee=actual_pompo_fee,
        expected_currency=expected_currency,
        actual_currency=actual_currency,
        pompo_reference=transaction.reference,
        provider_reference=provider_reference,
    )
