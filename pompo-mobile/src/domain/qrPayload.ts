const PUBLIC_ID = /^[A-Z0-9-]{8,32}$/;
const PAYLOAD = /^POMPO:(\d+):(static|dynamic):([A-Z0-9-]{8,32}):/;
const CANONICAL_URL =
  /^(?:(?:https?|pompo):\/\/(?:[^/]+\/p\/|p\/)|\/p\/|pompo:\/p\/)([A-Z0-9-]{8,32})(?:[/?#&]|$)/i;

export type QrExtractResult =
  | { ok: true; publicIdentifier: string }
  | { ok: false; message: string };

/**
 * Extract the public identifier from a scanned string, universal HTTPS URL, or legacy payload.
 * Does not verify HMAC, amounts, or expiry — those are backend-authoritative.
 */
export function extractPublicIdentifier(raw: string): QrExtractResult {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { ok: false, message: "Empty QR payload" };
  }
  if (PUBLIC_ID.test(trimmed)) {
    return { ok: true, publicIdentifier: trimmed.toUpperCase() };
  }
  const urlMatch = CANONICAL_URL.exec(trimmed);
  if (urlMatch !== null) {
    return { ok: true, publicIdentifier: urlMatch[1].toUpperCase() };
  }
  const match = PAYLOAD.exec(trimmed);
  if (match === null) {
    return { ok: false, message: "This is not a POMPO QR code" };
  }
  if (match[1] !== "1") {
    return { ok: false, message: "Unsupported QR version" };
  }
  return { ok: true, publicIdentifier: match[3].toUpperCase() };
}
