import { useCallback, useEffect, useState } from "react";
import { Switch, Text, View } from "react-native";

import { BottomNav } from "@/components/nav";
import { Card, ErrorBanner, Screen, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import type { CustomerPreferences } from "@/types";

const ROWS: { key: keyof Pick<CustomerPreferences, "notify_payment_success" | "notify_payment_failed" | "notify_payment_updates" | "notify_payment_requests">; label: string; hint: string }[] = [
  { key: "notify_payment_success", label: "Paid payments", hint: "When a payment succeeds" },
  { key: "notify_payment_failed", label: "Failed payments", hint: "When a payment fails or times out" },
  { key: "notify_payment_updates", label: "Payment updates", hint: "Processing and status changes" },
  { key: "notify_payment_requests", label: "Payment requests", hint: "When someone asks you to pay" },
];

export default function PreferencesScreen() {
  const theme = useTheme();
  const { api } = useAuth();
  const [prefs, setPrefs] = useState<CustomerPreferences | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const result = await api.getPreferences();
    if (!result.ok) {
      setError(result.error.message);
      return;
    }
    setError(null);
    setPrefs(result.data);
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggle(key: (typeof ROWS)[number]["key"], value: boolean) {
    if (!prefs || saving) {
      return;
    }
    setSaving(true);
    const result = await api.updatePreferences({ [key]: value });
    setSaving(false);
    if (!result.ok) {
      setError(result.error.message);
      return;
    }
    setError(null);
    setPrefs(result.data);
  }

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8, gap: 12 }}>
        <Title>Notifications</Title>
        <Text style={{ color: theme.muted }}>
          These flags are stored on your POMPO profile. They do not send SMS or email until a gateway is configured.
        </Text>
        {error ? <ErrorBanner message={error} /> : null}
        <Card>
          {prefs ? (
            ROWS.map((row, index) => (
              <View
                key={row.key}
                style={{
                  flexDirection: "row",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 12,
                  paddingVertical: 10,
                  borderBottomWidth: index === ROWS.length - 1 ? 0 : 1,
                  borderBottomColor: theme.border,
                }}
              >
                <View style={{ flex: 1 }}>
                  <Text style={{ color: theme.text, fontWeight: "700" }}>{row.label}</Text>
                  <Text style={{ color: theme.subtle, fontSize: 12 }}>{row.hint}</Text>
                </View>
                <Switch
                  value={prefs[row.key]}
                  onValueChange={(value) => void toggle(row.key, value)}
                  disabled={saving}
                />
              </View>
            ))
          ) : (
            <Text style={{ color: theme.muted }}>Loading preferences…</Text>
          )}
        </Card>
      </View>
      <BottomNav active="profile" />
    </Screen>
  );
}
