"""Versioned POMPO QR payload format with HMAC tamper protection."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.models.enums import QRType

POMPO_QR_PREFIX = "POMPO"
SUPPORTED_VERSION = 1
_SIGNATURE_LENGTH = 22

# POMPO:<version>:<type>:<public_id>:<body...>:<signature>
_PAYLOAD_PATTERN = re.compile(
    r"^POMPO:(\d+):(static|dynamic):([A-Z0-9-]{8,32})(?::(.+))?:([A-Za-z0-9_-]{22})$"
)
_PUBLIC_ID_PATTERN = re.compile(r"^[A-Z0-9-]{8,32}$")
_URL_PATTERN = re.compile(
    r"^(?:(?:https?|pompo)://[^/]+)?/p/([A-Z0-9-]{8,32})(?:[/?#].*)?$", re.IGNORECASE
)
_SCHEME_PATTERN = re.compile(
    r"^pompo:(?:/p/|//p/)([A-Z0-9-]{8,32})(?:[/?#].*)?$", re.IGNORECASE
)


def extract_public_identifier(raw: str) -> str | None:
    """Extract public identifier from a raw string, URL, scheme, or legacy payload."""
    normalized = raw.strip()
    if not normalized:
        return None
    if _PUBLIC_ID_PATTERN.match(normalized):
        return normalized
    url_match = _URL_PATTERN.match(normalized)
    if url_match:
        return url_match.group(1).upper()
    scheme_match = _SCHEME_PATTERN.match(normalized)
    if scheme_match:
        return scheme_match.group(1).upper()
    payload_match = _PAYLOAD_PATTERN.match(normalized)
    if payload_match:
        return payload_match.group(3)
    return None


class QRPayloadError(ValueError):
    """Raised when a QR payload cannot be parsed or verified."""


@dataclass(frozen=True)
class ParsedQRPayload:
    version: int
    qr_type: QRType
    public_identifier: str
    signature: str
    amount: Decimal | None = None
    currency: str | None = None
    expires_at: datetime | None = None
    payment_reference: str | None = None


class QRPayloadService:
    """Deterministic encode/decode for the internal POMPO QR protocol."""

    def __init__(self, signing_key: str) -> None:
        if len(signing_key) < 32:
            raise ValueError("QR signing key must be at least 32 characters")
        self._signing_key = signing_key.encode()

    def encode_static(self, *, public_identifier: str, version: int = SUPPORTED_VERSION) -> str:
        body = ""
        signature = self._sign(version, QRType.STATIC, public_identifier, body)
        return f"{POMPO_QR_PREFIX}:{version}:static:{public_identifier}:{signature}"

    def encode_dynamic(
        self,
        *,
        public_identifier: str,
        amount: Decimal,
        currency: str,
        expires_at: datetime,
        payment_reference: str,
        version: int = SUPPORTED_VERSION,
    ) -> str:
        amount_minor = self._amount_minor(amount)
        expiry_unix = int(expires_at.timestamp())
        body = f"{amount_minor}:{currency.upper()}:{expiry_unix}:{payment_reference}"
        signature = self._sign(version, QRType.DYNAMIC, public_identifier, body)
        return f"{POMPO_QR_PREFIX}:{version}:dynamic:{public_identifier}:{body}:{signature}"

    def parse(self, raw_payload: str) -> ParsedQRPayload:
        normalized = raw_payload.strip()
        match = _PAYLOAD_PATTERN.match(normalized)
        if match is None:
            raise QRPayloadError("Malformed QR payload")
        version = int(match.group(1))
        if version != SUPPORTED_VERSION:
            raise QRPayloadError(f"Unsupported QR version: {version}")
        qr_type = QRType(match.group(2))
        public_id = match.group(3)
        body = match.group(4) or ""
        signature = match.group(5)
        expected = self._sign(version, qr_type, public_id, body)
        if not hmac.compare_digest(signature, expected):
            raise QRPayloadError("Invalid QR signature")
        parsed = ParsedQRPayload(
            version=version,
            qr_type=qr_type,
            public_identifier=public_id,
            signature=signature,
        )
        if qr_type is QRType.DYNAMIC:
            if not body:
                raise QRPayloadError("Dynamic QR payload missing payment context")
            parts = body.split(":")
            if len(parts) != 4:
                raise QRPayloadError("Invalid dynamic QR body")
            amount_minor, currency, expiry_unix, payment_reference = parts
            try:
                minor = int(amount_minor)
                expiry = int(expiry_unix)
            except ValueError as exc:
                raise QRPayloadError("Invalid dynamic QR numeric fields") from exc
            return ParsedQRPayload(
                version=version,
                qr_type=qr_type,
                public_identifier=public_id,
                signature=signature,
                amount=Decimal(minor) / Decimal(100),
                currency=currency.upper(),
                expires_at=datetime.fromtimestamp(expiry, tz=UTC),
                payment_reference=payment_reference,
            )
        return parsed

    def _sign(self, version: int, qr_type: QRType, public_id: str, body: str) -> str:
        message = f"{version}|{qr_type.value}|{public_id}|{body}".encode()
        digest = hmac.new(self._signing_key, message, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")[:_SIGNATURE_LENGTH]

    @staticmethod
    def _amount_minor(amount: Decimal) -> int:
        return int(amount.quantize(Decimal("0.01")) * 100)
