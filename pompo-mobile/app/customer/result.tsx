import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { Card, formatMoney, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { mapPaymentStatus, paymentStatusLabel } from "@/domain/paymentStatus";
import { useCheckout } from "@/state/CheckoutProvider";

export default function ResultScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { session, clear } = useCheckout();
  const payment = session?.payment;
  const phase = payment ? mapPaymentStatus(payment.status) : "unknown";
  const success = phase === "success";

  return (
    <Screen>
      <Title>{success ? "Paid" : paymentStatusLabel(payment?.status ?? "unknown")}</Title>
      <Card style={{ backgroundColor: success ? theme.successBg : theme.errorBg }}>
        <Text style={[styles.headline, { color: success ? theme.success : theme.error }]}>
          {success ? "Payment successful" : "Payment did not complete"}
        </Text>
        {session ? (
          <Text style={{ color: theme.text, fontWeight: "700" }}>{session.inspect.merchant_name}</Text>
        ) : null}
        {payment ? (
          <View style={{ gap: 4 }}>
            <Text style={{ color: theme.text, fontSize: 28, fontWeight: "800" }}>
              {formatMoney(payment.amount, payment.currency)}
            </Text>
            <Text style={{ color: theme.muted }}>{payment.reference}</Text>
            {payment.failure_reason ? <Text style={{ color: theme.error }}>{payment.failure_reason}</Text> : null}
          </View>
        ) : (
          <Text style={{ color: theme.muted }}>No payment was created.</Text>
        )}
      </Card>
      <PrimaryButton
        label="Done"
        onPress={() => {
          const reference = payment?.reference;
          clear();
          if (reference) {
            router.replace(`/customer/payment/${reference}`);
            return;
          }
          router.replace("/customer");
        }}
      />
      <SecondaryButton
        label="Home"
        onPress={() => {
          clear();
          router.replace("/customer");
        }}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  headline: { fontSize: 18, fontWeight: "800" },
});
