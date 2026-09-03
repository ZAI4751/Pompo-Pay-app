import { useRouter } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";

import { BottomNav } from "@/components/nav";
import { Card, ErrorBanner, GlassInput, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";

export default function SecurityScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api, logout } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8, gap: 12 }}>
        <Title>Account security</Title>
        {error ? <ErrorBanner message={error} /> : null}
        {done ? <Text style={{ color: theme.success }}>{done}</Text> : null}
        <Card>
          <Text style={{ color: theme.text, fontWeight: "700" }}>Change password</Text>
          <GlassInput secureTextEntry placeholder="Current password" value={current} onChangeText={setCurrent} />
          <GlassInput secureTextEntry placeholder="New password" value={next} onChangeText={setNext} />
          <PrimaryButton
            label="Update password"
            onPress={async () => {
              setError(null);
              const result = await api.changePassword(current, next);
              if (!result.ok) {
                setError(result.error.message);
                return;
              }
              setDone("Password updated.");
              setCurrent("");
              setNext("");
            }}
          />
        </Card>
        <SecondaryButton
          label="Log out all sessions"
          onPress={async () => {
            await api.logoutAll();
            await logout();
            router.replace("/login");
          }}
        />
      </View>
      <BottomNav active="profile" />
    </Screen>
  );
}
