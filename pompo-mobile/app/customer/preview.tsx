import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { useState } from "react";
import { KeyboardAvoidingView, Platform, StyleSheet, Text, View } from "react-native";

import { AmountDisplay, CircleButton, FadeIn, GlassInput, InitialsAvatar } from "@/components/glass";
import { Card, ErrorBanner, formatMoney, PrimaryButton, Screen, useTheme } from "@/components/ui";
import { useCheckout } from "@/state/CheckoutProvider";

export default function PreviewScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { session, begin } = useCheckout();
  const [amount, setAmount] = useState(session?.amount ?? "");
  const [error, setError] = useState<string | null>(null);

  if (!session) {
    return (
      <Screen>
        <Text style={{ color: theme.text, fontWeight: "800", fontSize: 22 }}>No QR</Text>
        <Text style={{ color: theme.muted }}>Scan a code to continue.</Text>
      </Screen>
    );
  }

  const isDynamic = session.inspect.qr_type === "dynamic";
  const displayAmount = isDynamic ? (session.inspect.amount ?? session.amount) : amount;

  return (
    <Screen>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1, gap: 16 }}>
        <View style={styles.top}>
          <CircleButton accessibilityLabel="Go back" onPress={() => router.back()}>
            <Ionicons name="chevron-back" size={18} color={theme.text} />
          </CircleButton>
          <Text style={[styles.pageTitle, { color: theme.text }]}>Merchant</Text>
        </View>
        <FadeIn>
          <Card>
            <View style={styles.identity}>
              <InitialsAvatar name={session.inspect.merchant_name} size={52} active />
              <View style={{ flex: 1 }}>
                <Text style={{ color: theme.subtle, fontSize: 11, fontWeight: "800", letterSpacing: 0.8 }}>
                  PAYING
                </Text>
                <Text style={[styles.merchant, { color: theme.text }]}>{session.inspect.merchant_name}</Text>
                <Text style={{ color: theme.muted, marginTop: 2 }}>
                  {session.inspect.branch_name} · {session.inspect.till_name}
                </Text>
              </View>
            </View>
            {isDynamic ? (
              <AmountDisplay value={formatMoney(displayAmount, session.inspect.currency)} />
            ) : (
              <View style={{ gap: 8 }}>
                <Text style={{ color: theme.muted }}>Enter the amount to pay.</Text>
                <GlassInput
                  keyboardType="decimal-pad"
                  value={amount}
                  onChangeText={setAmount}
                  placeholder="0.00"
                  style={styles.input}
                />
              </View>
            )}
          </Card>
        </FadeIn>
        {error ? <ErrorBanner message={error} /> : null}
        <PrimaryButton
          label="Continue"
          onPress={() => {
            if (!isDynamic) {
              const parsed = Number(amount);
              if (!amount.trim() || Number.isNaN(parsed) || parsed <= 0) {
                setError("Enter a valid amount.");
                return;
              }
              begin(session.payload, session.inspect, Number(parsed).toFixed(2));
            }
            router.push("/customer/confirm");
          }}
        />
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  top: { flexDirection: "row", alignItems: "center", gap: 12 },
  pageTitle: { fontSize: 18, fontWeight: "800" },
  identity: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 8 },
  merchant: { fontSize: 22, fontWeight: "800", letterSpacing: -0.4 },
  input: { fontSize: 28, fontWeight: "800" },
});
