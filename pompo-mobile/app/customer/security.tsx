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
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8, gap: 12 }}>
        <Title>Account security</Title>
        <Text style={{ color: theme.muted }}>
          Changing your password signs out every other device. Never share your password, PIN, or card numbers with POMPO.
        </Text>
        {error ? <ErrorBanner message={error} /> : null}
        {done ? <Text style={{ color: theme.success }}>{done}</Text> : null}
        <Card>
          <Text style={{ color: theme.text, fontWeight: "700" }}>Change password</Text>
          <GlassInput secureTextEntry placeholder="Current password" value={current} onChangeText={setCurrent} />
          <GlassInput secureTextEntry placeholder="New password (8+ characters)" value={next} onChangeText={setNext} />
          <GlassInput secureTextEntry placeholder="Confirm new password" value={confirm} onChangeText={setConfirm} />
          <PrimaryButton
            label="Update password"
            loading={busy}
            onPress={async () => {
              setError(null);
              setDone(null);
              if (next.length < 8) {
                setError("New password must be at least 8 characters.");
                return;
              }
              if (next !== confirm) {
                setError("Confirmation does not match the new password.");
                return;
              }
              setBusy(true);
              const result = await api.changePassword(current, next);
              setBusy(false);
              if (!result.ok) {
                setError(result.error.message);
                return;
              }
              await logout();
              router.replace("/login");
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
