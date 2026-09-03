/** Pure helpers for the public `/p/[publicIdentifier]` checkout.

These do not invent merchants, methods, or payment states. They only
format and classify values returned by the backend.
*/

export type CheckoutPhase =
  | "loading"
  | "ready"
  | "auth_required"
  | "verify_email"
  | "forgot_password"
  | "processing"
  | "pending"
  | "success"
  | "failure"
  | "expired"
  | "revoked"
  | "consumed"
  | "not_found"
  | "network_error"
  | "unsupported_method";

export type MethodBadge =
  | "AVAILABLE"
  | "NOT AVAILABLE"
  | "REQUIRES AUTHORIZATION"
  | "REVOKED"
  | "SANDBOX"
  | "COMING SOON";

const AUTH_REQUIRED = new Set([
  "required",
  "waiting_provider",
  "open_provider_flow",
  "credential_required",
  "otp_required",
]);

const INTERNAL_ERROR_MARKERS = [
  "traceback",
  "sqlalchemy",
  "psycopg",
  "exception",
  "internal server error",
  "starlette",
  "uvicorn",
  "stack trace",
];

export function isTerminalPaymentStatus(status: string | null | undefined): boolean {
  return status === "success" || status === "failed" || status === "cancelled";
}

/** Never treat a still-pending payment as a failure. */
export function checkoutPhaseFromPayment(status: string | null | undefined): "success" | "failure" | "pending" {
  if (status === "success") return "success";
  if (status === "failed" || status === "cancelled") return "failure";
  return "pending";
}

export function humanizeCustomerError(
  message: string | null | undefined,
  fallback: string,
): string {
  if (!message) return fallback;
  const trimmed = message.trim();
  if (!trimmed) return fallback;
  const lower = trimmed.toLowerCase();
  if (INTERNAL_ERROR_MARKERS.some((marker) => lower.includes(marker))) {
    return fallback;
  }
  if (trimmed.length > 180) return fallback;
  return trimmed;
}

export function formatMoney(amount: string | number | null | undefined, currency = "MWK"): string {
  if (amount === null || amount === undefined || amount === "") {
    return `${currency} —`;
  }
  const numeric = typeof amount === "number" ? amount : Number(amount);
  if (!Number.isFinite(numeric)) {
    return `${currency} ${String(amount)}`;
  }
  return `${currency} ${numeric.toLocaleString("en-MW", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function sanitizeAmountInput(raw: string): string {
  const cleaned = raw.replace(/[^\d.]/g, "");
  const firstDot = cleaned.indexOf(".");
  if (firstDot === -1) return cleaned;
  return `${cleaned.slice(0, firstDot + 1)}${cleaned.slice(firstDot + 1).replace(/\./g, "").slice(0, 2)}`;
}

export function validateStaticAmount(val: string): string | null {
  const cleaned = val.trim();
  if (!cleaned) return "Enter the amount you want to pay.";
  const num = Number(cleaned);
  if (!Number.isFinite(num) || num <= 0) return "Enter a valid amount greater than 0.";
  if (num < 1) return "Minimum payment is MWK 1.00.";
  if (num > 50_000_000) return "Amount exceeds the maximum of MWK 50,000,000.";
  return null;
}

export function catalogMethodPresentation(item: {
  available: boolean;
  is_sandbox: boolean;
  reason: string | null;
  authorization_state: string;
}): { selectable: boolean; badges: MethodBadge[]; detail: string } {
  const badges: MethodBadge[] = [];
  const state = (item.authorization_state || "").toLowerCase();
  const reason = item.reason || "";
  const comingSoon = /coming soon/i.test(reason);

  if (state === "revoked") {
    badges.push("REVOKED");
  } else if (AUTH_REQUIRED.has(state)) {
    badges.push("REQUIRES AUTHORIZATION");
  } else if (comingSoon || state === "unsupported") {
    badges.push(comingSoon ? "COMING SOON" : "NOT AVAILABLE");
  } else if (item.available) {
    badges.push("AVAILABLE");
  } else {
    badges.push("NOT AVAILABLE");
  }

  if (item.is_sandbox) {
    badges.push("SANDBOX");
  }

  return {
    selectable: item.available && !AUTH_REQUIRED.has(state) && state !== "revoked" && state !== "unsupported",
    badges,
    detail: humanizeCustomerError(reason, item.available ? "Ready to pay" : "Not available for this payment"),
  };
}

export function shouldShowAppInvitation(phase: CheckoutPhase): boolean {
  return phase === "success";
}

export function paymentCtaLabel(options: {
  authenticated: boolean;
  currency: string;
  amount: string | null | undefined;
  qrType: "static" | "dynamic";
}): string {
  const money =
    options.qrType === "dynamic" || options.amount
      ? formatMoney(options.amount, options.currency)
      : null;
  if (!options.authenticated) {
    return money ? `Continue · ${money}` : "Continue";
  }
  return money ? `Pay ${money}` : "Pay";
}

export function formatReceiptTimestamp(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("en-MW", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export const PUBLIC_CHECKOUT_ORIGIN = "https://pay.pompo.mw";
