import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { canUseMerchantMode, defaultMode } from "@/domain/roles";
import { useAuth } from "@/state/AuthProvider";
import type { AppMode } from "@/types";

interface ModeState {
  mode: AppMode;
  canSwitch: boolean;
  setMode: (mode: AppMode) => void;
}

const ModeContext = createContext<ModeState | null>(null);

export function ModeProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const roleCode = user?.role_code ?? "customer";
  const [override, setOverride] = useState<AppMode | null>(null);
  const mode = override ?? defaultMode(roleCode);
  const canSwitch = canUseMerchantMode(roleCode, user?.merchant_id);

  const value = useMemo<ModeState>(
    () => ({
      mode: canSwitch ? mode : "customer",
      canSwitch,
      setMode: (next) => {
        if (next === "merchant" && !canSwitch) {
          return;
        }
        setOverride(next);
      },
    }),
    [canSwitch, mode],
  );

  return <ModeContext.Provider value={value}>{children}</ModeContext.Provider>;
}

export function useAppMode(): ModeState {
  const value = useContext(ModeContext);
  if (value === null) {
    throw new Error("useAppMode must be used inside ModeProvider");
  }
  return value;
}
