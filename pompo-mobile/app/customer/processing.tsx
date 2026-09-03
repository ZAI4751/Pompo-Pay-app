import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { FadeIn, ProcessingPulse } from "@/components/glass";
import { ErrorBanner, Screen, SecondaryButton, useTheme } from "@/components/ui";
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
  const [runId, setRunId] = useState(0);

  useEffect(() => {
    if (!session) {
      return;
    }
    let cancelled = false;

    async function run() {
      if (!session) {
        return;
      }
      setError(null);
      const amount = session.inspect.qr_type === "dynamic" ? undefined : session.amount;
      setMessage("Creating payment…");
      const initiated = await api.payFromQr({
        payload: session.payload ?? undefined,
        publicIdentifier: session.payload ? undefined : session.publicIdentifier,
        idempotencyKey: session.idempotencyKey,
        amount,
        paymentInstrumentId: session.paymentMethodId ?? undefined,
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
  }, [api, router, session, setPayment, runId]);

  if (!session) {
    return (
      <Screen>
        <Text style={{ color: theme.text, fontWeight: "800", fontSize: 22 }}>Payment</Text>
        <SecondaryButton label="Back" onPress={() => router.replace("/customer")} />
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.center}>
        {error ? null : (
          <FadeIn>
            <ProcessingPulse />
          </FadeIn>
        )}
        <Text style={[styles.title, { color: theme.text }]}>Paying {session.inspect.merchant_name}</Text>
        <Text style={{ color: theme.muted, textAlign: "center" }}>
          {error ? "Payment did not start" : message}
        </Text>
        {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
        {error ? (
          <View style={{ width: "100%", gap: 10, marginTop: 8 }}>
            <SecondaryButton
              label="Retry"
              onPress={() => {
                setMessage("Retrying…");
                setRunId((value) => value + 1);
              }}
            />
            <SecondaryButton label="Back to confirmation" onPress={() => router.replace("/customer/confirm")} />
          </View>
        ) : null}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: "center", alignItems: "center", gap: 16, paddingBottom: 48 },
  title: { fontSize: 20, fontWeight: "800", textAlign: "center" },
});
