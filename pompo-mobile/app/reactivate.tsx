import { useRouter, type Href } from "expo-router";
import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";

import { Atmosphere, FadeIn, GlassInput, HeroCard } from "@/components/glass";
import { Card, ErrorBanner, PrimaryButton, SecondaryButton, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";

export default function ReactivateScreen() {
  const theme = useTheme();
  const { api, refreshUser } = useAuth();
  const router = useRouter();

  const [mode, setMode] = useState<"request" | "confirm">("request");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleRequest() {
    setError(null);
    setInfo(null);
    if (!email.trim() || !email.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }
    setLoading(true);
    const result = await api.requestAccountReactivation(email.trim());
    setLoading(false);
    if (!result.ok) {
      setError(result.error.message);
      return;
    }
    setInfo(
      "If a deactivated POMPO account matches that email, reactivation instructions have been sent. Enter the token below to continue.",
    );
    setMode("confirm");
  }

  async function handleConfirm() {
    setError(null);
    setInfo(null);
    if (!token.trim()) {
      setError("Enter the reactivation token from your email.");
      return;
    }
    if (!password) {
      setError("Enter your password to confirm you own this account.");
      return;
    }
    setLoading(true);
    const result = await api.reactivateAccount(token.trim(), password);
    setLoading(false);
    if (!result.ok) {
      setError(result.error.message);
      return;
    }
    await refreshUser();
    router.replace("/customer");
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
            <Text style={styles.brand}>POMPO</Text>
            <Text style={styles.heroTitle}>Your POMPO account is deactivated.</Text>
            <Text style={styles.heroHint}>Reactivate with a fresh verification step.</Text>
          </HeroCard>
        </FadeIn>

        {error ? <ErrorBanner message={error} /> : null}
        {info ? (
          <Card style={{ backgroundColor: theme.scheme === "dark" ? "#064e3b" : "#ecfdf5", borderColor: "#059669" }}>
            <Text style={{ color: theme.scheme === "dark" ? "#a7f3d0" : "#065f46", fontSize: 13, lineHeight: 18 }}>
              {info}
            </Text>
          </Card>
        ) : null}

        {mode === "request" ? (
          <View style={{ gap: 12 }}>
            <View style={[styles.fields, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              <GlassInput
                autoCapitalize="none"
                keyboardType="email-address"
                placeholder="Account email"
                value={email}
                onChangeText={setEmail}
                style={styles.field}
              />
            </View>
            <PrimaryButton label="Request reactivation" loading={loading} onPress={handleRequest} />
            <SecondaryButton
              label="I have a reactivation token"
              onPress={() => {
                setError(null);
                setMode("confirm");
              }}
            />
          </View>
        ) : (
          <View style={{ gap: 12 }}>
            <View style={[styles.fields, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              <GlassInput
                autoCapitalize="none"
                placeholder="Reactivation token"
                value={token}
                onChangeText={setToken}
                style={styles.field}
              />
              <GlassInput
                secureTextEntry
                placeholder="Account password"
                value={password}
                onChangeText={setPassword}
              />
            </View>
            <PrimaryButton label="Reactivate and sign in" loading={loading} onPress={handleConfirm} />
            <SecondaryButton
              label="Request a new token"
              onPress={() => {
                setError(null);
                setMode("request");
              }}
            />
          </View>
        )}

        <SecondaryButton label="Back to sign in" onPress={() => router.replace("/login" as Href)} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  inner: { flexGrow: 1, justifyContent: "center", padding: 24, gap: 14 },
  hero: { minHeight: 120, marginBottom: 8 },
  brand: { color: "rgba(255,255,255,0.72)", fontSize: 12, fontWeight: "800", letterSpacing: 2 },
  heroTitle: { color: "#ffffff", fontSize: 24, fontWeight: "800" },
  heroHint: { color: "rgba(255,255,255,0.8)", fontSize: 13, fontWeight: "600", marginTop: 4 },
  fields: { borderWidth: 1, borderRadius: 20, padding: 12, gap: 10 },
  field: { marginBottom: 0 },
});
