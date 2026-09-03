import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Share, Text, View } from "react-native";

import { AmountDisplay, FadeIn, StatusPill } from "@/components/glass";
import { Card, ErrorBanner, formatMoney, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { mapPaymentStatus, paymentStatusLabel } from "@/domain/paymentStatus";
import { formatWhen } from "@/format";
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
      <Title>Payment received</Title>
      {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
      {payment ? (
        <FadeIn>
          <Card>
            <StatusPill label={paymentStatusLabel(payment.status)} tone={tone} />
            <AmountDisplay value={formatMoney(payment.amount, payment.currency)} />
            <View style={{ gap: 6, marginTop: 8 }}>
              <Text style={{ color: theme.subtle }}>Reference {payment.reference}</Text>
              {payment.till_name ? <Text style={{ color: theme.subtle }}>Till {payment.till_name}</Text> : null}
              {payment.created_at ? <Text style={{ color: theme.subtle }}>{formatWhen(payment.created_at)}</Text> : null}
            </View>
          </Card>
        </FadeIn>
      ) : null}
      {payment ? (
        <PrimaryButton
          label="Share receipt"
          onPress={() =>
            void Share.share({
              message: [
                "POMPO payment",
                formatMoney(payment.amount, payment.currency),
                paymentStatusLabel(payment.status),
                `Reference ${payment.reference}`,
              ].join("\n"),
            })
          }
        />
      ) : null}
      <SecondaryButton label="Back" onPress={() => router.back()} />
    </Screen>
  );
}
