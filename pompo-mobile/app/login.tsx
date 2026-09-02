import { Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, View } from "react-native";

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
      <View style={styles.inner}>
        <Text style={[styles.brand, { color: theme.darkBlue }]}>POMPO</Text>
        <Title>Sign in</Title>
        <Text style={{ color: theme.muted, marginBottom: 20 }}>
          Pay merchants or run your till — one app, two modes.
        </Text>
        {error ? <ErrorBanner message={error} /> : null}
        <TextInput
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          placeholder="Email"
          placeholderTextColor={theme.subtle}
          value={email}
          onChangeText={setEmail}
          style={[styles.input, { borderColor: theme.border, color: theme.text, backgroundColor: theme.surface }]}
        />
        <TextInput
          secureTextEntry
          autoComplete="password"
          placeholder="Password"
          placeholderTextColor={theme.subtle}
          value={password}
          onChangeText={setPassword}
          style={[styles.input, { borderColor: theme.border, color: theme.text, backgroundColor: theme.surface }]}
        />
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
  input: { borderWidth: 1, borderRadius: 14, paddingHorizontal: 14, paddingVertical: 14, fontSize: 16 },
});
