import { useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { FlatList, Text, View } from "react-native";

import { Card, EmptyState, ErrorBanner, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import type { AppNotification } from "@/types";

export default function NotificationsScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [items, setItems] = useState<AppNotification[] | null>(null);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const result = await api.listNotifications();
    if (!result.ok) {
      setError(result.error.message);
      setItems([]);
      return;
    }
    setItems(result.data.items);
    setUnread(result.data.unread_count);
    setError(null);
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8 }}>
        <Title>Notifications</Title>
        <Text style={{ color: theme.subtle, marginBottom: 12 }}>
          {unread} unread · payments, requests, and support updates
        </Text>
        {error ? <ErrorBanner message={error} /> : null}
        {unread > 0 ? (
          <SecondaryButton
            label="Mark all read"
            onPress={async () => {
              const result = await api.markAllNotificationsRead();
              if (result.ok) {
                setItems(result.data.items);
                setUnread(result.data.unread_count);
              } else {
                setError(result.error.message);
              }
            }}
          />
        ) : null}
        <FlatList
          data={items ?? []}
          keyExtractor={(item) => item.id}
          ListEmptyComponent={
            items === null ? (
              <Text style={{ color: theme.muted, marginTop: 16 }}>Loading inbox…</Text>
            ) : (
              <EmptyState
                title="You're all caught up"
                body="Payment results, requests, and support replies will appear here. POMPO never invents notifications."
              />
            )
          }
          renderItem={({ item }) => (
            <Card>
              <Text style={{ color: theme.text, fontWeight: "700" }}>{item.title}</Text>
              <Text style={{ color: theme.muted }}>{item.body}</Text>
              <Text style={{ color: theme.subtle, marginTop: 6, fontSize: 11 }}>
                {item.notification_type.replace(/_/g, " ")}
                {item.read_at ? "" : " · UNREAD"}
              </Text>
              {item.payment_reference ? (
                <Text
                  accessibilityRole="link"
                  style={{ color: theme.primary, marginTop: 8 }}
                  onPress={() => router.push(`/customer/payment/${item.payment_reference}`)}
                >
                  Open receipt
                </Text>
              ) : null}
              {!item.read_at ? (
                <Text
                  accessibilityRole="button"
                  style={{ color: theme.subtle, marginTop: 8, fontWeight: "700" }}
                  onPress={async () => {
                    const result = await api.markNotificationRead(item.id);
                    if (result.ok) {
                      await load();
                    }
                  }}
                >
                  Mark read
                </Text>
              ) : null}
            </Card>
          )}
        />
      </View>
    </Screen>
  );
}
