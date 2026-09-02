import { randomUUID } from "expo-crypto";
import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import type { Payment, QrInspect } from "@/types";

export interface CheckoutSession {
  payload: string;
  inspect: QrInspect;
  amount: string;
  idempotencyKey: string;
  payment: Payment | null;
}

interface CheckoutState {
  session: CheckoutSession | null;
  begin: (payload: string, inspect: QrInspect, amount: string) => void;
  setPayment: (payment: Payment) => void;
  clear: () => void;
}

const CheckoutContext = createContext<CheckoutState | null>(null);

export function CheckoutProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<CheckoutSession | null>(null);

  const value = useMemo<CheckoutState>(
    () => ({
      session,
      begin(payload, inspect, amount) {
        setSession({
          payload,
          inspect,
          amount,
          idempotencyKey: randomUUID(),
          payment: null,
        });
      },
      setPayment(payment) {
        setSession((current) => (current ? { ...current, payment } : current));
      },
      clear() {
        setSession(null);
      },
    }),
    [session],
  );

  return <CheckoutContext.Provider value={value}>{children}</CheckoutContext.Provider>;
}

export function useCheckout(): CheckoutState {
  const value = useContext(CheckoutContext);
  if (value === null) {
    throw new Error("useCheckout must be used inside CheckoutProvider");
  }
  return value;
}
