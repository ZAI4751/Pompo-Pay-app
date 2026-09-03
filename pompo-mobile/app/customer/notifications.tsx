import { useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { FlatList, Text, View } from "react-native";

import { BottomNav } from "@/components/nav";
import { Card, ErrorBanner, Screen, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import type { AppNotification } from "@/types";

export default function NotificationsScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [items, setItems] = useState<AppNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const result = await api.listNotifications();
    if (!result.ok) {
      setError(result.error.message);
      return;
    }
    setItems(result.data.items);
    setUnread(result.data.unread_count);
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8 }}>
        <Title>Notifications</Title>
        <Text style={{ color: theme.subtle, marginBottom: 12 }}>{unread} unread</Text>
        {error ? <ErrorBanner message={error} /> : null}
        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <Card>
              <Text style={{ color: theme.text, fontWeight: "700" }}>{item.title}</Text>
              <Text style={{ color: theme.muted }}>{item.body}</Text>
              {item.payment_reference ? (
                <Text
                  style={{ color: theme.primary, marginTop: 8 }}
                  onPress={() => router.push(`/customer/payment/${item.payment_reference}`)}
                >
                  Open payment
                </Text>
              ) : null}
            </Card>
          )}
        />
      </View>
      <BottomNav active="profile" />
    </Screen>
  );
}
