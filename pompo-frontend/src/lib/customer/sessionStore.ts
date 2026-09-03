/** sessionStorage adapter for the public-web customer identity.

Admin sessions stay in `pompo_admin_session`. This store never logs tokens.
*/

const SESSION_KEY = "pompo_customer_session";

export interface CustomerStoredSession {
  accessToken: string;
  refreshToken: string;
}

export function readCustomerSession(): CustomerStoredSession | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(SESSION_KEY);
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

export function writeCustomerSession(session: CustomerStoredSession | null): void {
  if (typeof window === "undefined") return;
  if (session) {
    window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    return;
  }
  window.sessionStorage.removeItem(SESSION_KEY);
}

const NOTICE_KEY = "pompo_customer_notice";

export function writeCustomerNotice(message: string | null): void {
  if (typeof window === "undefined") return;
  if (message) {
    window.sessionStorage.setItem(NOTICE_KEY, message);
    return;
  }
  window.sessionStorage.removeItem(NOTICE_KEY);
}

export function readCustomerNotice(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(NOTICE_KEY);
}
