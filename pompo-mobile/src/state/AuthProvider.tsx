import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { createApiClient, type PompoApi } from "@/api/client";
import { secureTokenStore } from "@/auth/secureStorage";
import { validateCustomerRegistrationInput } from "@/domain/registration";
import type { AuthenticatedUser } from "@/types";

interface AuthState {
  hydrated: boolean;
  user: AuthenticatedUser | null;
  api: PompoApi;
  login: (email: string, password: string) => Promise<{ ok: true } | { ok: false; message: string }>;
  register: (
    input: { email: string; password: string; full_name: string; phone?: string },
  ) => Promise<{ ok: true } | { ok: false; message: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const api = useMemo(() => createApiClient(secureTokenStore), []);
  const [hydrated, setHydrated] = useState(false);
  const [user, setUser] = useState<AuthenticatedUser | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const result = await api.restoreSession();
      if (!cancelled && result.ok) {
        setUser(result.data);
      }
      if (!cancelled) {
        setHydrated(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [api]);

  const value = useMemo<AuthState>(
    () => ({
      hydrated,
      user,
      api,
      async login(email, password) {
        const tokens = await api.login(email.trim(), password);
        if (!tokens.ok) {
          return { ok: false, message: tokens.error.message };
        }
        const me = await api.me();
        if (!me.ok) {
          await api.logout();
          return { ok: false, message: me.error.message };
        }
        setUser(me.data);
        return { ok: true };
      },
      async register(input) {
        const localReason = validateCustomerRegistrationInput(input);
        if (localReason) {
          return { ok: false, message: localReason };
        }
        const tokens = await api.register(input);
        if (!tokens.ok) {
          return { ok: false, message: tokens.error.message };
        }
        const me = await api.me();
        if (!me.ok) {
          await api.logout();
          return { ok: false, message: me.error.message };
        }
        setUser(me.data);
        return { ok: true };
      },
      async logout() {
        await api.logout();
        setUser(null);
      },
      async refreshUser() {
        const me = await api.me();
        if (me.ok) {
          setUser(me.data);
        }
      },
    }),
    [api, hydrated, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (value === null) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}
