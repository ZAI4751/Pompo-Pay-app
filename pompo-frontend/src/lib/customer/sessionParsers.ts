/** Pure parsers for customer session and checkout-return payloads. */

export interface CustomerStoredSession {
  accessToken: string;
  refreshToken: string;
}

export interface CheckoutDraft {
  path: string;
  amount?: string;
  methodKey?: string;
}

const CHECKOUT_PATH = /^\/p\/[A-Za-z0-9._~-]+$/;

function allowlistedCheckoutPath(value: string | null | undefined): string | null {
  if (!value) return null;
  const pathOnly = value.trim().split(/[?#]/, 1)[0] ?? "";
  if (!CHECKOUT_PATH.test(pathOnly)) return null;
  return pathOnly;
}

export function parseCustomerSessionJson(raw: string | null): CustomerStoredSession | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (typeof parsed.accessToken === "string" && typeof parsed.refreshToken === "string") {
      return { accessToken: parsed.accessToken, refreshToken: parsed.refreshToken };
    }
    return null;
  } catch {
    return null;
  }
}

export function parseCheckoutDraftJson(raw: string | null): CheckoutDraft | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const path = allowlistedCheckoutPath(typeof parsed.path === "string" ? parsed.path : null);
    if (!path) return null;
    const amount = typeof parsed.amount === "string" && parsed.amount.trim() ? parsed.amount : undefined;
    const methodKey =
      typeof parsed.methodKey === "string" && parsed.methodKey.trim() ? parsed.methodKey : undefined;
    return { path, amount, methodKey };
  } catch {
    return null;
  }
}
