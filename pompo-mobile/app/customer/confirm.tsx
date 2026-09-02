import { useRouter } from "expo-router";
import { StyleSheet, Text } from "react-native";

import { AmountDisplay, FadeIn } from "@/components/glass";
import { Card, formatMoney, Muted, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { useCheckout } from "@/state/CheckoutProvider";

export default function ConfirmScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { session } = useCheckout();

  if (!session) {
    return (
      <Screen>
        <Title>Nothing to confirm</Title>
      </Screen>
    );
  }

  const amount = session.inspect.qr_type === "dynamic" ? (session.inspect.amount ?? session.amount) : session.amount;

  return (
    <Screen>
      <Title>Confirm payment</Title>
      <Muted>POMPO will send this to the payment engine. Amounts come from the server for dynamic QR.</Muted>
      <FadeIn>
        <Card>
          <Text style={{ color: theme.subtle }}>Paying</Text>
          <Text style={[styles.merchant, { color: theme.text }]}>{session.inspect.merchant_name}</Text>
          <AmountDisplay value={formatMoney(amount, session.inspect.currency)} />
        </Card>
      </FadeIn>
      <PrimaryButton label="Pay now" onPress={() => router.push("/customer/processing")} />
      <SecondaryButton label="Cancel" onPress={() => router.replace("/customer")} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  merchant: { fontSize: 20, fontWeight: "700" },
});
