import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { AmountDisplay, FadeIn, InitialsAvatar, SuccessMark } from "@/components/glass";
import { Card, formatMoney, PrimaryButton, Screen, SecondaryButton, useTheme } from "@/components/ui";
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
      <View style={styles.center}>
        {success ? <SuccessMark /> : null}
        <FadeIn delay={success ? 80 : 0}>
          <Text style={[styles.title, { color: theme.text }]}>
            {success ? "Paid" : paymentStatusLabel(payment?.status ?? "unknown")}
          </Text>
        </FadeIn>
      </View>
      <FadeIn delay={140}>
        <Card>
          <Text style={[styles.headline, { color: success ? theme.success : theme.error }]}>
            {success ? "Payment successful" : "Payment did not complete"}
          </Text>
          <Text style={{ color: theme.muted, marginBottom: 12 }}>
            {success
              ? "That payment went through."
              : timedOut
                ? "The provider did not confirm in time. You can check the payment or try again."
                : "You can try again or review the payment."}
          </Text>
          {session ? (
            <View style={styles.identity}>
              <InitialsAvatar name={session.inspect.merchant_name} size={40} active={success} />
              <Text style={{ color: theme.text, fontWeight: "800", flex: 1 }}>{session.inspect.merchant_name}</Text>
            </View>
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
      </FadeIn>
      <PrimaryButton
        label={success ? "Done" : "View payment"}
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
  center: { alignItems: "center", gap: 12, paddingTop: 8 },
  title: { fontSize: 28, fontWeight: "800", letterSpacing: -0.6 },
  headline: { fontSize: 18, fontWeight: "800" },
  identity: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 8 },
});
