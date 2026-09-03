import { Redirect, Stack } from "expo-router";
import { StyleSheet } from "react-native";

import { AppShell } from "@/components/AppShell";
import { canUseMerchantMode } from "@/domain/roles";
import { useAuth } from "@/state/AuthProvider";
import { useTheme } from "@/theme";

export default function MerchantLayout() {
  const theme = useTheme();
  const { hydrated, user } = useAuth();
  if (hydrated && !user) {
    return <Redirect href="/login" />;
  }
  if (user && !canUseMerchantMode(user.role_code, user.merchant_id)) {
    return <Redirect href="/customer" />;
  }
  return (
    <AppShell>
      <Stack
        screenOptions={{
          headerShown: false,
          animation: "slide_from_right",
          contentStyle: [styles.stackContent, { backgroundColor: theme.background }],
        }}
      />
    </AppShell>
  );
}

const styles = StyleSheet.create({
  stackContent: { flex: 1 },
});
