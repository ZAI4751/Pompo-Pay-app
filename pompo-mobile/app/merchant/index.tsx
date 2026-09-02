import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Text, View } from "react-native";

import { FadeIn, PressScale } from "@/components/glass";
import { BottomNav, ModeSwitch } from "@/components/nav";
import { Card, ErrorBanner, Muted, PrimaryButton, Screen, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import type { Merchant } from "@/types";

export default function MerchantHome() {
  const theme = useTheme();
  const { user, api } = useAuth();
  const router = useRouter();
  const [merchant, setMerchant] = useState<Merchant | null>(null);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);

  useEffect(() => {
    if (!user?.merchant_id) {
      return;
    }
    void api.getMerchant(user.merchant_id).then((result) => {
      if (result.ok) {
        setMerchant(result.data);
      } else if (result.error.kind !== "forbidden") {
        setError({ message: result.error.message, requestId: result.error.requestId });
      }
    });
  }, [api, user?.merchant_id]);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 12, gap: 14 }}>
        <ModeSwitch />
        <FadeIn>
          <Title>Till</Title>
          <Muted>Generate a QR, then watch payments land.</Muted>
        </FadeIn>
        {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
        <Card>
          <Text style={{ color: theme.subtle }}>Business</Text>
          <Text style={{ color: theme.text, fontSize: 22, fontWeight: "800" }}>
            {merchant?.name ?? "Your merchant"}
          </Text>
          <Text style={{ color: theme.muted }}>{user?.full_name}</Text>
        </Card>
        <PressScale onPress={() => router.push("/merchant/qr")}>
          <View style={{ backgroundColor: theme.primary, borderRadius: 24, padding: 20 }}>
            <Text style={{ color: theme.primaryForeground, fontSize: 18, fontWeight: "800" }}>Show QR</Text>
            <Text style={{ color: theme.primaryForeground, opacity: 0.86, marginTop: 4 }}>
              Display a code for customers to scan
            </Text>
          </View>
        </PressScale>
        <PrimaryButton label="Payment activity" onPress={() => router.push("/merchant/activity")} />
      </View>
      <BottomNav active="home" />
    </Screen>
  );
}
