"""Bounded retry classification for provider attempts.

The database remains the financial identity authority. This module does not
auto-retry inside a single HTTP request; it tells the payment core whether a
new attempt is permitted.
"""

from __future__ import annotations

from app.payments.providers import ProviderError, ProviderErrorCode, RetryClass, retry_class_for

MAX_PROVIDER_ATTEMPTS = 3


def classify_retry(code: ProviderErrorCode) -> RetryClass:
    return retry_class_for(code)


def should_open_new_attempt(
    *,
    attempt_number: int,
    retryable: bool,
    max_attempts: int = MAX_PROVIDER_ATTEMPTS,
) -> bool:
    return retryable and attempt_number < max_attempts


def should_retry_error(error: ProviderError, attempt_number: int) -> bool:
    return should_open_new_attempt(attempt_number=attempt_number, retryable=error.retryable)
