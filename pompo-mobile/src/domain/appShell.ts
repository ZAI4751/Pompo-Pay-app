/** Persistent app-shell routing: which routes show the bottom nav, and which tab is active. */

export type BottomNavActive = "home" | "history" | "profile" | "qr" | "activity";

function normalizePath(pathname: string): string {
  if (!pathname) {
    return "/";
  }
  if (pathname.length > 1 && pathname.endsWith("/")) {
    return pathname.slice(0, -1);
  }
  return pathname;
}

/**
 * Immersive payment/detail flows keep the shell-mounted nav out of the way.
 * Scan stays in the shell so Home → Scan does not slide the bar away.
 */
export function shouldShowBottomNav(pathname: string): boolean {
  const path = normalizePath(pathname);

  if (
    path === "/customer/preview" ||
    path === "/customer/confirm" ||
    path === "/customer/processing" ||
    path === "/customer/result" ||
    path === "/customer/methods/add"
  ) {
    return false;
  }
  if (path.startsWith("/customer/payment/")) {
    return false;
  }
  if (path.startsWith("/customer/pay-request/")) {
    return false;
  }
  if (path.startsWith("/customer/repeat/")) {
    return false;
  }
  if (/^\/customer\/methods\/[^/]+$/.test(path)) {
    return false;
  }
  if (/^\/customer\/requests\/[^/]+$/.test(path)) {
    return false;
  }
  if (path.startsWith("/merchant/payment/")) {
    return false;
  }
  if (/^\/merchant\/qr\/[^/]+$/.test(path)) {
    return false;
  }

  return path.startsWith("/customer") || path.startsWith("/merchant");
}

export function activeTabFromPathname(pathname: string): BottomNavActive {
  const path = normalizePath(pathname);

  if (path.startsWith("/merchant")) {
    if (path.startsWith("/merchant/activity")) {
      return "activity";
    }
    if (path.startsWith("/merchant/profile")) {
      return "profile";
    }
    if (path.startsWith("/merchant/qr")) {
      return "qr";
    }
    return "home";
  }

  if (path.startsWith("/customer/history") || path.startsWith("/customer/requests")) {
    return "history";
  }
  if (
    path.startsWith("/customer/profile") ||
    path.startsWith("/customer/notifications") ||
    path.startsWith("/customer/security") ||
    path.startsWith("/customer/methods") ||
    path.startsWith("/customer/preferences") ||
    path.startsWith("/customer/support") ||
    path.startsWith("/customer/merchants")
  ) {
    return "profile";
  }

  return "home";
}
