import { useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { FlatList, Text, View } from "react-native";

import { BottomNav } from "@/components/nav";
import { Card, ErrorBanner, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import type { FavoriteMerchant } from "@/types";

export default function MerchantsScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [rows, setRows] = useState<FavoriteMerchant[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const result = await api.listMyMerchants();
    if (result.ok) setRows(result.data);
    else setError(result.error.message);
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8 }}>
        <Title>Merchants</Title>
        <Text style={{ color: theme.subtle, marginBottom: 12 }}>Recent and favourite merchants from your payments.</Text>
        {error ? <ErrorBanner message={error} /> : null}
        <FlatList
          data={rows}
          keyExtractor={(item) => item.merchant_id}
          renderItem={({ item }) => (
            <Card>
              <Text style={{ color: theme.text, fontWeight: "800" }}>{item.merchant_name}</Text>
              <Text style={{ color: theme.muted }}>
                {item.payment_count} payments{item.is_favorite ? " · Favourite" : ""}
              </Text>
              {item.last_payment_reference && item.is_active ? (
                <SecondaryButton
                  label="Pay again"
                  onPress={() =>
                    router.push({
                      pathname: "/customer/repeat/[reference]",
                      params: { reference: item.last_payment_reference ?? "" },
                    })
                  }
                />
              ) : null}
              <SecondaryButton
                label={item.is_favorite ? "Remove favourite" : "Favourite"}
                onPress={async () => {
                  if (item.is_favorite) {
                    await api.removeFavorite(item.merchant_id);
                  } else {
                    await api.addFavorite(item.merchant_id);
                  }
                  await load();
                }}
              />
            </Card>
          )}
        />
      </View>
      <BottomNav active="profile" />
    </Screen>
  );
}
