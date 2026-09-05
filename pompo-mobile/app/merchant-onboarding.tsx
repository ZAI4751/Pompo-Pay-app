import { useRouter } from "expo-router";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import { Atmosphere, FadeIn, HeroCard } from "@/components/glass";
import { PrimaryButton, SecondaryButton, useTheme } from "@/components/ui";

export default function MerchantOnboardingScreen() {
  const theme = useTheme();
  const router = useRouter();

  return (
    <View style={[styles.flex, { backgroundColor: theme.background }]}>
      <Atmosphere />
      <ScrollView contentContainerStyle={styles.inner}>
        <FadeIn>
          <HeroCard style={styles.hero}>
            <Text style={styles.brand}>POMPO BUSINESS</Text>
            <Text style={styles.title}>Register as a Merchant</Text>
            <Text style={styles.hint}>Accept customer payments with an approved POMPO business account.</Text>
          </HeroCard>
        </FadeIn>
        <View style={[styles.panel, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <Text style={[styles.heading, { color: theme.text }]}>Approval is required</Text>
          <Text style={[styles.body, { color: theme.muted }]}>Merchant access is not created by selecting a signup option.</Text>
          <Text style={[styles.body, { color: theme.muted }]}>POMPO verifies the business, creates the merchant organization, and assigns authorized users, branches, and tills before Merchant Mode becomes available.</Text>
          <Text style={[styles.note, { color: theme.subtle }]}>Creating a customer account will not grant merchant permissions.</Text>
        </View>
        <PrimaryButton label="Back to sign in" onPress={() => router.replace("/login")} />
        <SecondaryButton label="Create a customer account" onPress={() => router.replace("/register")} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  inner: { flexGrow: 1, justifyContent: "center", padding: 24, gap: 14 },
  hero: { minHeight: 170 },
  brand: { color: "rgba(255,255,255,0.72)", fontSize: 12, fontWeight: "800", letterSpacing: 2 },
  title: { color: "#ffffff", fontSize: 24, fontWeight: "800", marginTop: 10 },
  hint: { color: "rgba(255,255,255,0.8)", fontSize: 13, fontWeight: "600", marginTop: 6, lineHeight: 20 },
  panel: { borderWidth: 1, borderRadius: 20, padding: 18, gap: 10 },
  heading: { fontSize: 17, fontWeight: "800" },
  body: { fontSize: 14, lineHeight: 21 },
  note: { fontSize: 12, lineHeight: 18, marginTop: 2 },
});
