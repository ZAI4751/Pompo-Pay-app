"""Opaque payment-instrument token references.

POMPO stores HMAC-SHA256 digests of provider-issued or sandbox tokens.
The digest is not reversible. PINs, CVVs, PANs, and passwords never enter
this module.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets


FORBIDDEN_ENROLL_KEYS = frozenset(
    {
        "pin",
        "cvv",
        "cvc",
        "pan",
        "card_number",
        "password",
        "secret",
        "otp",
        "access_token",
    }
)

_MSISDN_DIGITS = re.compile(r"\D+")


def digest_token(secret: str, token: str) -> str:
    return hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def new_sandbox_token() -> str:
    return f"simtok_{secrets.token_hex(16)}"


def reject_secret_fields(payload: dict) -> None:
    lowered = {str(key).lower() for key in payload}
    overlap = lowered & FORBIDDEN_ENROLL_KEYS
    if overlap:
        raise ValueError("Provider secrets cannot be stored on POMPO")


def normalize_msisdn(raw: str) -> str:
    digits = _MSISDN_DIGITS.sub("", raw)
    if len(digits) < 9 or len(digits) > 15:
        raise ValueError("Enter a valid mobile-money number")
    if digits.startswith("0"):
        digits = f"265{digits[1:]}"
    if not digits.startswith("265") and len(digits) == 9:
        digits = f"265{digits}"
    return f"+{digits}"


def mask_msisdn(e164: str) -> str:
    digits = _MSISDN_DIGITS.sub("", e164)
    if len(digits) < 6:
        raise ValueError("Enter a valid mobile-money number")
    return f"+{digits[:3]} {digits[3:5]}•• ••{digits[-2:]}"


def mask_card_last4(last4: str) -> str:
    cleaned = re.sub(r"\D", "", last4)
    if len(cleaned) != 4:
        raise ValueError("Card enrollment stores only a 4-digit masked identifier")
    return f"•••• {cleaned}"
