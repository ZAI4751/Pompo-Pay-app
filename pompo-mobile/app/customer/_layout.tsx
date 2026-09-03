import { Redirect, Stack } from "expo-router";
import { StyleSheet } from "react-native";

import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/state/AuthProvider";

export default function CustomerLayout() {
  const { hydrated, user } = useAuth();
  if (hydrated && !user) {
    return <Redirect href="/login" />;
  }
  return (
    <AppShell>
      <Stack
        screenOptions={{
          headerShown: false,
          animation: "slide_from_right",
          contentStyle: styles.stackContent,
        }}
      />
    </AppShell>
  );
}

const styles = StyleSheet.create({
  stackContent: { flex: 1, backgroundColor: "transparent" },
});
