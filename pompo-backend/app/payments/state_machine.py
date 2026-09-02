"""Central transaction lifecycle rules."""

from __future__ import annotations

from app.models.enums import TransactionStatus


class InvalidTransactionTransition(ValueError):
    """Raised when a transaction status change is not permitted."""


TRANSITIONS: dict[TransactionStatus, frozenset[TransactionStatus]] = {
    TransactionStatus.CREATED: frozenset(
        {TransactionStatus.PENDING, TransactionStatus.CANCELLED, TransactionStatus.QR_GENERATED}
    ),
    TransactionStatus.QR_GENERATED: frozenset(
        {TransactionStatus.PENDING, TransactionStatus.CANCELLED}
    ),
    TransactionStatus.PENDING: frozenset(
        {TransactionStatus.PROCESSING, TransactionStatus.CANCELLED}
    ),
    TransactionStatus.PROCESSING: frozenset(
        {TransactionStatus.SUCCESS, TransactionStatus.FAILED, TransactionStatus.TIMEOUT}
    ),
    TransactionStatus.SUCCESS: frozenset({TransactionStatus.REFUNDED}),
}

# PENDING_USER_PIN remains on the enum for a future PIN checkout flow.


def validate_transition(current: TransactionStatus, target: TransactionStatus) -> None:
    if target not in TRANSITIONS.get(current, frozenset()):
        raise InvalidTransactionTransition(
            f"Cannot transition transaction from {current.value} to {target.value}"
        )
