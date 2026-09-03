import { Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";

import { Atmosphere, FadeIn, GlassInput, HeroCard } from "@/components/glass";
import { ErrorBanner, PrimaryButton, SecondaryButton, useTheme } from "@/components/ui";
import { defaultMode } from "@/domain/roles";
import { useAuth } from "@/state/AuthProvider";

export default function RegisterScreen() {
  const theme = useTheme();
  const { user, register } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
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
            <Text style={styles.brand}>POMPO</Text>
            <Text style={styles.heroTitle}>Create your account</Text>
            <Text style={styles.heroHint}>Pay merchants. POMPO does not hold your money.</Text>
          </HeroCard>
        </FadeIn>
        {error ? <ErrorBanner message={error} /> : null}
        <View style={[styles.fields, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <GlassInput placeholder="Full name" value={fullName} onChangeText={setFullName} style={styles.field} />
          <GlassInput
            autoCapitalize="none"
            keyboardType="email-address"
            placeholder="Email"
            value={email}
            onChangeText={setEmail}
            style={styles.field}
          />
          <GlassInput
            autoCapitalize="none"
            keyboardType="phone-pad"
            placeholder="Phone (optional)"
            value={phone}
            onChangeText={setPhone}
            style={styles.field}
          />
          <GlassInput secureTextEntry placeholder="Password (8+ characters)" value={password} onChangeText={setPassword} />
        </View>
        <Text style={{ color: theme.subtle, fontSize: 12 }}>
          Phone SMS verification is not configured yet. Email is your sign-in identity.
        </Text>
        <PrimaryButton
          label="Create account"
          loading={loading}
          onPress={async () => {
            setError(null);
            setLoading(true);
            const result = await register({
              email: email.trim(),
              password,
              full_name: fullName.trim(),
              phone: phone.trim() || undefined,
            });
            setLoading(false);
            if (!result.ok) {
              setError(result.message);
              return;
            }
            router.replace("/");
          }}
        />
        <SecondaryButton label="I already have an account" onPress={() => router.replace("/login")} />
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
