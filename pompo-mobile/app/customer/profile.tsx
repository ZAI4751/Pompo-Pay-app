import { useRouter } from "expo-router";
import { Text, View } from "react-native";

import { MenuRow } from "@/components/activity";
import { FadeIn, InitialsAvatar } from "@/components/glass";
import { BottomNav, ModeSwitch } from "@/components/nav";
import { Card, Screen, useTheme } from "@/components/ui";
import { roleLabel } from "@/format";
import { useAuth } from "@/state/AuthProvider";
import { useAppMode } from "@/state/ModeProvider";

export default function CustomerProfile() {
  const theme = useTheme();
  const { user, logout } = useAuth();
  const { canSwitch, setMode } = useAppMode();
  const router = useRouter();

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8, gap: 16 }}>
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
          <Text style={{ color: theme.text, fontSize: 22, fontWeight: "800" }}>Profile</Text>
          <ModeSwitch />
        </View>
        <FadeIn>
          <View style={{ alignItems: "center", paddingTop: 8, gap: 8 }}>
            <InitialsAvatar name={user?.full_name ?? "POMPO"} size={80} active />
            <Text style={{ color: theme.text, fontSize: 18, fontWeight: "800" }}>{user?.full_name}</Text>
            <Text style={{ color: theme.subtle, fontSize: 13 }}>{user?.email}</Text>
            <Text style={{ color: theme.primary, fontSize: 12, fontWeight: "700" }}>
              {roleLabel(user?.role_code ?? "customer")}
            </Text>
          </View>
        </FadeIn>
        <Card style={{ padding: 0, gap: 0, overflow: "hidden" }}>
          <MenuRow
            icon="person-circle-outline"
            label="Account"
            color={theme.primary}
            background={theme.scheme === "dark" ? "#1e3a8a" : "#eff6ff"}
            trailing={<Text style={{ color: theme.subtle, fontSize: 12 }}>{user?.email}</Text>}
            last={!canSwitch}
          />
          {canSwitch ? (
            <MenuRow
              icon="storefront-outline"
              label="Switch to merchant"
              color="#047857"
              background={theme.scheme === "dark" ? "#052e1c" : "#ecfdf5"}
              onPress={() => {
                setMode("merchant");
                router.replace("/merchant");
              }}
              last
            />
          ) : null}
        </Card>
        <View
          style={{
            borderRadius: 20,
            overflow: "hidden",
            backgroundColor: theme.errorBg,
            borderWidth: 1,
            borderColor: theme.scheme === "dark" ? "#7f1d1d" : "#fecaca",
          }}
        >
          <MenuRow
            icon="log-out-outline"
            label="Log out"
            color={theme.error}
            background={theme.errorBg}
            last
            onPress={async () => {
              await logout();
              router.replace("/login");
            }}
          />
        </View>
        <Text style={{ textAlign: "center", color: theme.subtle, fontSize: 12 }}>POMPO 1.0.0</Text>
      </View>
      <BottomNav active="profile" />
    </Screen>
  );
}
