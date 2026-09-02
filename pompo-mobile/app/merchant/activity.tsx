import { useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { FlatList, Pressable, RefreshControl, Text, View } from "react-native";

import { BottomNav } from "@/components/nav";
import { EmptyState, ErrorBanner, formatMoney, Screen, Title, useTheme } from "@/components/ui";
import { paymentStatusLabel } from "@/domain/paymentStatus";
import { useAuth } from "@/state/AuthProvider";
import type { Payment } from "@/types";

export default function MerchantActivity() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [rows, setRows] = useState<Payment[]>([]);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setRefreshing(true);
    const result = await api.listMerchantPayments();
    setRefreshing(false);
    if (!result.ok) {
      setError({ message: result.error.message, requestId: result.error.requestId });
      return;
    }
    setError(null);
    setRows(result.data);
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 12 }}>
        <Title>Activity</Title>
        {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
        <FlatList
          data={rows}
          keyExtractor={(item) => item.id}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void load()} />}
          ListEmptyComponent={
            refreshing ? null : (
              <EmptyState title="No payments yet" body="Generate a QR and take a customer payment." />
            )
          }
          renderItem={({ item }) => (
            <Pressable
              onPress={() => router.push(`/merchant/payment/${item.reference}`)}
              style={{ paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: theme.border }}
            >
              <Text style={{ color: theme.text, fontWeight: "700" }}>
                {formatMoney(item.amount, item.currency)}
              </Text>
              <Text style={{ color: theme.muted }}>
                {paymentStatusLabel(item.status)} · {item.reference}
              </Text>
            </Pressable>
          )}
        />
      </View>
      <BottomNav active="activity" />
    </Screen>
  );
}
