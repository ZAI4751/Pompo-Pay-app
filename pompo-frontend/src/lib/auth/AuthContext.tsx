"use client";

/**
 * Owns the session lifecycle: login, silent token refresh, logout, and
 * "session expired -> redirect to /login". API call sites report success/
 * error; this context is the only place that ends a session.
 *
 * Tokens live in memory plus sessionStorage (not localStorage, not cookies).
 *
 * Effective permissions are loaded from GET /rbac/roles/{role_id}
 * (permission_codes). /auth/me does not expose them. If that call is
 * forbidden, permissionCodes stays null and the UI does not invent grants.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { authService } from "@/lib/api/services/auth";
import { apiRequest } from "@/lib/api/client";
import { USE_MOCKS } from "@/lib/api/config";
import { isCustomerWebSurface, setAccessToken, setUnauthorizedHandler } from "@/lib/api/session";
import { getDemoAdminUser, mockRoleDetails } from "@/mocks/data";
import type { AuthenticatedUser } from "@/lib/types/auth";
import type { Role } from "@/lib/types/rbac";
import type { ApiErrorKind } from "@/lib/types/common";

interface LiveSession {
  kind: "live";
  accessToken: string;
  refreshToken: string;
}

interface DemoSession {
  kind: "demo";
}

type Session = LiveSession | DemoSession;

interface LoginOutcome {
  ok: boolean;
  error?: string;
  kind?: ApiErrorKind;
  httpStatus?: number;
  requestId?: string;
}

interface AuthContextValue {
  user: AuthenticatedUser | null;
  status: "loading" | "authenticated" | "unauthenticated";
  isDemoSession: boolean;
  /** null = unknown (do not invent). Loaded from the role API or demo catalog. */
  permissionCodes: string[] | null;
  login: (email: string, password: string) => Promise<LoginOutcome>;
  enterDemoSession: () => LoginOutcome;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const SESSION_KEY = "pompo_admin_session";

function readStoredSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (parsed.kind === "demo") return { kind: "demo" };
    if (parsed.kind === "live" && typeof parsed.accessToken === "string" && typeof parsed.refreshToken === "string") {
      return {
        kind: "live",
        accessToken: parsed.accessToken,
        refreshToken: parsed.refreshToken,
      };
    }
    if (typeof parsed.accessToken === "string" && typeof parsed.refreshToken === "string") {
      return {
        kind: "live",
        accessToken: parsed.accessToken,
        refreshToken: parsed.refreshToken,
      };
    }
    return null;
  } catch {
    return null;
  }
}

function storeSession(session: Session | null) {
  if (typeof window === "undefined") return;
  if (session) {
    window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } else {
    window.sessionStorage.removeItem(SESSION_KEY);
  }
}

function demoPermissionCodes(): string[] {
  const user = getDemoAdminUser();
  return mockRoleDetails[user.role_id]?.permission_codes ?? [];
}

async function loadRolePermissionCodes(
  roleId: string,
  accessToken: string,
): Promise<string[] | null> {
  const result = await apiRequest<Role>(`/rbac/roles/${roleId}`, {
    accessToken,
    skipUnauthorizedHandler: true,
  });
  if (result.status === "success") return result.data.permission_codes;
  return null;
}

