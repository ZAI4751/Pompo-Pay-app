import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { BottomNav, ModeSwitch } from "@/components/nav";
import { Card, Muted, PrimaryButton, Screen, Title, useTheme } from "@/components/ui";
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
        <Title>Hi {firstName}</Title>
        <Muted>Scan a merchant QR, check the details, then pay.</Muted>
        <Card>
          <Text style={[styles.step, { color: theme.subtle }]}>1 · SCAN</Text>
          <Text style={[styles.step, { color: theme.subtle }]}>2 · VERIFY</Text>
          <Text style={[styles.step, { color: theme.text }]}>3 · PAY</Text>
        </Card>
        <PrimaryButton label="Scan QR" onPress={() => router.push("/customer/scan")} />
      </View>
      <BottomNav active="home" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  body: { flex: 1, paddingHorizontal: 20, paddingTop: 12, gap: 14 },
  step: { fontSize: 20, fontWeight: "800", letterSpacing: 1 },
});
