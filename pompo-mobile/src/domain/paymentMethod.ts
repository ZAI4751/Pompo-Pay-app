import type { PaymentMethod, PaymentMethodCatalogItem } from "@/types";

const AUTH_REQUIRED = new Set([
  "required",
  "waiting_provider",
  "open_provider_flow",
  "credential_required",
  "otp_required",
]);

export function catalogMethodSelectable(item: PaymentMethodCatalogItem): boolean {
  const state = item.authorization_state.toLowerCase();
  return item.available && !AUTH_REQUIRED.has(state) && state !== "revoked" && state !== "unsupported";
}

export function paymentMethodChargeable(row: PaymentMethod): boolean {
  if (row.status !== "active") {
    return false;
  }
  if (row.authorization_state === "failed" || row.authorization_state === "unsupported") {
    return false;
  }
  return !AUTH_REQUIRED.has(row.authorization_state);
}

export function paymentMethodStateLabel(row: PaymentMethod): string {
  const parts: string[] = [];
  if (row.status === "revoked") {
    parts.push("REVOKED");
  } else if (row.status === "expired" || row.status === "inactive") {
    parts.push("NOT AVAILABLE");
  } else if (AUTH_REQUIRED.has(row.authorization_state) || row.authorization_state === "failed") {
    parts.push("REQUIRES AUTHORIZATION");
  } else if (row.status === "active") {
    parts.push("AVAILABLE");
  } else {
    parts.push(row.status.toUpperCase());
  }
  if (row.is_sandbox) {
    parts.push("SANDBOX");
  }
  if (row.is_default) {
    parts.push("DEFAULT");
  }
  return parts.join(" · ");
}

export function catalogOfferLabel(item: PaymentMethodCatalogItem): string {
  const state = item.authorization_state.toLowerCase();
  if (/coming soon/i.test(item.reason ?? "") || state === "unsupported") {
    return "Coming soon";
  }
  if (!catalogMethodSelectable(item)) {
    if (AUTH_REQUIRED.has(state)) {
      return "Requires authorization";
    }
    return item.reason ?? "Not available for this payment";
  }
  if (item.is_sandbox) {
    return "AVAILABLE · SANDBOX";
  }
  return "AVAILABLE";
}
