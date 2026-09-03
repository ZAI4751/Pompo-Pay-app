import type { PaymentMethod, PaymentMethodCatalogItem } from "@/types";

const AUTH_REQUIRED = new Set([
  "required",
  "waiting_provider",
  "open_provider_flow",
  "credential_required",
  "otp_required",
]);

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
  if (!item.available) {
    return item.reason ?? "Coming soon";
  }
  if (item.is_sandbox) {
    return "AVAILABLE · SANDBOX";
  }
  return "AVAILABLE";
}
