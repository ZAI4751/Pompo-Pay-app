"""Smallest forward-compatible POMPO pricing calculator.

Not a billing platform. Supports zero, fixed, and percentage fees with optional
min/max POMPO fee bounds, plus provider-specific cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import FeeType
from app.models.settlement import PricingSchedule
from app.payments.money import ZERO_MONEY, merchant_net, parse_money, percentage_of, quantize_derived


@dataclass(frozen=True)
class FeeBreakdown:
    gross: Decimal
    provider_cost: Decimal
    pompo_fee: Decimal
    merchant_net: Decimal
    currency: str


def _component_amount(
    *,
    gross: Decimal,
    fee_type: FeeType,
    fixed: Decimal,
    basis_points: int,
) -> Decimal:
    if fee_type is FeeType.ZERO:
        return ZERO_MONEY
    if fee_type is FeeType.FIXED:
        return parse_money(fixed)
    if fee_type is FeeType.PERCENTAGE:
        return percentage_of(gross, basis_points)
    raise ValueError(f"Unsupported fee type: {fee_type}")


def apply_schedule(gross: Decimal, schedule: PricingSchedule | None, currency: str) -> FeeBreakdown:
    """Calculate expected provider cost and POMPO fee for a gross amount."""

    amount = parse_money(gross)
    if schedule is None:
        return FeeBreakdown(
            gross=amount,
            provider_cost=ZERO_MONEY,
            pompo_fee=ZERO_MONEY,
            merchant_net=amount,
            currency=currency,
        )

    provider_cost = _component_amount(
        gross=amount,
        fee_type=schedule.provider_cost_type,
        fixed=schedule.provider_cost_fixed,
        basis_points=schedule.provider_cost_percentage_bps,
    )
    pompo_fee = _component_amount(
        gross=amount,
        fee_type=schedule.pompo_fee_type,
        fixed=schedule.pompo_fixed_amount,
        basis_points=schedule.pompo_percentage_bps,
    )
    if schedule.pompo_min_fee is not None and pompo_fee < parse_money(schedule.pompo_min_fee):
        pompo_fee = parse_money(schedule.pompo_min_fee)
    if schedule.pompo_max_fee is not None and pompo_fee > parse_money(schedule.pompo_max_fee):
        pompo_fee = parse_money(schedule.pompo_max_fee)
    pompo_fee = quantize_derived(pompo_fee)
    net = merchant_net(gross=amount, provider_fee=provider_cost, pompo_fee=pompo_fee)
    return FeeBreakdown(
        gross=amount,
        provider_cost=provider_cost,
        pompo_fee=pompo_fee,
        merchant_net=net,
        currency=currency,
    )


def pricing_scope_key(
    *,
    provider_id: str | None,
    merchant_id: str | None,
    currency: str,
) -> str:
    return f"{provider_id or 'platform'}:{merchant_id or 'all'}:{currency.upper()}"
