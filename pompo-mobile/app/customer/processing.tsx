import { useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Text } from "react-native";

import { ProcessingPulse } from "@/components/glass";
import { ErrorBanner, Screen, Title, useTheme } from "@/components/ui";
import { isTerminalPayment } from "@/domain/paymentStatus";
import { useAuth } from "@/state/AuthProvider";
import { useCheckout } from "@/state/CheckoutProvider";

export default function ProcessingScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const { session, setPayment } = useCheckout();
  const [message, setMessage] = useState("Starting payment…");
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!session || started.current) {
      return;
    }
    started.current = true;
    let cancelled = false;

    async function run() {
      if (!session) {
        return;
      }
      const amount = session.inspect.qr_type === "dynamic" ? undefined : session.amount;
      setMessage("Creating payment…");
      const initiated = await api.payFromQr({
        payload: session.payload,
        idempotencyKey: session.idempotencyKey,
        amount,
      });
      if (cancelled) {
        return;
      }
      if (!initiated.ok) {
        setError({ message: initiated.error.message, requestId: initiated.error.requestId });
        return;
      }
      setPayment(initiated.data);
      let payment = initiated.data;
      if (!isTerminalPayment(payment.status)) {
        setMessage("Processing with provider…");
        const processed = await api.processPayment(payment.reference);
        if (cancelled) {
          return;
        }
        if (!processed.ok) {
          setError({ message: processed.error.message, requestId: processed.error.requestId });
          return;
        }
        payment = processed.data;
        setPayment(payment);
      }
      if (!isTerminalPayment(payment.status) && payment.status !== "success") {
        for (let i = 0; i < 8; i += 1) {
          await new Promise((resolve) => setTimeout(resolve, 1500));
          const latest = await api.getPayment(payment.reference);
          if (cancelled) {
            return;
          }
          if (latest.ok) {
            payment = latest.data;
            setPayment(payment);
            if (isTerminalPayment(payment.status)) {
              break;
            }
          }
        }
      }
      router.replace("/customer/result");
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [api, router, session, setPayment]);

  if (!session) {
    return (
      <Screen>
        <Title>Payment</Title>
      </Screen>
    );
  }

  return (
    <Screen>
      <Title>Paying</Title>
      <ProcessingPulse />
      <Text style={{ color: theme.muted, textAlign: "center", marginTop: 16 }}>{message}</Text>
      {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
    </Screen>
  );
}
