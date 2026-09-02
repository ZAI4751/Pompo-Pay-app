import { useRouter } from "expo-router";
import { Text, View } from "react-native";

import { BottomNav, ModeSwitch } from "@/components/nav";
import { Card, PrimaryButton, Screen, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";

export default function MerchantProfile() {
  const theme = useTheme();
  const { user, logout } = useAuth();
  const router = useRouter();

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 12, gap: 14 }}>
        <ModeSwitch />
        <Title>Merchant profile</Title>
        <Card>
          <Text style={{ color: theme.text, fontSize: 18, fontWeight: "700" }}>{user?.full_name}</Text>
          <Text style={{ color: theme.muted }}>{user?.email}</Text>
          <Text style={{ color: theme.subtle }}>{user?.role_code}</Text>
        </Card>
        <PrimaryButton
          label="Sign out"
          onPress={async () => {
            await logout();
            router.replace("/login");
          }}
        />
      </View>
      <BottomNav active="profile" />
    </Screen>
  );
}
