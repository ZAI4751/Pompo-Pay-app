import { useRouter } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FlatList, RefreshControl, Text, View } from "react-native";

import { PressScale, StatusPill } from "@/components/glass";
import { BottomNav } from "@/components/nav";
import { EmptyState, ErrorBanner, formatMoney, Screen, Title, useTheme } from "@/components/ui";
import { mapPaymentStatus, paymentStatusLabel } from "@/domain/paymentStatus";
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

  const incoming = useMemo(
    () => rows.filter((row) => mapPaymentStatus(row.status) === "success").length,
    [rows],
  );

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 12 }}>
        <Title>Activity</Title>
        <Text style={{ color: theme.muted, marginBottom: 8 }}>{incoming} settled payments in this list</Text>
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
          renderItem={({ item }) => {
            const phase = mapPaymentStatus(item.status);
            const tone = phase === "success" ? "success" : phase === "failed" || phase === "timeout" ? "error" : "pending";
            return (
              <PressScale
                accessibilityRole="button"
                onPress={() => router.push(`/merchant/payment/${item.reference}`)}
                style={{ paddingVertical: 14, gap: 6 }}
              >
                <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                  <Text style={{ color: theme.text, fontWeight: "700" }}>
                    {formatMoney(item.amount, item.currency)}
                  </Text>
                  <StatusPill label={paymentStatusLabel(item.status)} tone={tone} />
                </View>
                <Text style={{ color: theme.muted }}>{item.reference}</Text>
              </PressScale>
            );
          }}
        />
      </View>
      <BottomNav active="activity" />
    </Screen>
  );
}
