import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider } from "@/state/AuthProvider";
import { CheckoutProvider } from "@/state/CheckoutProvider";
import { ModeProvider } from "@/state/ModeProvider";

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <AuthProvider>
          <ModeProvider>
            <CheckoutProvider>
              <StatusBar style="auto" />
              <Stack screenOptions={{ headerShown: false, animation: "fade" }} />
            </CheckoutProvider>
          </ModeProvider>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
