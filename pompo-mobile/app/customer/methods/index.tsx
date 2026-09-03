import { useRouter, type Href } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Pressable, Text, View } from "react-native";

import { BottomNav } from "@/components/nav";
import { Card, ErrorBanner, PrimaryButton, Screen, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import type { PaymentMethod } from "@/types";

export default function PaymentMethodsScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [rows, setRows] = useState<PaymentMethod[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const result = await api.listPaymentMethods();
    if (result.ok) {
      setRows(result.data);
      setError(null);
      return;
    }
    setError(result.error.message);
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8, gap: 12 }}>
        <Title>Payment methods</Title>
        <Text style={{ color: theme.subtle }}>
          Saved ways to pay merchants. POMPO does not keep PINs, CVVs, or card numbers.
        </Text>
        {error ? <ErrorBanner message={error} /> : null}
        {rows.map((row) => (
          <Pressable key={row.id} onPress={() => router.push(`/customer/methods/${row.id}` as Href)}>
            <Card>
              <Text style={{ color: theme.text, fontWeight: "800" }}>{row.display_name}</Text>
              <Text style={{ color: theme.muted, marginTop: 4 }}>{row.masked_identifier}</Text>
              <Text style={{ color: theme.subtle, marginTop: 6, fontSize: 12, fontWeight: "700" }}>
                {row.status.toUpperCase()}
                {row.is_default ? " · DEFAULT" : ""}
                {row.is_sandbox ? " · TEST" : ""}
              </Text>
            </Card>
          </Pressable>
        ))}
        <PrimaryButton label="Add payment method" onPress={() => router.push("/customer/methods/add" as Href)} />
      </View>
      <BottomNav active="profile" />
    </Screen>
  );
}
