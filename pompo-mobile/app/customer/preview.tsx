import { useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { AmountDisplay, FadeIn, GlassInput } from "@/components/glass";
import { Card, ErrorBanner, formatMoney, Muted, PrimaryButton, Screen, Title, useTheme } from "@/components/ui";
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
        <Title>No QR</Title>
        <Muted>Scan a code to continue.</Muted>
      </Screen>
    );
  }

  const isDynamic = session.inspect.qr_type === "dynamic";
  const displayAmount = isDynamic ? (session.inspect.amount ?? session.amount) : amount;

  return (
    <Screen>
      <Title>Verify</Title>
      <Muted>Confirm this is the right merchant before you pay.</Muted>
      <FadeIn>
        <Card>
          <Text style={{ color: theme.subtle, fontSize: 12, fontWeight: "700", letterSpacing: 0.8 }}>MERCHANT</Text>
          <Text style={[styles.merchant, { color: theme.text }]}>{session.inspect.merchant_name}</Text>
          <Text style={{ color: theme.muted }}>
            {session.inspect.branch_name} · {session.inspect.till_name}
          </Text>
          {isDynamic ? (
            <AmountDisplay value={formatMoney(displayAmount, session.inspect.currency)} />
          ) : (
            <View style={{ gap: 8 }}>
              <Muted>Enter the amount to pay.</Muted>
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
    </Screen>
  );
}

const styles = StyleSheet.create({
  merchant: { fontSize: 22, fontWeight: "700" },
  input: { fontSize: 24, fontWeight: "700" },
});
