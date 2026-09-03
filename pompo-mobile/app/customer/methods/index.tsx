import { useRouter, type Href } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";

import { BottomNav } from "@/components/nav";
import { Card, EmptyState, ErrorBanner, PrimaryButton, Screen, Title, useTheme } from "@/components/ui";
import { catalogOfferLabel, paymentMethodStateLabel } from "@/domain/paymentMethod";
import { useAuth } from "@/state/AuthProvider";
import type { PaymentMethod, PaymentMethodCatalogItem } from "@/types";

export default function PaymentMethodsScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [rows, setRows] = useState<PaymentMethod[] | null>(null);
  const [catalog, setCatalog] = useState<PaymentMethodCatalogItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [methods, offers] = await Promise.all([api.listPaymentMethods(), api.paymentMethodCatalog()]);
    if (methods.ok) {
      setRows(methods.data);
    } else {
      setRows([]);
      setError(methods.error.message);
    }
    if (offers.ok) {
      setCatalog(offers.data);
    } else if (!methods.ok) {
      setError(offers.error.message);
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  const enrolledKeys = useMemo(
    () => new Set((rows ?? []).map((row) => `${row.provider_code}:${row.instrument_type}`)),
    [rows],
  );
  const unavailableOffers = catalog.filter(
    (item) => !item.available && !enrolledKeys.has(`${item.provider_code}:${item.instrument_type}`),
  );

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8 }}>
        <Title>Payment methods</Title>
        <Text style={{ color: theme.subtle, marginBottom: 12 }}>
          Choose how you pay merchants. POMPO never stores PANs, CVVs, PINs, or tokens on this screen.
        </Text>
        {error ? <ErrorBanner message={error} /> : null}
        <ScrollView contentContainerStyle={{ gap: 12, paddingBottom: 24 }} showsVerticalScrollIndicator={false}>
          {rows === null ? (
            <Text style={{ color: theme.muted }}>Loading your methods…</Text>
          ) : rows.length === 0 ? (
            <EmptyState
              title="No methods yet"
              body="Add Airtel Money or a sandbox card. TNM and Standard Bank stay coming soon until their contracts exist."
            />
          ) : (
            rows.map((row) => (
              <Pressable
                key={row.id}
                accessibilityRole="button"
                accessibilityLabel={`${row.display_name} ${row.masked_identifier}`}
                onPress={() => router.push(`/customer/methods/${row.id}` as Href)}
              >
                <Card>
                  <Text style={{ color: theme.text, fontWeight: "800" }}>{row.display_name}</Text>
                  <Text style={{ color: theme.muted, marginTop: 4 }}>{row.masked_identifier}</Text>
                  <Text style={{ color: theme.subtle, marginTop: 6, fontSize: 12, fontWeight: "700" }}>
                    {paymentMethodStateLabel(row)}
                  </Text>
                </Card>
              </Pressable>
            ))
          )}
          {unavailableOffers.length ? (
            <View style={{ gap: 8, marginTop: 8 }}>
              <Text style={{ color: theme.text, fontWeight: "800" }}>Coming soon</Text>
              {unavailableOffers.map((item) => (
                <Card key={`${item.provider_code}-${item.instrument_type}`}>
                  <Text style={{ color: theme.text, fontWeight: "700" }}>{item.label}</Text>
                  <Text style={{ color: theme.subtle, marginTop: 4 }}>{catalogOfferLabel(item)}</Text>
                  <Text style={{ color: theme.muted, marginTop: 6, fontSize: 12, fontWeight: "700" }}>
                    NOT AVAILABLE
                  </Text>
                </Card>
              ))}
            </View>
          ) : null}
          <PrimaryButton label="Add payment method" onPress={() => router.push("/customer/methods/add" as Href)} />
        </ScrollView>
      </View>
      <BottomNav active="profile" />
    </Screen>
  );
}
