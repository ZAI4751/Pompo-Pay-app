import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { AmountDisplay, SuccessMark } from "@/components/glass";
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
  const timedOut = phase === "timeout";

  return (
    <Screen>
      <Title>{success ? "Paid" : paymentStatusLabel(payment?.status ?? "unknown")}</Title>
      {success ? <SuccessMark /> : null}
      <Card style={{ backgroundColor: success ? theme.successBg : theme.errorBg }}>
        <Text style={[styles.headline, { color: success ? theme.success : theme.error }]}>
          {success ? "Payment successful" : "Payment did not complete"}
        </Text>
        <Text style={{ color: theme.muted, marginBottom: 8 }}>
          {success
            ? "That payment went through."
            : timedOut
              ? "The provider did not confirm in time. You can check the transaction or try again."
              : "You can try again or review the transaction."}
        </Text>
        {session ? (
          <Text style={{ color: theme.text, fontWeight: "700" }}>{session.inspect.merchant_name}</Text>
        ) : null}
        {payment ? (
          <View style={{ gap: 4 }}>
            <AmountDisplay value={formatMoney(payment.amount, payment.currency)} />
            <Text style={{ color: theme.muted }}>{payment.reference}</Text>
            {payment.completed_at ? (
              <Text style={{ color: theme.subtle }}>{new Date(payment.completed_at).toLocaleString()}</Text>
            ) : null}
            {payment.failure_reason ? <Text style={{ color: theme.error }}>{payment.failure_reason}</Text> : null}
          </View>
        ) : (
          <Text style={{ color: theme.muted }}>No payment was created.</Text>
        )}
      </Card>
      <PrimaryButton
        label={success ? "Done" : "View Transaction"}
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
      {success ? (
        <SecondaryButton
          label="Home"
          onPress={() => {
            clear();
            router.replace("/customer");
          }}
        />
      ) : (
        <SecondaryButton
          label="Try Again"
          onPress={() => {
            clear();
            router.replace("/customer/scan");
          }}
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  headline: { fontSize: 18, fontWeight: "800" },
});
