import { randomUUID } from "expo-crypto";
import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import type { Payment, QrInspect } from "@/types";

export interface CheckoutSession {
  payload: string | null;
  publicIdentifier: string;
  inspect: QrInspect;
  amount: string;
  idempotencyKey: string;
  payment: Payment | null;
  paymentMethodId: string | null;
}

interface CheckoutState {
  session: CheckoutSession | null;
  begin: (raw: string, inspect: QrInspect, amount: string) => void;
  selectPaymentMethod: (id: string | null) => void;
  setPayment: (payment: Payment) => void;
  clear: () => void;
}

const CheckoutContext = createContext<CheckoutState | null>(null);

export function CheckoutProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<CheckoutSession | null>(null);

  const value = useMemo<CheckoutState>(
    () => ({
      session,
      begin(raw, inspect, amount) {
        const trimmed = raw.trim();
        const isPayload = trimmed.startsWith("POMPO:");
        setSession((current) => {
          const sameQr = current?.inspect.public_identifier === inspect.public_identifier;
          return {
            payload: isPayload ? trimmed : sameQr ? current?.payload ?? null : null,
            publicIdentifier: inspect.public_identifier,
            inspect,
            amount,
            idempotencyKey: sameQr && current ? current.idempotencyKey : randomUUID(),
            payment: null,
            paymentMethodId: sameQr && current ? current.paymentMethodId : null,
          };
        });
      },
      selectPaymentMethod(id) {
        setSession((current) => (current ? { ...current, paymentMethodId: id } : current));
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
