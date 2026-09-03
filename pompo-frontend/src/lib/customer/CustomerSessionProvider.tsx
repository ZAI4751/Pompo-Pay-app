"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { authService } from "@/lib/api/services/auth";
import { setCustomerAccessToken, setCustomerUnauthorizedHandler } from "@/lib/api/session";
import type { AuthenticatedUser } from "@/lib/types/auth";
import { readCustomerSession, writeCustomerSession, type CustomerStoredSession } from "./sessionStore";

interface CustomerSessionValue {
  user: AuthenticatedUser | null;
  status: "loading" | "authenticated" | "unauthenticated";
  refreshToken: string | null;
  signIn: (accessToken: string, refreshToken: string) => Promise<AuthenticatedUser | null>;
  refreshProfile: () => Promise<AuthenticatedUser | null>;
  signOut: () => Promise<void>;
  clearSession: () => void;
  logoutAllSessions: () => Promise<{ ok: boolean; message?: string }>;
}

const CustomerSessionContext = createContext<CustomerSessionValue | null>(null);

export function CustomerSessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [status, setStatus] = useState<CustomerSessionValue["status"]>(() =>
    readCustomerSession() ? "loading" : "unauthenticated",
  );

  const clear = useCallback(() => {
    setUser(null);
    setRefreshToken(null);
    setCustomerAccessToken(null);
    writeCustomerSession(null);
    setStatus("unauthenticated");
  }, []);

  const activate = useCallback((session: CustomerStoredSession, nextUser: AuthenticatedUser) => {
    setCustomerAccessToken(session.accessToken);
    writeCustomerSession(session);
    setRefreshToken(session.refreshToken);
    setUser(nextUser);
    setStatus("authenticated");
  }, []);

  const signIn = useCallback(
    async (accessToken: string, nextRefreshToken: string) => {
      const session = { accessToken, refreshToken: nextRefreshToken };
      setCustomerAccessToken(accessToken);
      const me = await authService.me(accessToken);
      if (me.status !== "success") {
        clear();
        return null;
      }
      activate(session, me.data);
      return me.data;
    },
    [activate, clear],
  );

  const refreshProfile = useCallback(async () => {
    const stored = readCustomerSession();
    if (!stored) {
      clear();
      return null;
    }
    const me = await authService.me(stored.accessToken);
    if (me.status === "success") {
      activate(stored, me.data);
      return me.data;
    }
    return user;
  }, [activate, clear, user]);

  useEffect(() => {
    setCustomerUnauthorizedHandler(() => {
      clear();
    });
    return () => setCustomerUnauthorizedHandler(null);
  }, [clear]);

  useEffect(() => {
    const stored = readCustomerSession();
    if (!stored) {
      return;
    }

    void (async () => {
      const me = await authService.me(stored.accessToken);
      if (me.status === "success") {
        activate(stored, me.data);
        return;
      }
      if (me.kind === "network") {
        setCustomerAccessToken(stored.accessToken);
        setRefreshToken(stored.refreshToken);
        setStatus("unauthenticated");
        return;
      }
      const refreshed = await authService.refresh(stored.refreshToken);
      if (refreshed.status === "success") {
        const next: CustomerStoredSession = {
          accessToken: refreshed.data.access_token,
          refreshToken: refreshed.data.refresh_token,
        };
        const retried = await authService.me(next.accessToken);
        if (retried.status === "success") {
          activate(next, retried.data);
          return;
        }
      }
      clear();
    })();
  }, [activate, clear]);

  const signOut = useCallback(async () => {
    const stored = readCustomerSession();
    if (stored?.refreshToken) {
      await authService.logout(stored.refreshToken);
    }
    clear();
  }, [clear]);

  const logoutAllSessions = useCallback(async () => {
    const result = await authService.logoutAll();
    if (result.status === "error") {
      return { ok: false, message: result.message };
    }
    clear();
    return { ok: true };
  }, [clear]);

  const value = useMemo(
    () => ({
      user,
      status,
      refreshToken,
      signIn,
      refreshProfile,
      signOut,
      clearSession: clear,
      logoutAllSessions,
    }),
    [user, status, refreshToken, signIn, refreshProfile, signOut, clear, logoutAllSessions],
  );

  return <CustomerSessionContext.Provider value={value}>{children}</CustomerSessionContext.Provider>;
}

export function useCustomerSession(): CustomerSessionValue {
  const ctx = useContext(CustomerSessionContext);
  if (!ctx) throw new Error("useCustomerSession must be used within CustomerSessionProvider");
  return ctx;
}
