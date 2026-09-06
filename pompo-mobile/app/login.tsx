import { Redirect, useRouter, type Href } from "expo-router";
import { useState } from "react";
import { Image, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";

import { Atmosphere, FadeIn, GlassInput, HeroCard } from "@/components/glass";
import { ErrorBanner, PrimaryButton, SecondaryButton, useTheme } from "@/components/ui";
import { defaultMode } from "@/domain/roles";
import { useAuth } from "@/state/AuthProvider";

export default function LoginScreen() {
  const theme = useTheme();
  const { user, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (user) {
    return <Redirect href={defaultMode(user.role_code) === "merchant" ? "/merchant" : "/customer"} />;
  }

  return (
    <KeyboardAvoidingView
      style={[styles.flex, { backgroundColor: theme.background }]}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <Atmosphere />
      <ScrollView
        contentContainerStyle={styles.inner}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
      >
        <FadeIn>
          <HeroCard style={styles.hero}>
            <Image source={require("../assets/icon.png")} style={styles.brandMark} resizeMode="contain" />
            <Text style={styles.brand}>POMPO</Text>
            <View>
              <Text style={styles.heroTitle}>Pay in a scan.</Text>
              <Text style={styles.heroHint}>Merchants and customers, one app.</Text>
            </View>
          </HeroCard>
        </FadeIn>
        <FadeIn delay={80}>
          <Text style={[styles.title, { color: theme.text }]}>Sign in</Text>
          <Text style={{ color: theme.muted, marginBottom: 8 }}>
            Use your POMPO account. Nothing is stored in this screen.
          </Text>
        </FadeIn>
        {error ? <ErrorBanner message={error} /> : null}
        <View style={[styles.fields, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <GlassInput
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            placeholder="Email"
            value={email}
            onChangeText={setEmail}
            style={styles.field}
          />
          <GlassInput
            secureTextEntry
            autoComplete="password"
            placeholder="Password"
            value={password}
            onChangeText={setPassword}
          />
        </View>
        <PrimaryButton
          label="Continue"
          loading={loading}
          onPress={async () => {
            setError(null);
            setLoading(true);
            const result = await login(email, password);
            setLoading(false);
            if (!result.ok) {
              if (result.code === "account_deactivated") {
                router.push("/reactivate" as Href);
                setError("Your POMPO account is deactivated.");
                return;
              }
              setError(result.message);
              return;
            }
            router.replace("/");
          }}
        />
            <SecondaryButton label="Forgot password?" onPress={() => router.push("/forgot-password" as Href)} />
        <SecondaryButton label="Create a customer account" onPress={() => router.push("/register")} />
            <View style={styles.businessEntry}>
              <Text style={{ color: theme.muted, textAlign: "center" }}>Are you a business?</Text>
              <SecondaryButton
                label="Register as a Merchant"
                onPress={() => router.push("/merchant-onboarding" as Href)}
              />
            </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  inner: { flexGrow: 1, justifyContent: "center", padding: 24, gap: 14 },
  hero: { minHeight: 140, marginBottom: 8 },
  brandMark: { width: 44, height: 44, marginBottom: 8 },
  brand: { color: "rgba(255,255,255,0.72)", fontSize: 12, fontWeight: "800", letterSpacing: 2 },
  heroTitle: { color: "#ffffff", fontSize: 26, fontWeight: "800", letterSpacing: -0.5 },
  heroHint: { color: "rgba(255,255,255,0.8)", fontSize: 13, fontWeight: "600", marginTop: 4 },
  title: { fontSize: 22, fontWeight: "800" },
  fields: { borderWidth: 1, borderRadius: 20, padding: 12, gap: 10 },
  field: { marginBottom: 0 },
  businessEntry: { marginTop: 4, gap: 2 },
});
