import { Ionicons } from "@expo/vector-icons";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { InitialsAvatar, PressScale } from "@/components/glass";
import { useTheme } from "@/theme";
import { useAuth } from "@/state/AuthProvider";
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
    <PressScale
      accessibilityRole="button"
      accessibilityLabel="Switch app mode"
      onPress={() => {
        setMode(next);
        router.replace(next === "merchant" ? "/merchant" : "/customer");
      }}
    >
      <View style={[styles.modeChip, { backgroundColor: theme.scheme === "dark" ? "#1e293b" : "#eff6ff" }]}>
        <Text style={[styles.modeChipText, { color: theme.primary }]}>
          {`${mode === "merchant" ? "Merchant" : "Customer"} · switch`}
        </Text>
      </View>
    </PressScale>
  );
}

export function BottomNav({ active }: { active: "home" | "history" | "profile" | "qr" | "activity" }) {
  const theme = useTheme();
  const { user } = useAuth();
  const { mode } = useAppMode();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const isMerchant = mode === "merchant";
  const items = isMerchant
    ? [
        { key: "home", label: "Home", href: "/merchant", icon: "home-outline" as const, iconActive: "home" as const },
        { key: "activity", label: "Activity", href: "/merchant/activity", icon: "time-outline" as const, iconActive: "time" as const },
      ]
    : [
        { key: "home", label: "Home", href: "/customer", icon: "home-outline" as const, iconActive: "home" as const },
        { key: "history", label: "Activity", href: "/customer/history", icon: "time-outline" as const, iconActive: "time" as const },
      ];
  const profileHref = isMerchant ? "/merchant/profile" : "/customer/profile";
  const fabHref = isMerchant ? "/merchant/qr" : "/customer/scan";
  const fabLabel = isMerchant ? "QR" : "Scan";

  return (
    <View style={[styles.wrap, { paddingBottom: Math.max(insets.bottom, 8) }]}>
      <View
        style={[
          styles.nav,
          {
            backgroundColor: theme.navFill,
            borderColor: theme.border,
            shadowColor: theme.shadow,
          },
        ]}
      >
        {items.map((item) => (
          <NavItem
            key={item.key}
            label={item.label}
            icon={item.key === active ? item.iconActive : item.icon}
            active={item.key === active}
            onPress={() => router.replace(item.href as never)}
          />
        ))}
        <PressScale
          accessibilityRole="button"
          accessibilityLabel={isMerchant ? "Show QR" : "Scan QR"}
          onPress={() => router.push(fabHref as never)}
          hitSlop={6}
          style={[styles.fab, { backgroundColor: theme.primary, shadowColor: theme.primary }]}
        >
          <Ionicons name={isMerchant ? "qr-code" : "scan"} size={22} color={theme.primaryForeground} />
          <Text style={[styles.fabLabel, { color: theme.primaryForeground }]}>{fabLabel}</Text>
        </PressScale>
        <Pressable
          accessibilityRole="button"
          accessibilityState={{ selected: active === "profile" }}
          onPress={() => router.replace(profileHref as never)}
          style={styles.navItem}
          hitSlop={8}
        >
          <InitialsAvatar name={user?.full_name ?? "POMPO"} size={28} active={active === "profile"} />
          <Text style={{ color: active === "profile" ? theme.primary : theme.subtle, fontWeight: "700", fontSize: 10 }}>
            Profile
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

function NavItem({
  label,
  icon,
  active,
  onPress,
}: {
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  active: boolean;
  onPress: () => void;
}) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={styles.navItem}
      hitSlop={8}
    >
      <Ionicons name={icon} size={22} color={active ? theme.primary : theme.subtle} />
      <Text style={{ color: active ? theme.primary : theme.subtle, fontWeight: "700", fontSize: 10 }}>{label}</Text>
      <View style={[styles.dot, { backgroundColor: active ? theme.primary : "transparent" }]} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: { paddingHorizontal: 12, paddingTop: 6 },
  nav: {
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "space-between",
    borderWidth: 1,
    borderRadius: 28,
    paddingHorizontal: 8,
    paddingTop: 8,
    paddingBottom: 6,
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 1,
    shadowRadius: 20,
    elevation: 10,
  },
  navItem: { minWidth: 58, minHeight: 48, alignItems: "center", justifyContent: "center", gap: 2 },
  dot: { width: 4, height: 4, borderRadius: 2, marginTop: 1 },
  fab: {
    width: 62,
    height: 62,
    marginTop: -26,
    borderRadius: 31,
    alignItems: "center",
    justifyContent: "center",
    gap: 1,
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.35,
    shadowRadius: 16,
    elevation: 10,
  },
  fabLabel: { fontSize: 10, fontWeight: "800", letterSpacing: 0.3 },
  modeChip: {
    alignSelf: "flex-start",
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  modeChipText: { fontSize: 12, fontWeight: "700" },
});
