import { useRouter, type Href } from "expo-router";
import { useEffect, useState } from "react";
import { Text, View } from "react-native";

import { Card, ErrorBanner, GlassInput, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { catalogOfferLabel } from "@/domain/paymentMethod";
import { useAuth } from "@/state/AuthProvider";
import type { PaymentMethodCatalogItem } from "@/types";

export default function AddPaymentMethodScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [catalog, setCatalog] = useState<PaymentMethodCatalogItem[]>([]);
  const [selected, setSelected] = useState<PaymentMethodCatalogItem | null>(null);
  const [msisdn, setMsisdn] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void api.paymentMethodCatalog().then((result) => {
      if (result.ok) setCatalog(result.data);
      else setError(result.error.message);
    });
  }, [api]);

  async function enroll() {
    if (!selected) {
      return;
    }
    setBusy(true);
    setError(null);
    const body: {
      provider_code: string;
      instrument_type: string;
      msisdn?: string;
      card_last4?: string;
    } = {
      provider_code: selected.provider_code,
      instrument_type: selected.instrument_type,
    };
    if (selected.instrument_type === "mobile_money") {
      body.msisdn = msisdn;
    } else if (selected.instrument_type === "visa") {
      body.card_last4 = "4242";
    } else if (selected.instrument_type === "mastercard") {
      body.card_last4 = "0912";
    }
    const result = await api.addPaymentMethod(body);
    setBusy(false);
    if (!result.ok) {
      setError(result.error.message);
      return;
    }
    router.replace("/customer/methods" as Href);
  }

  return (
    <Screen>
      <Title>Add payment method</Title>
      <Text style={{ color: theme.subtle }}>
        Choose a type. Unavailable providers stay unavailable until their contract exists.
      </Text>
      {error ? <ErrorBanner message={error} /> : null}
      {catalog.map((item) => (
        <Card key={`${item.provider_code}-${item.instrument_type}`}>
          <Text style={{ color: theme.text, fontWeight: "800" }}>{item.label}</Text>
          <Text style={{ color: theme.muted, marginTop: 4 }}>{catalogOfferLabel(item)}</Text>
          {item.available ? (
            <PrimaryButton
              label={selected?.label === item.label ? "Selected" : "Select"}
              onPress={() => setSelected(item)}
            />
          ) : (
            <Text style={{ color: theme.subtle, marginTop: 8, fontWeight: "700" }}>Coming soon</Text>
          )}
        </Card>
      ))}
      {selected?.available && selected.instrument_type === "mobile_money" ? (
        <View style={{ gap: 8 }}>
          <Text style={{ color: theme.muted }}>Mobile-money number (not a PIN)</Text>
          <GlassInput placeholder="+265 88…" keyboardType="phone-pad" value={msisdn} onChangeText={setMsisdn} />
        </View>
      ) : null}
      {selected?.available && selected.instrument_type !== "mobile_money" ? (
        <Text style={{ color: theme.muted }}>
          Sandbox cards use a masked test identifier only. No PAN or CVV is collected.
        </Text>
      ) : null}
      <PrimaryButton
        label="Save method"
        loading={busy}
        onPress={() => void enroll()}
        disabled={!selected?.available}
      />
      <SecondaryButton label="Cancel" onPress={() => router.back()} />
    </Screen>
  );
}
