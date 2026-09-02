import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { FadeIn, GlassSurface, PressScale } from "@/components/glass";
import { BottomNav, ModeSwitch } from "@/components/nav";
import { Muted, Screen, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";

export default function CustomerHome() {
  const theme = useTheme();
  const { user } = useAuth();
  const router = useRouter();
  const firstName = user?.full_name.split(" ")[0] ?? "there";

  return (
    <Screen padded={false}>
      <View style={styles.body}>
        <ModeSwitch />
        <FadeIn>
          <Text style={[styles.kicker, { color: theme.subtle }]}>POMPO</Text>
          <Title>Hi {firstName}</Title>
          <Muted>Scan a merchant QR, check the details, then pay.</Muted>
        </FadeIn>
        <FadeIn delay={40}>
          <PressScale
            accessibilityRole="button"
            accessibilityLabel="Scan QR"
            onPress={() => router.push("/customer/scan")}
          >
            <View style={[styles.hero, { backgroundColor: theme.primary, shadowColor: theme.primary }]}>
              <Text style={[styles.heroLabel, { color: theme.primaryForeground }]}>Scan & pay</Text>
              <Text style={[styles.heroHint, { color: theme.primaryForeground }]}>
                OPEN → SCAN → VERIFY → PAY
              </Text>
            </View>
          </PressScale>
        </FadeIn>
        <View style={styles.row}>
          <PressScale style={styles.shortcut} onPress={() => router.push("/customer/history")}>
            <GlassSurface style={styles.shortcutInner}>
              <Text style={[styles.shortcutTitle, { color: theme.text }]}>Activity</Text>
              <Text style={{ color: theme.subtle, fontSize: 13 }}>Payment history</Text>
            </GlassSurface>
          </PressScale>
          <PressScale style={styles.shortcut} onPress={() => router.push("/customer/profile")}>
            <GlassSurface style={styles.shortcutInner}>
              <Text style={[styles.shortcutTitle, { color: theme.text }]}>Profile</Text>
              <Text style={{ color: theme.subtle, fontSize: 13 }}>Account & mode</Text>
            </GlassSurface>
          </PressScale>
        </View>
      </View>
      <BottomNav active="home" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  body: { flex: 1, paddingHorizontal: 20, paddingTop: 12, gap: 16 },
  kicker: { fontSize: 12, fontWeight: "800", letterSpacing: 2, marginBottom: 4 },
  hero: {
    borderRadius: 28,
    paddingVertical: 22,
    paddingHorizontal: 20,
    gap: 6,
    shadowOffset: { width: 0, height: 14 },
    shadowOpacity: 0.28,
    shadowRadius: 20,
    elevation: 6,
  },
  heroLabel: { fontSize: 22, fontWeight: "800" },
  heroHint: { fontSize: 12, fontWeight: "600", opacity: 0.86, letterSpacing: 0.6 },
  row: { flexDirection: "row", gap: 12 },
  shortcut: { flex: 1 },
  shortcutInner: { minHeight: 96, justifyContent: "flex-end", gap: 4 },
  shortcutTitle: { fontSize: 16, fontWeight: "700" },
});
