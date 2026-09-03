import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { AmountDisplay, FadeIn, InitialsAvatar } from "@/components/glass";
import { Card, formatMoney, Muted, PrimaryButton, Screen, SecondaryButton, useTheme } from "@/components/ui";
import { useCheckout } from "@/state/CheckoutProvider";

export default function ConfirmScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { session } = useCheckout();

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
      <Text style={[styles.title, { color: theme.text }]}>Here is exactly what you are paying.</Text>
      <Muted>POMPO sends this to the payment engine. Dynamic amounts come from the server.</Muted>
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
      <PrimaryButton label="Pay now" onPress={() => router.push("/customer/processing")} />
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
