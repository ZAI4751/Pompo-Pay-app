import { useLocalSearchParams, useRouter, type Href } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Text } from "react-native";

import { Card, ErrorBanner, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { paymentMethodStateLabel } from "@/domain/paymentMethod";
import { useAuth } from "@/state/AuthProvider";
import type { PaymentMethod } from "@/types";

export default function PaymentMethodDetailScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [row, setRow] = useState<PaymentMethod | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) {
      return;
    }
    const result = await api.getPaymentMethod(id);
    if (result.ok) {
      setRow(result.data);
      return;
    }
    setError(result.error.message);
  }, [api, id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!row) {
    return (
      <Screen>
        <Title>Payment method</Title>
        {error ? <ErrorBanner message={error} /> : null}
      </Screen>
    );
  }

  return (
    <Screen>
      <Title>{row.display_name}</Title>
      <Card>
        <Text style={{ color: theme.text, fontWeight: "800" }}>{row.masked_identifier}</Text>
        <Text style={{ color: theme.muted, marginTop: 8 }}>{row.provider_display_name}</Text>
        <Text style={{ color: theme.subtle, marginTop: 8 }}>{paymentMethodStateLabel(row)}</Text>
        {row.last_used_at ? (
          <Text style={{ color: theme.subtle, marginTop: 8 }}>Last used {row.last_used_at}</Text>
        ) : null}
      </Card>
      {error ? <ErrorBanner message={error} /> : null}
      {!row.is_default ? (
        <PrimaryButton
          label="Set as default"
          onPress={async () => {
            const result = await api.setDefaultPaymentMethod(row.id);
            if (result.ok) setRow(result.data);
            else setError(result.error.message);
          }}
        />
      ) : null}
      <SecondaryButton
        label="Remove"
        onPress={async () => {
          const result = await api.revokePaymentMethod(row.id);
          if (!result.ok) {
            setError(result.error.message);
            return;
          }
          router.replace("/customer/methods" as Href);
        }}
      />
    </Screen>
  );
}
