/** Customer browser session and checkout-return persistence.

Admin sessions stay in `pompo_admin_session` (sessionStorage).
Customer tokens live in `localStorage` so a later visit can continue
payment while the refresh session is still valid. Tokens are never logged.
This is the same XSS model as the previous in-page JWTs; it is not a
httpOnly cookie migration.
*/

import { safeCheckoutReturnPath } from "@/lib/checkout/publicCheckout";
import {
  parseCheckoutDraftJson,
  parseCustomerSessionJson,
  type CheckoutDraft,
  type CustomerStoredSession,
} from "./sessionParsers";

export type { CheckoutDraft, CustomerStoredSession };
export { parseCheckoutDraftJson, parseCustomerSessionJson };

const SESSION_KEY = "pompo_customer_session";
const NOTICE_KEY = "pompo_customer_notice";
const CHECKOUT_DRAFT_KEY = "pompo_checkout_return";

function browserStorage(kind: "local" | "session"): Storage | null {
  if (typeof window === "undefined") return null;
  return kind === "local" ? window.localStorage : window.sessionStorage;
}

export function readCustomerSession(): CustomerStoredSession | null {
  const local = parseCustomerSessionJson(browserStorage("local")?.getItem(SESSION_KEY) ?? null);
  if (local) return local;
  const migrated = parseCustomerSessionJson(browserStorage("session")?.getItem(SESSION_KEY) ?? null);
  if (migrated) {
    writeCustomerSession(migrated);
    return migrated;
  }
  return null;
}

export function writeCustomerSession(session: CustomerStoredSession | null): void {
  const local = browserStorage("local");
  const tab = browserStorage("session");
  if (!local) return;
  if (session) {
    local.setItem(SESSION_KEY, JSON.stringify(session));
    tab?.removeItem(SESSION_KEY);
    return;
  }
  local.removeItem(SESSION_KEY);
  tab?.removeItem(SESSION_KEY);
}

export function writeCustomerNotice(message: string | null): void {
  const tab = browserStorage("session");
  if (!tab) return;
  if (message) {
    tab.setItem(NOTICE_KEY, message);
    return;
  }
  tab.removeItem(NOTICE_KEY);
}

export function readCustomerNotice(): string | null {
  return browserStorage("session")?.getItem(NOTICE_KEY) ?? null;
}

export function peekCheckoutDraft(): CheckoutDraft | null {
  const local = parseCheckoutDraftJson(browserStorage("local")?.getItem(CHECKOUT_DRAFT_KEY) ?? null);
  if (local) return local;
  return parseCheckoutDraftJson(browserStorage("session")?.getItem(CHECKOUT_DRAFT_KEY) ?? null);
}

export function writeCheckoutDraft(draft: CheckoutDraft | null): void {
  const local = browserStorage("local");
  const tab = browserStorage("session");
  if (!local) return;
  if (!draft) {
    local.removeItem(CHECKOUT_DRAFT_KEY);
    tab?.removeItem(CHECKOUT_DRAFT_KEY);
    return;
  }
  const path = safeCheckoutReturnPath(draft.path);
  if (!path) {
    local.removeItem(CHECKOUT_DRAFT_KEY);
    tab?.removeItem(CHECKOUT_DRAFT_KEY);
    return;
  }
  const payload: CheckoutDraft = { path };
  if (draft.amount?.trim()) payload.amount = draft.amount;
  if (draft.methodKey?.trim()) payload.methodKey = draft.methodKey;
  local.setItem(CHECKOUT_DRAFT_KEY, JSON.stringify(payload));
  tab?.removeItem(CHECKOUT_DRAFT_KEY);
}

export function clearCheckoutDraft(): void {
  writeCheckoutDraft(null);
}

export function resolveCheckoutReturnPath(candidate: string | null | undefined): string | null {
  return safeCheckoutReturnPath(candidate) ?? peekCheckoutDraft()?.path ?? null;
}
