import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import { ActionTile, PaymentRow, SectionHeader } from "@/components/activity";
import { FadeIn, HeroCard, IconWell, PressScale } from "@/components/glass";
import { BottomNav, ModeSwitch } from "@/components/nav";
import { Greeting, Screen, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import { useAppMode } from "@/state/ModeProvider";
import type { Payment } from "@/types";

export default function CustomerHome() {
  const theme = useTheme();
  const { user, api } = useAuth();
  const { canSwitch, setMode } = useAppMode();
  const router = useRouter();
  const firstName = user?.full_name.split(" ")[0] ?? "there";
  const [recent, setRecent] = useState<Payment[]>([]);

  useEffect(() => {
    void api.listMyPayments().then((result) => {
      if (result.ok) {
        setRecent(result.data.slice(0, 5));
      }
    });
  }, [api]);

  return (
    <Screen padded={false}>
      <View style={styles.body}>
        <View style={styles.top}>
          <Greeting name={firstName} subtitle="Welcome back" />
          <ModeSwitch />
        </View>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <FadeIn>
            <PressScale
              accessibilityRole="button"
              accessibilityLabel="Scan QR"
              onPress={() => router.push("/customer/scan")}
            >
              <HeroCard>
                <View style={styles.heroTop}>
                  <Text style={styles.heroKicker}>POMPO</Text>
                  <View style={styles.heroBadge}>
                    <Text style={styles.heroBadgeText}>Scan</Text>
                  </View>
                </View>
                <View>
                  <Text style={styles.heroTitle}>Scan & pay</Text>
                  <Text style={styles.heroHint}>OPEN → SCAN → PAY</Text>
                </View>
              </HeroCard>
            </PressScale>
          </FadeIn>
          <FadeIn delay={60}>
            <View style={styles.actions}>
              <ActionTile label="Scan" icon="scan-outline" onPress={() => router.push("/customer/scan")} />
              <ActionTile label="Activity" icon="time-outline" onPress={() => router.push("/customer/history")} />
              <ActionTile label="Profile" icon="person-outline" onPress={() => router.push("/customer/profile")} />
              {canSwitch ? (
                <ActionTile
                  label="Till"
                  icon="storefront-outline"
                  onPress={() => {
                    setMode("merchant");
                    router.replace("/merchant");
                  }}
                />
              ) : null}
            </View>
          </FadeIn>
          <FadeIn delay={110}>
            <SectionHeader title="Recent activity" action="See all" onAction={() => router.push("/customer/history")} />
            <View style={[styles.list, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              {recent.length === 0 ? (
                <View style={styles.emptyRecent}>
                  <Text style={{ color: theme.text, fontWeight: "700" }}>No payments yet</Text>
                  <Text style={{ color: theme.subtle, fontSize: 12, textAlign: "center" }}>
                    Scan a merchant QR to make your first payment.
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
                      onPress={() => router.push(`/customer/payment/${payment.reference}`)}
                    />
                  </View>
                ))
              )}
            </View>
          </FadeIn>
          <FadeIn delay={160}>
            <View style={[styles.tip, { backgroundColor: theme.surfaceRaised, borderColor: theme.border }]}>
              <IconWell background={theme.scheme === "dark" ? "#1e3a8a" : "#dbeafe"} size={36}>
                <Text style={{ color: theme.primary, fontWeight: "800" }}>→</Text>
              </IconWell>
              <Text style={{ color: theme.muted, fontSize: 12, flex: 1, lineHeight: 18 }}>
                Point your camera at a POMPO code. We verify the merchant before you pay.
              </Text>
            </View>
          </FadeIn>
        </ScrollView>
      </View>
      <BottomNav active="home" />
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
  heroTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  heroKicker: { color: "rgba(255,255,255,0.72)", fontSize: 11, fontWeight: "800", letterSpacing: 1.6 },
  heroBadge: {
    backgroundColor: "rgba(255,255,255,0.16)",
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  heroBadgeText: { color: "#ffffff", fontSize: 11, fontWeight: "700" },
  heroTitle: { color: "#ffffff", fontSize: 28, fontWeight: "800", letterSpacing: -0.6 },
  heroHint: { color: "rgba(255,255,255,0.82)", fontSize: 12, fontWeight: "700", marginTop: 6, letterSpacing: 0.8 },
  actions: { flexDirection: "row", gap: 8 },
  list: { borderRadius: 20, borderWidth: 1, overflow: "hidden" },
  emptyRecent: { paddingVertical: 28, paddingHorizontal: 16, alignItems: "center", gap: 6 },
  tip: { flexDirection: "row", alignItems: "center", gap: 12, borderRadius: 18, borderWidth: 1, padding: 14 },
});