function initialDemoSession(): boolean {
  return USE_MOCKS && readStoredSession()?.kind === "demo";
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(() =>
    initialDemoSession() ? { kind: "demo" } : null,
  );
  const [user, setUser] = useState<AuthenticatedUser | null>(() =>
    initialDemoSession() ? getDemoAdminUser() : null,
  );
  const [permissionCodes, setPermissionCodes] = useState<string[] | null>(() =>
    initialDemoSession() ? demoPermissionCodes() : null,
  );
  const [status, setStatus] = useState<AuthContextValue["status"]>(() => {
    const stored = readStoredSession();
    if (USE_MOCKS && stored?.kind === "demo") return "authenticated";
    if (!USE_MOCKS && stored?.kind === "live") return "loading";
    return "unauthenticated";
  });

  const clearSession = useCallback(() => {
    setSession(null);
    setUser(null);
    setPermissionCodes(null);
    setAccessToken(null);
    storeSession(null);
    setStatus("unauthenticated");
  }, []);

  const suspendSession = useCallback(() => {
    setSession(null);
    setUser(null);
    setPermissionCodes(null);
    setAccessToken(null);
    setStatus("unauthenticated");
  }, []);

  const activateDemoSession = useCallback((): LoginOutcome => {
    if (!USE_MOCKS) {
      return { ok: false, error: "Demo mode is disabled. Sign in against the Pompo backend." };
    }
    const demo: DemoSession = { kind: "demo" };
    storeSession(demo);
    setSession(demo);
    setAccessToken(null);
    setUser(getDemoAdminUser());
    setPermissionCodes(demoPermissionCodes());
    setStatus("authenticated");
    return { ok: true };
  }, []);

  const enterDemoSession = useCallback((): LoginOutcome => activateDemoSession(), [activateDemoSession]);

  useEffect(() => {
    setAccessToken(session?.kind === "live" ? session.accessToken : null);
  }, [session]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      clearSession();
      if (typeof window !== "undefined" && !isCustomerWebSurface()) {
        router.push("/login");
      }
    });
    return () => setUnauthorizedHandler(null);
  }, [clearSession, router]);

  useEffect(() => {
    const stored = readStoredSession();
    if (!stored) return;

    if (USE_MOCKS) {
      return;
    }

    if (stored.kind === "demo") {
      storeSession(null);
      return;
    }

    void (async () => {
      const meResult = await authService.me(stored.accessToken);
      if (meResult.status === "success") {
        const codes = await loadRolePermissionCodes(meResult.data.role_id, stored.accessToken);
        setSession(stored);
        setAccessToken(stored.accessToken);
        setUser(meResult.data);
        setPermissionCodes(codes);
        setStatus("authenticated");
        return;
      }
      if (meResult.kind === "network") {
        suspendSession();
        return;
      }
      const refreshed = await authService.refresh(stored.refreshToken);
      if (refreshed.status === "success") {
        const nextSession: LiveSession = {
          kind: "live",
          accessToken: refreshed.data.access_token,
          refreshToken: refreshed.data.refresh_token,
        };
        const retriedMe = await authService.me(nextSession.accessToken);
        if (retriedMe.status === "success") {
          const codes = await loadRolePermissionCodes(retriedMe.data.role_id, nextSession.accessToken);
          setSession(nextSession);
          storeSession(nextSession);
          setAccessToken(nextSession.accessToken);
          setUser(retriedMe.data);
          setPermissionCodes(codes);
          setStatus("authenticated");
          return;
        }
        if (retriedMe.kind === "network") {
          suspendSession();
          return;
        }
      } else if (refreshed.kind === "network") {
        suspendSession();
        return;
      }
      clearSession();
    })();
  }, [clearSession, suspendSession]);

  const login = useCallback(
    async (email: string, password: string): Promise<LoginOutcome> => {
      if (USE_MOCKS) {
        void email;
        void password;
        return activateDemoSession();
      }

      const result = await authService.login({
        email: email.trim().toLowerCase(),
        password,
      });
      if (result.status === "error") {
        return {
          ok: false,
          error: result.message,
          kind: result.kind,
          httpStatus: result.httpStatus,
          requestId: result.requestId,
        };
      }
      const nextSession: LiveSession = {
        kind: "live",
        accessToken: result.data.access_token,
        refreshToken: result.data.refresh_token,
      };
      const meResult = await authService.me(nextSession.accessToken);
      if (meResult.status === "error") {
        return {
          ok: false,
          error: `Signed in, but could not load your profile. ${meResult.message}`,
          kind: meResult.kind,
          httpStatus: meResult.httpStatus,
          requestId: meResult.requestId,
        };
      }
      const codes = await loadRolePermissionCodes(meResult.data.role_id, nextSession.accessToken);
      setSession(nextSession);
      storeSession(nextSession);
      setAccessToken(nextSession.accessToken);
      setUser(meResult.data);
      setPermissionCodes(codes);
      setStatus("authenticated");
      return { ok: true };
    },
    [activateDemoSession],
  );

  const logout = useCallback(async () => {
    if (session?.kind === "live") {
      await authService.logout(session.refreshToken);
    }
    clearSession();
    router.push("/login");
  }, [session, clearSession, router]);

  const isDemoSession = session?.kind === "demo";

  const value = useMemo(
    () => ({
      user,
      status,
      isDemoSession,
      permissionCodes,
      login,
      enterDemoSession,
      logout,
    }),
    [user, status, isDemoSession, permissionCodes, login, enterDemoSession, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
