"""Exact monetary arithmetic for POMPO financial records.

Never use floating point. Incoming amounts must already have at most two
decimal places; derived percentage fees use an explicit ROUND_HALF_UP policy.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

MONEY_QUANTUM = Decimal("0.01")
ZERO_MONEY = Decimal("0.00")


class MoneyError(ValueError):
    """Raised when a value cannot be accepted as exact money."""


def parse_money(value: Decimal | int | str) -> Decimal:
    """Parse an exact 2-decimal money amount. Does not silently round."""

    if isinstance(value, float):
        raise MoneyError("Floating point amounts are not allowed")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as exc:
        raise MoneyError("Amount is not a valid decimal") from exc
    if not amount.is_finite():
        raise MoneyError("Amount must be finite")
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise MoneyError("Amount must have at most 2 decimal places")
    return amount.quantize(MONEY_QUANTUM)


def quantize_derived(value: Decimal) -> Decimal:
    """Explicit rounding for derived fees (percentage of gross)."""

    if not value.is_finite():
        raise MoneyError("Derived amount must be finite")
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def percentage_of(gross: Decimal, basis_points: int) -> Decimal:
    """Return ``gross * bps / 10000`` quantized to 2 decimal places."""

    if basis_points < 0:
        raise MoneyError("Basis points must be non-negative")
    return quantize_derived(parse_money(gross) * Decimal(basis_points) / Decimal(10000))


def money_sum(*values: Decimal) -> Decimal:
    total = ZERO_MONEY
    for value in values:
        total += parse_money(value)
    return parse_money(total)


def merchant_net(*, gross: Decimal, provider_fee: Decimal, pompo_fee: Decimal) -> Decimal:
    return parse_money(parse_money(gross) - parse_money(provider_fee) - parse_money(pompo_fee))
