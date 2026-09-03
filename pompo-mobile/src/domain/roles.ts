import type { AppMode } from "@/types";

const MERCHANT_ROLES = new Set([
  "merchant_owner",
  "branch_manager",
  "cashier",
]);

export function canUseMerchantMode(roleCode: string, merchantId?: string | null): boolean {
  if (roleCode === "platform_admin") {
    return Boolean(merchantId);
  }
  return MERCHANT_ROLES.has(roleCode);
}

export function defaultMode(_roleCode?: string): AppMode {
  return "customer";
}

export function canCreateQr(roleCode: string, merchantId?: string | null): boolean {
  if (roleCode === "platform_admin") {
    return Boolean(merchantId);
  }
  return roleCode === "merchant_owner" || roleCode === "branch_manager";
}

export function canRevokeQr(roleCode: string, merchantId?: string | null): boolean {
  if (roleCode === "platform_admin") {
    return Boolean(merchantId);
  }
  return roleCode === "merchant_owner";
}
