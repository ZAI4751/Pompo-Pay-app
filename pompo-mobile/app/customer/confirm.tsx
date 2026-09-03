import { useRouter, type Href } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { AmountDisplay, FadeIn, InitialsAvatar } from "@/components/glass";
import { Card, ErrorBanner, formatMoney, Muted, PrimaryButton, Screen, SecondaryButton, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import { useCheckout } from "@/state/CheckoutProvider";
import type { PaymentMethod } from "@/types";

export default function ConfirmScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const { session, selectPaymentMethod } = useCheckout();
  const [methods, setMethods] = useState<PaymentMethod[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const result = await api.listPaymentMethods();
    if (!result.ok) {
      setError(result.error.message);
      return;
    }
    setMethods(result.data);
    if (!session?.paymentMethodId) {
      const preferred = result.data.find((row) => row.is_default) ?? result.data[0];
      if (preferred) {
        selectPaymentMethod(preferred.id);
      }
    }
  }, [api, selectPaymentMethod, session?.paymentMethodId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!session) {
    return (
      <Screen>
        <Text style={{ color: theme.text, fontWeight: "800", fontSize: 22 }}>Nothing to confirm</Text>
      </Screen>
    );
  }

  const amount = session.inspect.qr_type === "dynamic" ? (session.inspect.amount ?? session.amount) : session.amount;

  return (
    <Screen>
      <Text style={[styles.kicker, { color: theme.subtle }]}>CONFIRM</Text>
      <Text style={[styles.title, { color: theme.text }]}>PAY {formatMoney(amount, session.inspect.currency)}</Text>
      <Muted>{session.inspect.merchant_name}</Muted>
      <FadeIn>
        <Card>
          <View style={styles.identity}>
            <InitialsAvatar name={session.inspect.merchant_name} size={48} active />
            <View style={{ flex: 1 }}>
              <Text style={{ color: theme.subtle, fontSize: 12 }}>Paying</Text>
              <Text style={[styles.merchant, { color: theme.text }]}>{session.inspect.merchant_name}</Text>
            </View>
          </View>
          <AmountDisplay value={formatMoney(amount, session.inspect.currency)} />
          <Text style={{ color: theme.muted }}>
            {session.inspect.branch_name} · {session.inspect.till_name}
          </Text>
        </Card>
      </FadeIn>
      <Text style={{ color: theme.text, fontWeight: "800", marginTop: 4 }}>How would you like to pay?</Text>
      {error ? <ErrorBanner message={error} /> : null}
      {methods.map((row) => {
        const selected = session.paymentMethodId === row.id;
        return (
          <Pressable key={row.id} onPress={() => selectPaymentMethod(row.id)}>
            <Card
              style={{
                borderWidth: 2,
                borderColor: selected ? theme.primary : theme.border,
              }}
            >
              <Text style={{ color: theme.text, fontWeight: "800" }}>{row.display_name}</Text>
              <Text style={{ color: theme.muted }}>{row.masked_identifier}</Text>
              <Text style={{ color: theme.subtle, fontSize: 12, marginTop: 4 }}>
                {row.status.toUpperCase()}
                {row.is_default ? " · DEFAULT" : ""}
                {row.is_sandbox ? " · TEST" : ""}
              </Text>
            </Card>
          </Pressable>
        );
      })}
      <SecondaryButton label="+ Add payment method" onPress={() => router.push("/customer/methods/add" as Href)} />
      <PrimaryButton
        label={`PAY ${formatMoney(amount, session.inspect.currency)}`}
        disabled={!session.paymentMethodId}
        onPress={() => {
          if (!session.paymentMethodId) {
            setError("Choose how to pay.");
            return;
          }
          router.push("/customer/processing");
        }}
      />
      <SecondaryButton label="Cancel" onPress={() => router.replace("/customer")} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  kicker: { fontSize: 11, fontWeight: "800", letterSpacing: 1.4 },
  title: { fontSize: 26, fontWeight: "800", letterSpacing: -0.6, lineHeight: 32 },
  identity: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 8 },
  merchant: { fontSize: 20, fontWeight: "800" },
});
