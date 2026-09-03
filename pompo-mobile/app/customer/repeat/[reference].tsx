import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Share, Text } from "react-native";

import { AmountDisplay, FadeIn, StatusPill } from "@/components/glass";
import {
  Card,
  ErrorBanner,
  formatMoney,
  PrimaryButton,
  Screen,
  SecondaryButton,
  Title,
  useTheme,
} from "@/components/ui";
import { paymentStatusDetail, paymentStatusLabel } from "@/domain/paymentStatus";
import { useAuth } from "@/state/AuthProvider";
import type { Payment } from "@/types";

export default function RepeatPaymentScreen() {
  const { reference } = useLocalSearchParams<{ reference: string }>();
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [payment, setPayment] = useState<Payment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!reference) return;
    void api.getPayment(reference).then((result) => {
      if (result.ok) setPayment(result.data);
      else setError(result.error.message);
    });
  }, [api, reference]);

  return (
    <Screen>
      <Title>Pay again</Title>
      <Text style={{ color: theme.muted, marginBottom: 12 }}>
        This creates a new payment to the same merchant. The previous payment is not reused.
      </Text>
      {error ? <ErrorBanner message={error} /> : null}
      {payment ? (
        <FadeIn>
          <Card>
            <Text style={{ color: theme.text, fontWeight: "800" }}>{payment.merchant_name}</Text>
            <AmountDisplay value={formatMoney(payment.amount, payment.currency)} />
            <StatusPill label={paymentStatusLabel(payment.status)} tone="success" />
            <Text style={{ color: theme.subtle, marginTop: 8 }}>
              {payment.status_detail || paymentStatusDetail(payment.status)}
            </Text>
          </Card>
        </FadeIn>
      ) : null}
      <PrimaryButton
        label="Confirm new payment"
        loading={loading}
        onPress={async () => {
          if (!reference) return;
          setLoading(true);
          const created = await api.repeatPayment(reference, `repeat-${Date.now()}`);
          if (!created.ok) {
            setLoading(false);
            setError(created.error.message);
            return;
          }
          const processed = await api.processPayment(created.data.reference);
          setLoading(false);
          if (!processed.ok) {
            setError(processed.error.message);
            return;
          }
          router.replace(`/customer/payment/${processed.data.reference}`);
        }}
      />
      <SecondaryButton
        label="Share this merchant"
        onPress={() =>
          payment
            ? void Share.share({
                message: `Pay ${payment.merchant_name ?? "this merchant"} with POMPO. Last amount ${formatMoney(payment.amount, payment.currency)}.`,
              })
            : undefined
        }
      />
      <SecondaryButton label="Cancel" onPress={() => router.back()} />
    </Screen>
  );
}
