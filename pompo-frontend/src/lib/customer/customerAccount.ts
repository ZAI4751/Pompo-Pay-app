/** Pure helpers for the lightweight public-web customer account. */

export const DEACTIVATION_CONFIRMATION = "DEACTIVATE";

export type AccountSection = "profile" | "activity" | "receipts" | "security" | "care";

export const ACCOUNT_NAV: Array<{ href: string; label: string; section: AccountSection }> = [
  { href: "/account", label: "Profile", section: "profile" },
  { href: "/account/activity", label: "Activity", section: "activity" },
  { href: "/account/receipts", label: "Receipts", section: "receipts" },
  { href: "/account/security", label: "Security", section: "security" },
  { href: "/account/care", label: "Customer Care", section: "care" },
];

export function isReceiptEligible(status: string | null | undefined): boolean {
  return status === "success";
}

export function emailDeliveryCopy(delivery: string | null | undefined, sentFallback: string): string {
  if (delivery === "not_configured") {
    return "Email delivery is not configured on this POMPO environment. Use the POMPO app or contact customer care if you need help.";
  }
  return sentFallback;
}

export function securityStateCopy(user: {
  is_active: boolean;
  is_email_verified?: boolean;
  account_status?: string;
}): { email: string; account: string; mfa: string } {
  const status = (user.account_status || (user.is_active ? "active" : "inactive")).toLowerCase();
  return {
    email: user.is_email_verified ? "Email verified" : "Email not verified",
    account: status === "deactivated" ? "Account deactivated" : user.is_active ? "Account active" : "Account inactive",
    mfa: "Two-factor authentication is not available on POMPO yet.",
  };
}

export function isCustomerRole(roleCode: string | null | undefined): boolean {
  return !roleCode || roleCode === "customer";
}

export function confirmationMatchesDeactivate(value: string): boolean {
  return value.trim() === DEACTIVATION_CONFIRMATION;
}
