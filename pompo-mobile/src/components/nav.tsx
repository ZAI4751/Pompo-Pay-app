import { Pressable, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { GlassPill, PressScale } from "@/components/glass";
import { useTheme } from "@/theme";
import { useAppMode } from "@/state/ModeProvider";

export function ModeSwitch() {
  const { mode, canSwitch, setMode } = useAppMode();
  const router = useRouter();
  if (!canSwitch) {
    return null;
  }
  const next = mode === "customer" ? "merchant" : "customer";
  return (
    <GlassPill
      accessibilityLabel="Switch app mode"
      onPress={() => {
        setMode(next);
        router.replace(next === "merchant" ? "/merchant" : "/customer");
      }}
    >
    {`${mode === "merchant" ? "Merchant" : "Customer"} · switch`}
    </GlassPill>
  );
}

export function BottomNav({ active }: { active: "home" | "history" | "profile" | "qr" | "activity" }) {
  const theme = useTheme();
  const { mode } = useAppMode();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const isMerchant = mode === "merchant";
  const items = isMerchant
    ? [
        { key: "home", label: "Home", href: "/merchant" },
        { key: "activity", label: "Activity", href: "/merchant/activity" },
        { key: "profile", label: "Profile", href: "/merchant/profile" },
      ]
    : [
        { key: "home", label: "Home", href: "/customer" },
        { key: "history", label: "Activity", href: "/customer/history" },
        { key: "profile", label: "Profile", href: "/customer/profile" },
      ];
  const fabHref = isMerchant ? "/merchant/qr" : "/customer/scan";
  const fabLabel = isMerchant ? "QR" : "Scan";

  return (
    <View style={[styles.wrap, { paddingBottom: Math.max(insets.bottom, 10) }]}>
      <View
        style={[
          styles.nav,
          {
            backgroundColor: theme.glassFill,
            borderColor: theme.glassBorder,
            shadowColor: theme.shadow,
          },
        ]}
      >
        {items.slice(0, 2).map((item) => (
          <NavItem
            key={item.key}
            label={item.label}
            active={item.key === active}
            onPress={() => router.replace(item.href as never)}
          />
        ))}
        <PressScale
          accessibilityRole="button"
          accessibilityLabel={isMerchant ? "Show QR" : "Scan QR"}
          onPress={() => router.push(fabHref as never)}
          hitSlop={6}
          style={[
            styles.fab,
            {
              backgroundColor: theme.primary,
              shadowColor: theme.primary,
            },
          ]}
        >
          <Text style={[styles.fabMark, { color: theme.primaryForeground }]}>+</Text>
          <Text style={[styles.fabLabel, { color: theme.primaryForeground }]}>{fabLabel}</Text>
        </PressScale>
        <NavItem
          label={items[2].label}
          active={items[2].key === active}
          onPress={() => router.replace(items[2].href as never)}
        />
      </View>
    </View>
  );
}

function NavItem({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={styles.navItem}
      hitSlop={8}
    >
      <Text style={{ color: active ? theme.primary : theme.subtle, fontWeight: active ? "700" : "500", fontSize: 13 }}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: { paddingHorizontal: 16, paddingTop: 8 },
  nav: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderWidth: 1,
    borderRadius: 32,
    paddingHorizontal: 10,
    paddingVertical: 8,
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.16,
    shadowRadius: 20,
    elevation: 8,
  },
  navItem: { minWidth: 64, minHeight: 44, alignItems: "center", justifyContent: "center" },
  fab: {
    width: 64,
    height: 64,
    marginTop: -28,
    borderRadius: 32,
    alignItems: "center",
    justifyContent: "center",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.35,
    shadowRadius: 16,
    elevation: 10,
  },
  fabMark: { fontSize: 18, fontWeight: "800", marginTop: -2 },
  fabLabel: { fontSize: 10, fontWeight: "700", letterSpacing: 0.4 },
});
