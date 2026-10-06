import { randomUUID } from "expo-crypto";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { useAuth } from "@/state/AuthProvider";
import type { Payment, PaymentMethodCatalogItem, QrInspect } from "@/types";

export interface CheckoutSession {
  payload: string | null;
  publicIdentifier: string;
  inspect: QrInspect;
  amount: string;
  idempotencyKey: string;
  payment: Payment | null;
  paymentMethod: PaymentMethodCatalogItem | null;
  customerPhone: string;
}

interface CheckoutState {
  session: CheckoutSession | null;
  begin: (raw: string, inspect: QrInspect, amount: string) => void;
  selectPaymentMethod: (method: PaymentMethodCatalogItem | null) => void;
  setCustomerPhone: (phone: string) => void;
  setPayment: (payment: Payment) => void;
  clear: () => void;
}

const CheckoutContext = createContext<CheckoutState | null>(null);

export function CheckoutProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [session, setSession] = useState<CheckoutSession | null>(null);
  const hadUser = useRef(false);

  useEffect(() => {
    if (user) {
      hadUser.current = true;
      return;
    }
    if (hadUser.current) {
      setSession(null);
      hadUser.current = false;
    }
  }, [user]);

  const begin = useCallback((raw: string, inspect: QrInspect, amount: string) => {
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
        paymentMethod: sameQr ? current?.paymentMethod ?? null : null,
        customerPhone: sameQr ? current?.customerPhone ?? "" : "",
      };
    });
  }, []);

  const selectPaymentMethod = useCallback((method: PaymentMethodCatalogItem | null) => {
    setSession((current) => {
      if (!current) {
        return current;
      }
      if (
        current.paymentMethod?.provider_code === method?.provider_code &&
        current.paymentMethod?.instrument_type === method?.instrument_type
      ) {
        return current.paymentMethod === method ? current : { ...current, paymentMethod: method };
      }
      return { ...current, paymentMethod: method };
    });
  }, []);

  const setCustomerPhone = useCallback((phone: string) => {
    setSession((current) => (current ? { ...current, customerPhone: phone } : current));
  }, []);

  const setPayment = useCallback((payment: Payment) => {
    setSession((current) => (current ? { ...current, payment } : current));
  }, []);

  const clear = useCallback(() => {
    setSession(null);
  }, []);

  const value = useMemo<CheckoutState>(
    () => ({
      session,
      begin,
      selectPaymentMethod,
      setCustomerPhone,
      setPayment,
      clear,
    }),
    [session, begin, selectPaymentMethod, setCustomerPhone, setPayment, clear],
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
