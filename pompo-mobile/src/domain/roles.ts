import type { AppMode } from "@/types";

const MERCHANT_ROLES = new Set([
  "merchant_owner",
  "branch_manager",
  "cashier",
  "platform_admin",
]);

export function canUseMerchantMode(roleCode: string): boolean {
  return MERCHANT_ROLES.has(roleCode);
}

export function defaultMode(roleCode: string): AppMode {
  return canUseMerchantMode(roleCode) ? "merchant" : "customer";
}

export function canCreateQr(roleCode: string): boolean {
  return roleCode === "merchant_owner" || roleCode === "branch_manager" || roleCode === "platform_admin";
}

export function canRevokeQr(roleCode: string): boolean {
  return roleCode === "merchant_owner" || roleCode === "platform_admin";
}
