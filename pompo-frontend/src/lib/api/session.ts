/**
 * In-memory session bridge so service modules can attach a Bearer token
 * without importing React. Admin AuthContext writes the admin token;
 * CustomerSessionProvider writes the customer token. Tokens are never logged.
 */

let adminAccessToken: string | null = null;
let customerAccessToken: string | null = null;
let onAdminUnauthorized: (() => void) | null = null;
let onCustomerUnauthorized: (() => void) | null = null;

export function isCustomerWebSurface(pathname?: string): boolean {
  const path =
    pathname ?? (typeof window !== "undefined" ? window.location.pathname : "");
  return path.startsWith("/p/") || path === "/p" || path.startsWith("/account");
}

export function setAccessToken(token: string | null): void {
  adminAccessToken = token;
}

export function setCustomerAccessToken(token: string | null): void {
  customerAccessToken = token;
}

export function getAccessToken(): string | null {
  return isCustomerWebSurface() ? customerAccessToken : adminAccessToken;
}

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onAdminUnauthorized = handler;
}

export function setCustomerUnauthorizedHandler(handler: (() => void) | null): void {
  onCustomerUnauthorized = handler;
}

export function notifyUnauthorized(): void {
  if (isCustomerWebSurface()) {
    onCustomerUnauthorized?.();
    return;
  }
  onAdminUnauthorized?.();
}
