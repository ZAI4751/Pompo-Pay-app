import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Text } from "react-native";

import { AmountDisplay, FadeIn } from "@/components/glass";
import { Card, ErrorBanner, formatMoney, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import type { PaymentRequest } from "@/types";

export default function PayRequestScreen() {
  const { publicId } = useLocalSearchParams<{ publicId: string }>();
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [request, setRequest] = useState<PaymentRequest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!publicId) return;
    void api.inspectPaymentRequest(publicId).then((result) => {
      if (result.ok) setRequest(result.data);
      else setError(result.error.message);
    });
  }, [api, publicId]);

  return (
    <Screen>
      <Title>Confirm payment</Title>
      <Text style={{ color: theme.muted, marginBottom: 12 }}>
        This creates a new merchant payment. POMPO does not hold funds.
      </Text>
      {error ? <ErrorBanner message={error} /> : null}
      {request ? (
        <FadeIn>
          <Card>
            <Text style={{ color: theme.text, fontWeight: "800" }}>{request.merchant_name}</Text>
            <AmountDisplay value={formatMoney(request.amount, request.currency)} />
            <Text style={{ color: theme.muted }}>{request.description}</Text>
          </Card>
        </FadeIn>
      ) : null}
      <PrimaryButton
        label="Pay now"
        loading={loading}
        onPress={async () => {
          if (!publicId) return;
          setLoading(true);
          const created = await api.payPaymentRequest(publicId, `reqpay-${Date.now()}`);
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
      <SecondaryButton label="Cancel" onPress={() => router.back()} />
    </Screen>
  );
}
