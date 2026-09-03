import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import { ActionTile, PaymentRow, SectionHeader } from "@/components/activity";
import { FadeIn, HeroCard, PressScale } from "@/components/glass";
import { ModeSwitch } from "@/components/nav";
import { Card, EmptyState, ErrorBanner, Greeting, PrimaryButton, Screen, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import { useAppMode } from "@/state/ModeProvider";
import type { Merchant, MerchantAccessResponse, MerchantSummary, Payment } from "@/types";

export default function MerchantHome() {
  const theme = useTheme();
  const { user, api } = useAuth();
  const { setMode } = useAppMode();
  const router = useRouter();
  const [access, setAccess] = useState<MerchantAccessResponse | null>(null);
  const [merchant, setMerchant] = useState<Merchant | null>(null);
  const [recent, setRecent] = useState<Payment[]>([]);
  const [summary, setSummary] = useState<MerchantSummary | null>(null);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [checking, setChecking] = useState(true);
  const firstName = user?.full_name.split(" ")[0] ?? "there";

  useEffect(() => {
    let cancelled = false;
    setChecking(true);
    void api.getMerchantAccess().then((res) => {
      if (cancelled) return;
      setChecking(false);
      if (res.ok) {
        setAccess(res.data);
        if (!res.data.allowed) {
          return;
        }
      }
      if (user?.merchant_id) {
        void api.getMerchant(user.merchant_id).then((result) => {
          if (!cancelled && result.ok) {
            setMerchant(result.data);
          } else if (!cancelled && !result.ok && result.error.kind !== "forbidden") {
            setError({ message: result.error.message, requestId: result.error.requestId });
          }
        });
        void api.listMerchantPayments().then((result) => {
          if (!cancelled && result.ok) {
            setRecent(result.data.slice(0, 5));
          }
        });
        void api.merchantSummary().then((result) => {
          if (!cancelled && result.ok) {
            setSummary(result.data);
          }
        });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [api, user?.merchant_id]);

  if (!checking && access && !access.allowed) {
    return (
      <Screen padded={false}>
        <View style={{ flex: 1, padding: 20, justifyContent: "center" }}>
          <EmptyState
            title="Merchant Access Restricted"
            body={
              access.reason ||
              "This account is not authorized to access merchant tools or operate tills. Contact your organization administrator."
            }
          />
          <View style={{ marginTop: 20 }}>
            <PrimaryButton
              label="Return to Customer Home"
              onPress={() => {
                setMode("customer");
                router.replace("/customer");
              }}
            />
          </View>
        </View>
      </Screen>
    );
  }

  return (
    <Screen padded={false}>
      <View style={styles.body}>
        <View style={styles.top}>
          <Greeting name={firstName} subtitle="Merchant dashboard" />
          <ModeSwitch />
        </View>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
          <FadeIn>
            <PressScale
              accessibilityRole="button"
              accessibilityLabel="Show QR"
              onPress={() => router.push("/merchant/qr")}
            >
              <HeroCard>
                <Text style={styles.heroKicker}>TILL</Text>
                <View>
                  <Text style={styles.heroTitle}>Show QR</Text>
                  <Text style={styles.heroHint}>Display a code for customers to scan</Text>
                </View>
              </HeroCard>
            </PressScale>
          </FadeIn>
          <FadeIn delay={50}>
            <Card>
              <Text style={{ color: theme.subtle, fontSize: 11, fontWeight: "800", letterSpacing: 0.8 }}>BUSINESS</Text>
              <Text style={{ color: theme.text, fontSize: 22, fontWeight: "800" }}>
                {merchant?.name ?? access?.merchant?.name ?? "Your merchant"}
              </Text>
              <Text style={{ color: theme.muted }}>{user?.full_name}</Text>
              {summary ? (
                <Text style={{ color: theme.subtle, marginTop: 8 }}>
                  Today: {summary.payments_today} successful · {summary.total_today} {summary.currency}
                </Text>
              ) : null}
            </Card>
          </FadeIn>
          <FadeIn delay={90}>
            <View style={styles.actions}>
              <ActionTile label="QR" icon="qr-code-outline" onPress={() => router.push("/merchant/qr")} />
              <ActionTile label="Activity" icon="time-outline" onPress={() => router.push("/merchant/activity")} />
              <ActionTile label="Profile" icon="person-outline" onPress={() => router.push("/merchant/profile")} />
            </View>
          </FadeIn>
          <FadeIn delay={130}>
            <SectionHeader
              title="Recent activity"
              action="See all"
              onAction={() => router.push("/merchant/activity")}
            />
            <View style={[styles.list, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              {recent.length === 0 ? (
                <View style={styles.empty}>
                  <Text style={{ color: theme.text, fontWeight: "700" }}>Waiting for the first scan</Text>
                  <Text style={{ color: theme.subtle, fontSize: 12, textAlign: "center" }}>
                    Generate a QR, then watch payments land here.
                  </Text>
                </View>
              ) : (
                recent.map((payment, index) => (
                  <View
                    key={payment.id}
                    style={index === recent.length - 1 ? undefined : { borderBottomWidth: 1, borderBottomColor: theme.border }}
                  >
                    <PaymentRow
                      payment={payment}
                      emphasizeAmount
                      onPress={() => router.push(`/merchant/payment/${payment.reference}`)}
                    />
                  </View>
                ))
              )}
            </View>
          </FadeIn>
        </ScrollView>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  body: { flex: 1 },
  top: {
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 4,
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 12,
  },
  scroll: { paddingHorizontal: 20, paddingTop: 12, paddingBottom: 20, gap: 20 },
  heroKicker: { color: "rgba(255,255,255,0.72)", fontSize: 11, fontWeight: "800", letterSpacing: 1.6 },
  heroTitle: { color: "#ffffff", fontSize: 28, fontWeight: "800", letterSpacing: -0.6 },
  heroHint: { color: "rgba(255,255,255,0.82)", fontSize: 13, fontWeight: "600", marginTop: 6 },
  actions: { flexDirection: "row", gap: 8 },
  list: { borderRadius: 20, borderWidth: 1, overflow: "hidden" },
  empty: { paddingVertical: 28, paddingHorizontal: 16, alignItems: "center", gap: 6 },
});
