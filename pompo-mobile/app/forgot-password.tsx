import { useRouter } from "expo-router";
import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";

import { Atmosphere, FadeIn, GlassInput, HeroCard } from "@/components/glass";
import { Card, ErrorBanner, PrimaryButton, SecondaryButton, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";

export default function ForgotPasswordScreen() {
  const theme = useTheme();
  const { api } = useAuth();
  const router = useRouter();

  const [mode, setMode] = useState<"request" | "reset">("request");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
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
    const result = await api.forgotPassword(email.trim());
    setLoading(false);
    if (!result.ok) {
      setError(result.error.message);
      return;
    }
    setInfo(
      "If an account exists with this email, password reset instructions have been dispatched. Check your inbox or enter your token below.",
    );
  }

  async function handleReset() {
    setError(null);
    setInfo(null);
    if (!token.trim()) {
      setError("Please enter your password reset token.");
      return;
    }
    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Password confirmation does not match.");
      return;
    }
    setLoading(true);
    const result = await api.resetPassword(token.trim(), newPassword);
    setLoading(false);
    if (!result.ok) {
      setError(result.error.message);
      return;
    }
    setInfo("Password successfully reset! Returning to sign in…");
    setTimeout(() => {
      router.replace("/login");
    }, 1500);
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
            <Text style={styles.heroTitle}>Account Recovery</Text>
            <Text style={styles.heroHint}>Reset your password securely</Text>
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
            <PrimaryButton label="Send reset instructions" loading={loading} onPress={handleRequest} />
            <SecondaryButton
              label="I have a reset token"
              onPress={() => {
                setError(null);
                setMode("reset");
              }}
            />
          </View>
        ) : (
          <View style={{ gap: 12 }}>
            <View style={[styles.fields, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              <GlassInput
                autoCapitalize="none"
                placeholder="Reset token"
                value={token}
                onChangeText={setToken}
                style={styles.field}
              />
              <GlassInput
                secureTextEntry
                placeholder="New password (8+ chars)"
                value={newPassword}
                onChangeText={setNewPassword}
                style={styles.field}
              />
              <GlassInput
                secureTextEntry
                placeholder="Confirm new password"
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                style={styles.field}
              />
            </View>
            <PrimaryButton label="Update password" loading={loading} onPress={handleReset} />
            <SecondaryButton
              label="Request new token"
              onPress={() => {
                setError(null);
                setMode("request");
              }}
            />
          </View>
        )}

        <SecondaryButton label="Back to sign in" onPress={() => router.replace("/login")} />
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
