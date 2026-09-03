import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Share, Text } from "react-native";

import { AmountDisplay, FadeIn, StatusPill } from "@/components/glass";
import { Card, ErrorBanner, formatMoney, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import type { PaymentRequest } from "@/types";

export default function PaymentRequestDetail() {
  const { publicId } = useLocalSearchParams<{ publicId: string }>();
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [request, setRequest] = useState<PaymentRequest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!publicId) return;
    void api.inspectPaymentRequest(publicId).then((result) => {
      if (result.ok) setRequest(result.data);
      else setError(result.error.message);
    });
  }, [api, publicId]);

  return (
    <Screen>
      <Title>Payment request</Title>
      {error ? <ErrorBanner message={error} /> : null}
      {request ? (
        <FadeIn>
          <Card>
            <StatusPill label={request.status} tone={request.status === "paid" ? "success" : "pending"} />
            <Text style={{ color: theme.text, fontWeight: "800", marginTop: 8 }}>
              {request.merchant_name ?? "Merchant"}
            </Text>
            <AmountDisplay value={formatMoney(request.amount, request.currency)} />
            <Text style={{ color: theme.muted }}>{request.description}</Text>
            <Text style={{ color: theme.subtle }}>Code {request.share_code}</Text>
            {request.payment_reference ? (
              <Text style={{ color: theme.subtle }}>Paid as {request.payment_reference}</Text>
            ) : null}
          </Card>
        </FadeIn>
      ) : null}
      {request?.status === "pending" ? (
        <PrimaryButton
          label="Pay this request"
          onPress={() =>
            router.push({
              pathname: "/customer/pay-request/[publicId]",
              params: { publicId: request.public_identifier },
            })
          }
        />
      ) : null}
      <SecondaryButton
        label="Share"
        onPress={() =>
          request
            ? void Share.share({
                message: `POMPO payment request ${request.share_code} — ${formatMoney(request.amount, request.currency)} to ${request.merchant_name ?? "merchant"}.`,
              })
            : undefined
        }
      />
      {request?.status === "pending" ? (
        <SecondaryButton
          label="Cancel request"
          onPress={async () => {
            const result = await api.cancelPaymentRequest(request.public_identifier);
            if (result.ok) setRequest(result.data);
            else setError(result.error.message);
          }}
        />
      ) : null}
    </Screen>
  );
}
