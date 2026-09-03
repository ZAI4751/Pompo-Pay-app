import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Share, Text, View } from "react-native";

import { AmountDisplay, FadeIn, InitialsAvatar, StatusPill } from "@/components/glass";
import { Card, ErrorBanner, formatMoney, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { mapPaymentStatus, paymentStatusDetail, paymentStatusLabel } from "@/domain/paymentStatus";
import { formatWhen } from "@/format";
import { useAuth } from "@/state/AuthProvider";
import type { Payment } from "@/types";

export default function CustomerPaymentDetail() {
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
      <Title>Receipt</Title>
      {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
      {payment ? (
        <FadeIn>
          <Card>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <InitialsAvatar name={payment.merchant_name ?? "Merchant"} size={48} active={tone === "success"} />
              <StatusPill label={paymentStatusLabel(payment.status)} tone={tone} />
            </View>
            <Text style={{ color: theme.text, fontSize: 18, fontWeight: "800", marginTop: 8 }}>
              {payment.merchant_name ?? "Merchant"}
            </Text>
            {payment.branch_name ? (
              <Text style={{ color: theme.muted }}>
                {payment.branch_name}
                {payment.till_name ? ` · ${payment.till_name}` : ""}
              </Text>
            ) : null}
            <AmountDisplay value={formatMoney(payment.amount, payment.currency)} />
            <Text style={{ color: theme.muted, marginTop: 8 }}>
              {payment.status_detail || paymentStatusDetail(payment.status)}
            </Text>
            <View style={{ gap: 6, marginTop: 8 }}>
              <Text style={{ color: theme.subtle }}>Reference {payment.reference}</Text>
              {payment.created_at ? (
                <Text style={{ color: theme.subtle }}>{formatWhen(payment.created_at)}</Text>
              ) : null}
              {payment.attempts[0]?.provider_reference ? (
                <Text style={{ color: theme.subtle }}>Provider ref {payment.attempts[0].provider_reference}</Text>
              ) : null}
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
                "POMPO PAYMENT RECEIPT",
                payment.merchant_name ?? "Merchant",
                formatMoney(payment.amount, payment.currency),
                paymentStatusLabel(payment.status),
                `Reference ${payment.reference}`,
              ].join("\n"),
            })
          }
        />
      ) : null}
      {payment && mapPaymentStatus(payment.status) === "success" ? (
        <SecondaryButton
          label="Pay again"
          onPress={() =>
            router.push({ pathname: "/customer/repeat/[reference]", params: { reference: payment.reference } })
          }
        />
      ) : null}
      {payment ? (
        <SecondaryButton
          label="Ask for a share"
          onPress={() =>
            router.push({ pathname: "/customer/requests/index", params: { from: payment.reference } })
          }
        />
      ) : null}
      <SecondaryButton label="Back" onPress={() => router.back()} />
    </Screen>
  );
}
