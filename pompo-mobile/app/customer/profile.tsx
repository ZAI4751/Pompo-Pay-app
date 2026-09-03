import { useRouter, type Href } from "expo-router";
import { useEffect, useState } from "react";
import { ScrollView, Text, View } from "react-native";

import { MenuRow } from "@/components/activity";
import { FadeIn, InitialsAvatar } from "@/components/glass";
import { ModeSwitch } from "@/components/nav";
import { Card, Screen, useTheme } from "@/components/ui";
import { roleLabel } from "@/format";
import { useAuth } from "@/state/AuthProvider";
import { useAppMode } from "@/state/ModeProvider";
import type { MerchantAccessResponse } from "@/types";

export default function CustomerProfile() {
  const theme = useTheme();
  const { user, api, logout } = useAuth();
  const { setMode } = useAppMode();
  const router = useRouter();
  const [access, setAccess] = useState<MerchantAccessResponse | null>(null);

  useEffect(() => {
    void api.getMerchantAccess().then((res) => {
      if (res.ok) {
        setAccess(res.data);
      }
    });
  }, [api]);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8 }}>
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
          <Text style={{ color: theme.text, fontSize: 22, fontWeight: "800" }}>Account Control Centre</Text>
          <ModeSwitch />
        </View>

        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ gap: 14, paddingBottom: 24 }}>
          {/* Identity & Account Center */}
          <FadeIn>
            <View style={{ alignItems: "center", paddingTop: 4, gap: 6 }}>
              <InitialsAvatar name={user?.full_name ?? "POMPO"} size={72} active />
              <Text style={{ color: theme.text, fontSize: 18, fontWeight: "800" }}>{user?.full_name}</Text>
              <Text style={{ color: theme.subtle, fontSize: 13 }}>{user?.email}</Text>
              <View style={{ flexDirection: "row", gap: 6, alignItems: "center" }}>
                <Text style={{ color: theme.primary, fontSize: 12, fontWeight: "700" }}>
                  {roleLabel(user?.role_code ?? "customer")}
                </Text>
                <Text style={{ color: theme.subtle, fontSize: 12 }}>•</Text>
                <Text
                  style={{
                    color: user?.is_email_verified ? theme.success : "#f59e0b",
                    fontSize: 12,
                    fontWeight: "600",
                  }}
                >
                  {user?.is_email_verified ? "Verified ✓" : "Unverified"}
                </Text>
              </View>
            </View>
          </FadeIn>

          {/* Real Customer Information */}
          <Card style={{ gap: 8 }}>
            <Text style={{ color: theme.subtle, fontSize: 11, fontWeight: "800", letterSpacing: 0.5 }}>
              CUSTOMER IDENTIFIERS
            </Text>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <Text style={{ color: theme.muted, fontSize: 13 }}>Customer ID</Text>
              <Text style={{ color: theme.text, fontSize: 13, fontWeight: "600" }}>
                {user?.id ? user.id.slice(0, 8).toUpperCase() : "—"}
              </Text>
            </View>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <Text style={{ color: theme.muted, fontSize: 13 }}>Email</Text>
              <Text style={{ color: theme.text, fontSize: 13, fontWeight: "600" }}>{user?.email ?? "—"}</Text>
            </View>
            {user?.phone ? (
              <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                <Text style={{ color: theme.muted, fontSize: 13 }}>Phone</Text>
                <Text style={{ color: theme.text, fontSize: 13, fontWeight: "600" }}>{user.phone}</Text>
              </View>
            ) : null}
          </Card>

          {/* Merchant Mode Authorized Capability Access */}
          {access?.allowed ? (
            <Card style={{ borderColor: "#059669", backgroundColor: theme.scheme === "dark" ? "#064e3b22" : "#ecfdf566" }}>
              <Text style={{ color: "#059669", fontSize: 11, fontWeight: "800", letterSpacing: 0.5 }}>
                MERCHANT CAPABILITY
              </Text>
              <Text style={{ color: theme.text, fontSize: 16, fontWeight: "800", marginTop: 2 }}>
                {access.merchant?.name ?? "Authorized Merchant"}
              </Text>
              <Text style={{ color: theme.muted, fontSize: 12 }}>
                Branches: {access.branches.length} · Tills: {access.tills.length}
              </Text>
              <MenuRow
                icon="storefront-outline"
                label="Enter Merchant Mode"
                color="#047857"
                background={theme.scheme === "dark" ? "#052e1c" : "#ecfdf5"}
                onPress={() => {
                  setMode("merchant");
                  router.replace("/merchant");
                }}
                last
              />
            </Card>
          ) : (
            <Card style={{ borderColor: theme.border }}>
              <Text style={{ color: theme.subtle, fontSize: 11, fontWeight: "800", letterSpacing: 0.5 }}>
                BUSINESS OPERATING CONTEXT
              </Text>
              <Text style={{ color: theme.text, fontWeight: "700", marginTop: 2 }}>Customer Account</Text>
              <Text style={{ color: theme.muted, fontSize: 12, lineHeight: 18 }}>
                This account is not provisioned for merchant till operation or QR generation. Contact your organization administrator for merchant assignment.
              </Text>
            </Card>
          )}

          {/* Account Services & Tools */}
          <Card style={{ padding: 0, gap: 0, overflow: "hidden" }}>
            <MenuRow
              icon="card-outline"
              label="Payment methods"
              color={theme.primary}
              background={theme.scheme === "dark" ? "#1e3a8a" : "#eff6ff"}
              onPress={() => router.push("/customer/methods" as Href)}
            />
            <MenuRow
              icon="send-outline"
              label="Payment requests"
              color={theme.primary}
              background={theme.scheme === "dark" ? "#1e3a8a" : "#eff6ff"}
              onPress={() => router.push("/customer/requests/index")}
            />
            <MenuRow
              icon="storefront-outline"
              label="Merchants"
              color={theme.primary}
              background={theme.scheme === "dark" ? "#1e3a8a" : "#eff6ff"}
              onPress={() => router.push("/customer/merchants")}
            />
            <MenuRow
              icon="notifications-outline"
              label="Notifications"
              color={theme.primary}
              background={theme.scheme === "dark" ? "#1e3a8a" : "#eff6ff"}
              onPress={() => router.push("/customer/notifications")}
            />
            <MenuRow
              icon="options-outline"
              label="Notification settings"
              color={theme.primary}
              background={theme.scheme === "dark" ? "#1e3a8a" : "#eff6ff"}
              onPress={() => router.push("/customer/preferences" as Href)}
            />
            <MenuRow
              icon="lock-closed-outline"
              label="Account security"
              color={theme.primary}
              background={theme.scheme === "dark" ? "#1e3a8a" : "#eff6ff"}
              onPress={() => router.push("/customer/security")}
            />
            <MenuRow
              icon="help-circle-outline"
              label="Customer support"
              color={theme.primary}
              background={theme.scheme === "dark" ? "#1e3a8a" : "#eff6ff"}
              onPress={() => router.push("/customer/support")}
              last
            />
          </Card>

          {/* Sign Out */}
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
        </ScrollView>
      </View>
    </Screen>
  );
}
