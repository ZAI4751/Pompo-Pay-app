/** User-facing API error mapping. Does not invent authorization decisions. */

export const GENERIC_VALIDATION_DETAIL = "Request validation failed";

const FIELD_REASON: Record<string, { missing: string; invalid: string }> = {
  email: { missing: "Email address is required", invalid: "Email address is invalid" },
  password: { missing: "Password is required", invalid: "Password does not meet requirements" },
  new_password: { missing: "Password is required", invalid: "Password does not meet requirements" },
  full_name: { missing: "Full name is required", invalid: "Full name is required" },
  phone: { missing: "Phone number is required", invalid: "Phone number is invalid" },
};

interface ValidationErrorEntry {
  loc: string[];
  msg: string;
  type: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function fieldName(loc: string[]): string {
  const parts = loc.filter((part) => part !== "body" && part !== "query" && part !== "path" && part !== "header");
  return parts[parts.length - 1] ?? "";
}

export function messageFromValidationError(error: ValidationErrorEntry): string {
  const field = fieldName(error.loc);
  const mapped = FIELD_REASON[field];
  const type = error.type;
  const msg = error.msg.toLowerCase();
  if (type === "missing") {
    return mapped?.missing ?? "Required field missing";
  }
  if (field === "email" || type.includes("email") || msg.includes("email address")) {
    return FIELD_REASON.email.invalid;
  }
  if (mapped) {
    return mapped.invalid;
  }
  return GENERIC_VALIDATION_DETAIL;
}

export function readFieldErrors(payload: unknown): ValidationErrorEntry[] {
  if (!isRecord(payload)) {
    return [];
  }
  const raw = Array.isArray(payload.errors)
    ? payload.errors
    : Array.isArray(payload.detail)
      ? payload.detail
      : [];
  return raw.filter(isRecord).map((entry) => ({
    loc: Array.isArray(entry.loc) ? entry.loc.map(String) : [],
    msg: String(entry.msg ?? ""),
    type: String(entry.type ?? ""),
  }));
}

export function messageFromApiPayload(payload: unknown, fallback: string): string {
  const fieldErrors = readFieldErrors(payload);
  if (fieldErrors.length > 0) {
    const messages: string[] = [];
    const seen = new Set<string>();
    for (const error of fieldErrors) {
      const message = messageFromValidationError(error);
      if (seen.has(message)) {
        continue;
      }
      seen.add(message);
      messages.push(message);
    }
    if (messages.length > 0 && !(messages.length === 1 && messages[0] === GENERIC_VALIDATION_DETAIL)) {
      return messages.join(". ");
    }
  }
  if (isRecord(payload) && typeof payload.detail === "string" && payload.detail.trim()) {
    if (payload.detail.trim() === GENERIC_VALIDATION_DETAIL) {
      return fallback;
    }
    return payload.detail.trim();
  }
  return fallback;
}
