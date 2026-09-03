import { useRouter } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FlatList, RefreshControl, Text, View } from "react-native";

import { PaymentRow } from "@/components/activity";
import { GlassInput } from "@/components/glass";
import { BottomNav } from "@/components/nav";
import { EmptyState, ErrorBanner, Screen, Title, useTheme } from "@/components/ui";
import { groupLabel } from "@/format";
import { cachedPayments, isOffline, markOffline, markOnline, rememberPayments } from "@/offline/cache";
import { useAuth } from "@/state/AuthProvider";
import type { Payment } from "@/types";

type DateWindow = "" | "7d" | "30d";
type AmountWindow = "" | "under1000" | "over1000";

function createdFrom(window: DateWindow): string | undefined {
  if (!window) {
    return undefined;
  }
  const days = window === "7d" ? 7 : 30;
  const start = new Date();
  start.setUTCDate(start.getUTCDate() - days);
  return start.toISOString();
}

function FilterChip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  const theme = useTheme();
  return (
    <Text
      accessibilityRole="button"
      onPress={onPress}
      style={{
        color: active ? theme.primary : theme.muted,
        fontWeight: "700",
        fontSize: 12,
        paddingVertical: 6,
        paddingHorizontal: 4,
      }}
    >
      {label}
    </Text>
  );
}

export default function HistoryScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [rows, setRows] = useState<Payment[]>([]);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [dates, setDates] = useState<DateWindow>("");
  const [amount, setAmount] = useState<AmountWindow>("");

  const load = useCallback(async () => {
    setRefreshing(true);
    const result = await api.listMyPayments({
      q: query.trim() || undefined,
      status: status || undefined,
      created_from: createdFrom(dates),
      amount_max: amount === "under1000" ? "999.99" : undefined,
      amount_min: amount === "over1000" ? "1000" : undefined,
    });
    setRefreshing(false);
    if (!result.ok) {
      if (result.error.kind === "network") {
        markOffline();
        const cached = cachedPayments();
        if (cached.length) {
          setRows(cached);
          setError({ message: "You're offline. Showing the last payments loaded on this device." });
          return;
        }
      }
      setError({ message: result.error.message, requestId: result.error.requestId });
      return;
    }
    markOnline();
    rememberPayments(result.data);
    setError(null);
    setRows(result.data);
  }, [amount, api, dates, query, status]);

  useEffect(() => {
    void load();
    // Search text is applied on submit/refresh; other filters reload immediately.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, status, dates, amount]);

  const grouped = useMemo(() => {
    const items: ({ type: "header"; title: string } | { type: "row"; item: Payment; last: boolean })[] = [];
    let last = "";
    rows.forEach((item, index) => {
      const title = groupLabel(item.created_at);
      if (title !== last) {
        items.push({ type: "header", title });
        last = title;
      }
      const next = rows[index + 1];
      const lastInGroup = !next || groupLabel(next.created_at) !== title;
      items.push({ type: "row", item, last: lastInGroup });
    });
    return items;
  }, [rows]);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8 }}>
        <Title>Activity</Title>
        <Text style={{ color: theme.subtle, marginTop: 4, marginBottom: 12 }}>Receipts for payments you made</Text>
        <GlassInput
          placeholder="Search merchant or reference"
          value={query}
          onChangeText={setQuery}
          onSubmitEditing={() => void load()}
          style={{ marginBottom: 8 }}
        />
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 4, marginBottom: 4 }}>
          {["", "success", "failed", "processing"].map((value) => (
            <FilterChip
              key={value || "all"}
              label={value === "" ? "All" : value}
              active={status === value}
              onPress={() => setStatus(value)}
            />
          ))}
        </View>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 4, marginBottom: 4 }}>
          <FilterChip label="Any date" active={dates === ""} onPress={() => setDates("")} />
          <FilterChip label="7 days" active={dates === "7d"} onPress={() => setDates("7d")} />
          <FilterChip label="30 days" active={dates === "30d"} onPress={() => setDates("30d")} />
        </View>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 4, marginBottom: 8 }}>
          <FilterChip label="Any amount" active={amount === ""} onPress={() => setAmount("")} />
          <FilterChip label="Under 1,000" active={amount === "under1000"} onPress={() => setAmount("under1000")} />
          <FilterChip label="1,000+" active={amount === "over1000"} onPress={() => setAmount("over1000")} />
        </View>
        {isOffline() || error ? (
          <ErrorBanner message={error?.message ?? "Connection problem"} requestId={error?.requestId} />
        ) : null}
        <FlatList
          data={grouped}
          keyExtractor={(entry, index) =>
            entry.type === "header" ? `h-${entry.title}-${index}` : entry.item.id
          }
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void load()} />}
          contentContainerStyle={{ paddingBottom: 16 }}
          ListEmptyComponent={
            refreshing ? null : (
              <EmptyState title="No payments yet" body="Scan a QR to make your first payment. Offline history appears here after a successful load." />
            )
          }
          renderItem={({ item: entry }) => {
            if (entry.type === "header") {
              return (
                <Text style={{ color: theme.subtle, fontWeight: "800", marginTop: 16, marginBottom: 8 }}>
                  {entry.title}
                </Text>
              );
            }
            return (
              <View
                style={{
                  backgroundColor: theme.surface,
                  borderColor: theme.border,
                  borderWidth: 1,
                  borderBottomWidth: entry.last ? 1 : 0,
                  borderTopLeftRadius: 0,
                  borderTopRightRadius: 0,
                  overflow: "hidden",
                }}
              >
                <PaymentRow
                  payment={entry.item}
                  onPress={() => router.push(`/customer/payment/${entry.item.reference}`)}
                />
              </View>
            );
          }}
        />
      </View>
      <BottomNav active="history" />
    </Screen>
  );
}
