import { Redirect } from "expo-router";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { defaultMode } from "@/domain/roles";
import { useAuth } from "@/state/AuthProvider";
import { useAppMode } from "@/state/ModeProvider";
import { palette } from "@/theme";

export default function SplashScreen() {
  const { hydrated, user } = useAuth();
  const { mode } = useAppMode();

  if (!hydrated) {
    return (
      <View style={styles.splash} accessibilityLabel="Loading POMPO">
        <Text style={styles.brand}>POMPO</Text>
        <Text style={styles.tag}>Scan · Verify · Pay</Text>
        <ActivityIndicator color="#93c5fd" style={styles.spinner} />
      </View>
    );
  }

  if (!user) {
    return <Redirect href="/login" />;
  }

  const target = (mode || defaultMode(user.role_code)) === "merchant" ? "/merchant" : "/customer";
  return <Redirect href={target} />;
}

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    backgroundColor: palette.darkBlue,
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  brand: { color: "#ffffff", fontSize: 36, fontWeight: "800", letterSpacing: 2 },
  tag: { color: "#93c5fd", fontSize: 16, fontWeight: "500" },
  spinner: { marginTop: 24 },
});
