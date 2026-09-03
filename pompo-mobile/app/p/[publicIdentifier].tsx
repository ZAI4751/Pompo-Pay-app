import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { AmountDisplay, FadeIn } from "@/components/glass";
import {
  Card,
  ErrorBanner,
  formatMoney,
  PrimaryButton,
  Screen,
  SecondaryButton,
  Title,
  useTheme,
} from "@/components/ui";
import { extractPublicIdentifier } from "@/domain/qrPayload";
import { useAuth } from "@/state/AuthProvider";
import { useCheckout } from "@/state/CheckoutProvider";
import type { QrInspect } from "@/types";

export default function UniversalQrDeepLinkScreen() {
  const { publicIdentifier } = useLocalSearchParams<{ publicIdentifier: string }>();
  const theme = useTheme();
  const router = useRouter();
  const { user, api } = useAuth();
  const { begin } = useCheckout();

  const [inspect, setInspect] = useState<QrInspect | null>(null);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function resolve() {
      if (!publicIdentifier) {
        setError({ message: "No QR code identifier provided" });
        setLoading(false);
        return;
      }
      const extracted = extractPublicIdentifier(publicIdentifier);
      if (!extracted.ok) {
        setError({ message: extracted.message });
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      const res = await api.inspectQr(extracted.publicIdentifier);
      if (!active) return;
      setLoading(false);
      if (!res.ok) {
        setError({ message: res.error.message, requestId: res.error.requestId });
        return;
      }
      setInspect(res.data);
      const initialAmount = res.data.qr_type === "dynamic" ? (res.data.amount ?? "") : "";
      begin(extracted.publicIdentifier, res.data, initialAmount);
    }

    void resolve();
    return () => {
      active = false;
    };
  }, [api, begin, publicIdentifier]);

  function onProceed() {
    if (!inspect) return;
    if (user) {
      router.replace("/customer/preview");
    } else {
      router.push("/login");
    }
  }

  return (
    <Screen>
      <Title>POMPO Checkout</Title>
      <Text style={{ color: theme.muted, marginBottom: 16 }}>
        Universal QR detected. Complete your payment securely.
      </Text>

      {error ? (
        <FadeIn>
          <ErrorBanner message={error.message} requestId={error.requestId} />
          <View style={styles.buttonGap}>
            <PrimaryButton label="Scan another QR" onPress={() => router.replace("/customer/scan")} />
            <SecondaryButton label="Return Home" onPress={() => router.replace("/customer")} />
          </View>
        </FadeIn>
      ) : loading ? (
        <Card>
          <Text style={{ color: theme.text, fontWeight: "700" }}>Resolving payment request…</Text>
          <Text style={{ color: theme.muted, marginTop: 4 }}>Connecting to POMPO network</Text>
        </Card>
      ) : inspect ? (
        <FadeIn>
          <Card>
            <Text style={{ color: theme.subtle, fontSize: 13, textTransform: "uppercase", letterSpacing: 0.5 }}>
              Paying
            </Text>
            <Text style={{ color: theme.text, fontWeight: "800", fontSize: 20, marginTop: 2 }}>
              {inspect.merchant_name}
            </Text>
            <Text style={{ color: theme.muted, fontSize: 13, marginTop: 2 }}>
              {inspect.branch_name} · {inspect.till_name}
            </Text>

            <View style={{ marginVertical: 14 }}>
              {inspect.qr_type === "dynamic" && inspect.amount ? (
                <AmountDisplay value={formatMoney(inspect.amount, inspect.currency)} />
              ) : (
                <Text style={{ color: theme.text, fontWeight: "600", fontSize: 16 }}>
                  Static QR · Enter amount at checkout
                </Text>
              )}
            </View>

            <View style={[styles.badgeRow, { borderColor: theme.border }]}>
              <Text style={{ color: theme.muted, fontSize: 12 }}>Status</Text>
              <Text style={{ color: theme.success, fontSize: 12, fontWeight: "700", textTransform: "uppercase" }}>
                {inspect.status}
              </Text>
            </View>
          </Card>

          <View style={styles.buttonGap}>
            <PrimaryButton
              label={user ? "Proceed to checkout" : "Sign in to pay"}
              onPress={onProceed}
            />
            {!user ? (
              <SecondaryButton
                label="Create a POMPO account"
                onPress={() => router.push("/register")}
              />
            ) : null}
            <SecondaryButton label="Cancel" onPress={() => router.back()} />
          </View>
        </FadeIn>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  buttonGap: {
    gap: 10,
    marginTop: 20,
  },
  badgeRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingTop: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
});
