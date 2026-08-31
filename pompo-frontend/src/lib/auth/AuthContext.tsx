"use client";

/**
 * Owns the session lifecycle end-to-end: login, silent token refresh,
 * logout, and "session expired -> redirect to /login". This is the ONLY
 * place that decides the session is over -- API call sites just report
 * success/error and this context reacts.
 *
 * Tokens live in memory (React state) plus sessionStorage for reload
 * survival -- deliberately NOT localStorage, so a session doesn't silently
 * persist across browser restarts on a shared machine, and deliberately
 * not a cookie (no backend session-cookie support exists; the API takes a
 * bearer token, per the real M003 contract).
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { authService } from "@/lib/api/services/auth";
import type { AuthenticatedUser } from "@/lib/types/auth";
import type { ApiErrorKind } from "@/lib/types/common";

interface Session {
  accessToken: string;
  refreshToken: string;
}

interface LoginOutcome {
  ok: boolean;
  error?: string;
  /** Why login failed, so callers can react without matching on message text. */
  kind?: ApiErrorKind;
  httpStatus?: number;
  requestId?: string;
}

interface AuthContextValue {
  user: AuthenticatedUser | null;
  status: "loading" | "authenticated" | "unauthenticated";
  login: (email: string, password: string) => Promise<LoginOutcome>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const SESSION_KEY = "pompo_admin_session";

function readStoredSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
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

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  // "No stored session" is knowable synchronously, so it's resolved via a
  // lazy initializer rather than a setState call inside the effect below --
  // the effect only needs to handle the genuinely async case (verifying/
  // refreshing a token that IS present).
  const [status, setStatus] = useState<AuthContextValue["status"]>(() =>
    readStoredSession() ? "loading" : "unauthenticated",
  );

  const clearSession = useCallback(() => {
    setSession(null);
    setUser(null);
    storeSession(null);
    setStatus("unauthenticated");
  }, []);

  // Give up on this page load without destroying the stored tokens: used when
  // the backend could not be reached, where the session may well still be
  // valid and discarding it would sign the user out over a transient blip.
  const suspendSession = useCallback(() => {
    setSession(null);
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  // On mount: try to resume a session from sessionStorage, refreshing the
  // access token if needed rather than trusting a possibly-stale one.
  useEffect(() => {
    const stored = readStoredSession();
    if (!stored) {
      return; // status was already initialized to "unauthenticated" above
    }
    void (async () => {
      const meResult = await authService.me(stored.accessToken);
      if (meResult.status === "success") {
        setSession(stored);
        setUser(meResult.data);
        setStatus("authenticated");
        return;
      }
      // The backend never answered, so this says nothing about whether the
      // token is still good. Keep it and retry on the next load.
      if (meResult.kind === "network") {
        suspendSession();
        return;
      }
      // Access token expired/invalid -- try the refresh token before
      // giving up on the session entirely.
      const refreshed = await authService.refresh(stored.refreshToken);
      if (refreshed.status === "success") {
        const nextSession = {
          accessToken: refreshed.data.access_token,
          refreshToken: refreshed.data.refresh_token,
        };
        const retriedMe = await authService.me(nextSession.accessToken);
        if (retriedMe.status === "success") {
          setSession(nextSession);
          storeSession(nextSession);
          setUser(retriedMe.data);
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

  const login = useCallback(async (email: string, password: string): Promise<LoginOutcome> => {
    const result = await authService.login({ email, password });
    if (result.status === "error") {
      return {
        ok: false,
        error: result.message,
        kind: result.kind,
        httpStatus: result.httpStatus,
        requestId: result.requestId,
      };
    }
    const nextSession = {
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
    setSession(nextSession);
    storeSession(nextSession);
    setUser(meResult.data);
    setStatus("authenticated");
    return { ok: true };
  }, []);

  const logout = useCallback(async () => {
    if (session) {
      await authService.logout(session.refreshToken);
    }
    clearSession();
    router.push("/login");
  }, [session, clearSession, router]);

  const value = useMemo(
    () => ({ user, status, login, logout }),
    [user, status, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
