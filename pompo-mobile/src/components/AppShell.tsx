import { type ReactNode, useEffect, useState } from "react";
import { Keyboard, Platform, StyleSheet, View } from "react-native";
import { usePathname } from "expo-router";
import * as SystemUI from "expo-system-ui";

import { BottomNav } from "@/components/nav";
import { shouldShowBottomNav } from "@/domain/appShell";
import { useTheme } from "@/theme";

/**
 * Persistent application shell: screen stacks animate inside the content
 * region while the bottom navigation stays mounted and visually anchored.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const theme = useTheme();
  const pathname = usePathname();
  const showNav = shouldShowBottomNav(pathname);
  const [keyboardHeight, setKeyboardHeight] = useState(0);

  useEffect(() => {
    void SystemUI.setBackgroundColorAsync(theme.background);
  }, [theme.background]);

  useEffect(() => {
    const showEvent = Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const hideEvent = Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide";
    const shown = Keyboard.addListener(showEvent, (event) => {
      setKeyboardHeight(event.endCoordinates.height);
    });
    const hidden = Keyboard.addListener(hideEvent, () => {
      setKeyboardHeight(0);
    });
    return () => {
      shown.remove();
      hidden.remove();
    };
  }, []);

  return (
    <View style={[styles.shell, { backgroundColor: theme.background }]} testID="pompo-app-shell">
      <View style={[styles.content, { backgroundColor: theme.background }]} testID="pompo-app-shell-content">
        {children}
      </View>
      <View
        testID="pompo-persistent-bottom-nav"
        pointerEvents={showNav ? "auto" : "none"}
        style={[
          styles.navSlot,
          { backgroundColor: theme.background },
          !showNav && styles.navHidden,
          showNav && Platform.OS === "android" && keyboardHeight > 0
            ? { marginBottom: -keyboardHeight }
            : null,
        ]}
      >
        <BottomNav />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  shell: { flex: 1 },
  content: { flex: 1 },
  navSlot: { zIndex: 20, elevation: 20 },
  navHidden: { height: 0, overflow: "hidden", marginBottom: 0 },
});
