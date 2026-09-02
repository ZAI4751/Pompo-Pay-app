import { Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { KeyboardAvoidingView, Platform, StyleSheet, Text, View } from "react-native";

import { Atmosphere, FadeIn, GlassInput, GlassSurface } from "@/components/glass";
import { ErrorBanner, PrimaryButton, Title, useTheme } from "@/components/ui";
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
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <Atmosphere />
      <View style={styles.inner}>
        <FadeIn>
          <Text style={[styles.brand, { color: theme.darkBlue }]}>POMPO</Text>
          <Title>Sign in</Title>
          <Text style={{ color: theme.muted, marginBottom: 20 }}>
            Pay merchants or run your till — one app, two modes.
          </Text>
        </FadeIn>
        {error ? <ErrorBanner message={error} /> : null}
        <GlassSurface>
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
            style={styles.field}
          />
        </GlassSurface>
        <PrimaryButton
          label="Continue"
          loading={loading}
          onPress={async () => {
            setError(null);
            setLoading(true);
            const result = await login(email, password);
            setLoading(false);
            if (!result.ok) {
              setError(result.message);
              return;
            }
            router.replace("/");
          }}
        />
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  inner: { flex: 1, justifyContent: "center", padding: 24, gap: 12 },
  brand: { fontSize: 14, fontWeight: "800", letterSpacing: 3, marginBottom: 8 },
  field: { marginBottom: 10 },
});
