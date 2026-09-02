import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Text, View } from "react-native";

import { AmountDisplay, StatusPill } from "@/components/glass";
import { Card, ErrorBanner, formatMoney, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { mapPaymentStatus, paymentStatusLabel } from "@/domain/paymentStatus";
import { useAuth } from "@/state/AuthProvider";
import type { Payment } from "@/types";

export default function MerchantPaymentDetail() {
  const { reference } = useLocalSearchParams<{ reference: string }>();
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [payment, setPayment] = useState<Payment | null>(null);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);

  useEffect(() => {
    if (!reference) {
      return;
    }
    void api.getPayment(reference).then((result) => {
      if (result.ok) {
        setPayment(result.data);
      } else {
        setError({ message: result.error.message, requestId: result.error.requestId });
      }
    });
  }, [api, reference]);

  const phase = payment ? mapPaymentStatus(payment.status) : "unknown";
  const tone = phase === "success" ? "success" : phase === "failed" || phase === "timeout" ? "error" : "pending";

  return (
    <Screen>
      <Title>Payment</Title>
      {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
      {payment ? (
        <Card>
          <StatusPill label={paymentStatusLabel(payment.status)} tone={tone} />
          <AmountDisplay value={formatMoney(payment.amount, payment.currency)} />
          <View style={{ gap: 4, marginTop: 8 }}>
            <Text style={{ color: theme.subtle }}>Reference {payment.reference}</Text>
            {payment.till_name ? <Text style={{ color: theme.subtle }}>Till {payment.till_name}</Text> : null}
            {payment.created_at ? (
              <Text style={{ color: theme.subtle }}>{new Date(payment.created_at).toLocaleString()}</Text>
            ) : null}
          </View>
        </Card>
      ) : null}
      <SecondaryButton label="Back" onPress={() => router.back()} />
    </Screen>
  );
}
