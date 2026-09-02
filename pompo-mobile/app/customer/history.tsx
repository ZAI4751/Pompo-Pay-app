import { useRouter } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FlatList, RefreshControl, Text, View } from "react-native";

import { PressScale, StatusPill } from "@/components/glass";
import { BottomNav } from "@/components/nav";
import { EmptyState, ErrorBanner, formatMoney, Screen, Title, useTheme } from "@/components/ui";
import { mapPaymentStatus, paymentStatusLabel } from "@/domain/paymentStatus";
import { useAuth } from "@/state/AuthProvider";
import type { Payment } from "@/types";

function groupLabel(iso: string | null): string {
  if (!iso) {
    return "Undated";
  }
  const date = new Date(iso);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return "Today";
  }
  return date.toLocaleDateString();
}

export default function HistoryScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [rows, setRows] = useState<Payment[]>([]);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setRefreshing(true);
    const result = await api.listMyPayments();
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

  const grouped = useMemo(() => {
    const items: ({ type: "header"; title: string } | { type: "row"; item: Payment })[] = [];
    let last = "";
    for (const item of rows) {
      const title = groupLabel(item.created_at);
      if (title !== last) {
        items.push({ type: "header", title });
        last = title;
      }
      items.push({ type: "row", item });
    }
    return items;
  }, [rows]);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 12 }}>
        <Title>History</Title>
        {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
        <FlatList
          data={grouped}
          keyExtractor={(entry, index) =>
            entry.type === "header" ? `h-${entry.title}-${index}` : entry.item.id
          }
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void load()} />}
          ListEmptyComponent={
            refreshing ? null : <EmptyState title="No payments yet" body="Scan a QR to make your first payment." />
          }
          renderItem={({ item: entry }) => {
            if (entry.type === "header") {
              return (
                <Text style={{ color: theme.subtle, fontWeight: "700", marginTop: 16, marginBottom: 6 }}>
                  {entry.title}
                </Text>
              );
            }
            const item = entry.item;
            const phase = mapPaymentStatus(item.status);
            const tone = phase === "success" ? "success" : phase === "failed" || phase === "timeout" ? "error" : "pending";
            return (
              <PressScale
                accessibilityRole="button"
                onPress={() => router.push(`/customer/payment/${item.reference}`)}
                style={{
                  paddingVertical: 14,
                  paddingHorizontal: 4,
                  flexDirection: "row",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <View style={{ flex: 1, gap: 4 }}>
                  <Text style={{ color: theme.text, fontWeight: "700" }}>{item.merchant_name ?? "Merchant"}</Text>
                  <Text style={{ color: theme.muted }}>{formatMoney(item.amount, item.currency)}</Text>
                </View>
                <StatusPill label={paymentStatusLabel(item.status)} tone={tone} />
              </PressScale>
            );
          }}
        />
      </View>
      <BottomNav active="history" />
    </Screen>
  );
}
