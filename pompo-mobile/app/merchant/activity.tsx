import { useRouter } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FlatList, RefreshControl, Text, View } from "react-native";

import { PaymentRow } from "@/components/activity";
import { GlassInput, PressScale } from "@/components/glass";
import { BottomNav } from "@/components/nav";
import { EmptyState, ErrorBanner, Screen, Title, useTheme } from "@/components/ui";
import { mapPaymentStatus } from "@/domain/paymentStatus";
import { useAuth } from "@/state/AuthProvider";
import type { Payment } from "@/types";

export default function MerchantActivity() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [rows, setRows] = useState<Payment[]>([]);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");

  const load = useCallback(async () => {
    setRefreshing(true);
    const result = await api.listMerchantPayments({
      q: query.trim() || undefined,
      status: status || undefined,
    });
    setRefreshing(false);
    if (!result.ok) {
      setError({ message: result.error.message, requestId: result.error.requestId });
      return;
    }
    setError(null);
    setRows(result.data);
  }, [api, query, status]);

  useEffect(() => {
    void load();
    // Search text is applied on submit/refresh; status changes reload immediately.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, status]);

  const incoming = useMemo(
    () => rows.filter((row) => mapPaymentStatus(row.status) === "success").length,
    [rows],
  );

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8 }}>
        <Title>Activity</Title>
        <Text style={{ color: theme.subtle, marginTop: 4, marginBottom: 12 }}>
          {incoming} settled payments in this list
        </Text>
        <GlassInput
          placeholder="Search reference or description"
          value={query}
          onChangeText={setQuery}
          onSubmitEditing={() => void load()}
          style={{ marginBottom: 8 }}
        />
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
          {[
            { value: "", label: "All" },
            { value: "success", label: "Success" },
            { value: "failed", label: "Failed" },
            { value: "processing", label: "Processing" },
          ].map((item) => {
            const active = status === item.value;
            return (
              <PressScale
                key={item.label}
                accessibilityRole="button"
                accessibilityState={{ selected: active }}
                onPress={() => setStatus(item.value)}
                hitSlop={6}
                style={{
                  paddingVertical: 8,
                  paddingHorizontal: 14,
                  borderRadius: 20,
                  backgroundColor: active
                    ? theme.scheme === "dark"
                      ? "#1e3a8a"
                      : "#eff6ff"
                    : theme.surface,
                  borderWidth: 1,
                  borderColor: active ? theme.primary : theme.border,
                  minHeight: 36,
                  justifyContent: "center",
                  alignItems: "center",
                }}
              >
                <Text
                  style={{
                    color: active ? theme.primary : theme.text,
                    fontWeight: active ? "700" : "500",
                    fontSize: 13,
                  }}
                >
                  {item.label}
                </Text>
              </PressScale>
            );
          })}
        </View>
        {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
        <FlatList
          data={rows}
          keyExtractor={(item) => item.id}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void load()} />}
          contentContainerStyle={{ paddingBottom: 16 }}
          ListEmptyComponent={
            refreshing ? null : (
              <EmptyState title="No payments yet" body="Generate a QR and take a customer payment." />
            )
          }
          renderItem={({ item, index }) => (
            <View
              style={{
                backgroundColor: theme.surface,
                borderColor: theme.border,
                borderWidth: 1,
                borderBottomWidth: index === rows.length - 1 ? 1 : 0,
                borderTopLeftRadius: index === 0 ? 20 : 0,
                borderTopRightRadius: index === 0 ? 20 : 0,
                borderBottomLeftRadius: index === rows.length - 1 ? 20 : 0,
                borderBottomRightRadius: index === rows.length - 1 ? 20 : 0,
                overflow: "hidden",
              }}
            >
              <PaymentRow
                payment={item}
                emphasizeAmount
                onPress={() => router.push(`/merchant/payment/${item.reference}`)}
              />
            </View>
          )}
        />
      </View>
      <BottomNav active="activity" />
    </Screen>
  );
}
