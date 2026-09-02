import { Pressable, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";

import { useTheme } from "@/components/ui";
import { useAppMode } from "@/state/ModeProvider";

export function ModeSwitch() {
  const theme = useTheme();
  const { mode, canSwitch, setMode } = useAppMode();
  const router = useRouter();
  if (!canSwitch) {
    return null;
  }
  const next = mode === "customer" ? "merchant" : "customer";
  return (
    <Pressable
      onPress={() => {
        setMode(next);
        router.replace(next === "merchant" ? "/merchant" : "/customer");
      }}
      style={({ pressed }) => [
        styles.chip,
        { backgroundColor: theme.surfaceRaised, borderColor: theme.border, opacity: pressed ? 0.8 : 1 },
      ]}
    >
      <Text style={[styles.label, { color: theme.muted }]}>
        {mode === "merchant" ? "Merchant" : "Customer"} · switch
      </Text>
    </Pressable>
  );
}

export function BottomNav({ active }: { active: "home" | "history" | "profile" | "qr" | "activity" }) {
  const theme = useTheme();
  const { mode } = useAppMode();
  const router = useRouter();
  const items =
    mode === "merchant"
      ? [
          { key: "home", label: "Home", href: "/merchant" },
          { key: "qr", label: "QR", href: "/merchant/qr" },
          { key: "activity", label: "Activity", href: "/merchant/activity" },
          { key: "profile", label: "Profile", href: "/merchant/profile" },
        ]
      : [
          { key: "home", label: "Home", href: "/customer" },
          { key: "history", label: "History", href: "/customer/history" },
          { key: "profile", label: "Profile", href: "/customer/profile" },
        ];
  return (
    <View style={[styles.nav, { backgroundColor: theme.surface, borderColor: theme.border }]}>
      {items.map((item) => {
        const isActive = item.key === active;
        return (
          <Pressable key={item.key} onPress={() => router.replace(item.href as never)} style={styles.navItem}>
            <Text style={{ color: isActive ? theme.primary : theme.subtle, fontWeight: isActive ? "700" : "500" }}>
              {item.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  chip: { alignSelf: "flex-start", borderRadius: 999, borderWidth: 1, paddingHorizontal: 12, paddingVertical: 6 },
  label: { fontSize: 13, fontWeight: "600" },
  nav: {
    flexDirection: "row",
    borderTopWidth: 1,
    paddingVertical: 12,
    paddingHorizontal: 8,
    justifyContent: "space-around",
  },
  navItem: { paddingHorizontal: 8, paddingVertical: 4 },
});
