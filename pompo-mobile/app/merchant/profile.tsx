import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ScrollView, Text, View } from "react-native";

import { MenuRow } from "@/components/activity";
import { FadeIn, InitialsAvatar } from "@/components/glass";
import { ModeSwitch } from "@/components/nav";
import { Card, formatMoney, Screen, useTheme } from "@/components/ui";
import { roleLabel } from "@/format";
import { useAuth } from "@/state/AuthProvider";
import { useAppMode } from "@/state/ModeProvider";
import type { MerchantAccessResponse } from "@/types";

export default function MerchantProfile() {
  const theme = useTheme();
  const { user, api, logout } = useAuth();
  const { setMode } = useAppMode();
  const router = useRouter();
  const [access, setAccess] = useState<MerchantAccessResponse | null>(null);
  const [settlement, setSettlement] = useState<{
    total_settled_amount: string;
    total_fees: string;
    batch_count: number;
    currency: string;
  } | null>(null);

  useEffect(() => {
    void api.getMerchantAccess().then((res) => {
      if (res.ok) {
        setAccess(res.data);
      }
    });
    void api.getSettlementSummary().then((res) => {
      if (res.ok) {
        setSettlement(res.data);
      }
    });
  }, [api]);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8 }}>
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
          <Text style={{ color: theme.text, fontSize: 22, fontWeight: "800" }}>Merchant Control Centre</Text>
          <ModeSwitch />
        </View>

        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ gap: 14, paddingBottom: 24 }}>
          {/* Identity */}
          <FadeIn>
            <View style={{ alignItems: "center", paddingTop: 4, gap: 6 }}>
              <InitialsAvatar name={user?.full_name ?? "POMPO"} size={72} active />
              <Text style={{ color: theme.text, fontSize: 18, fontWeight: "800" }}>{user?.full_name}</Text>
              <Text style={{ color: theme.subtle, fontSize: 13 }}>{user?.email}</Text>
              <Text style={{ color: theme.primary, fontSize: 12, fontWeight: "700" }}>
                {roleLabel(user?.role_code ?? "merchant_owner")}
              </Text>
            </View>
          </FadeIn>

          {/* Real Backend Organization & Till Context */}
          <Card style={{ gap: 8 }}>
            <Text style={{ color: theme.subtle, fontSize: 11, fontWeight: "800", letterSpacing: 0.5 }}>
              BUSINESS & OPERATING TILL
            </Text>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <Text style={{ color: theme.muted, fontSize: 13 }}>Merchant Name</Text>
              <Text style={{ color: theme.text, fontSize: 13, fontWeight: "600" }}>
                {access?.merchant?.name ?? "—"}
              </Text>
            </View>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <Text style={{ color: theme.muted, fontSize: 13 }}>Merchant ID</Text>
              <Text style={{ color: theme.text, fontSize: 13, fontWeight: "600" }}>
                {access?.merchant?.id ? access.merchant.id.slice(0, 8).toUpperCase() : "—"}
              </Text>
            </View>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <Text style={{ color: theme.muted, fontSize: 13 }}>Assigned Branch</Text>
              <Text style={{ color: theme.text, fontSize: 13, fontWeight: "600" }}>
                {access?.branches.find((b) => b.id === access.operating_branch_id)?.name ??
                  access?.branches[0]?.name ??
                  "—"}
              </Text>
            </View>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <Text style={{ color: theme.muted, fontSize: 13 }}>Assigned Till</Text>
              <Text style={{ color: theme.text, fontSize: 13, fontWeight: "600" }}>
                {access?.tills.find((t) => t.id === access.operating_till_id)?.name ??
                  access?.tills[0]?.name ??
                  "—"}
              </Text>
            </View>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <Text style={{ color: theme.muted, fontSize: 13 }}>QR Generation</Text>
              <Text
                style={{
                  color: access?.can_generate_qr ? theme.success : "#f59e0b",
                  fontSize: 13,
                  fontWeight: "600",
                }}
              >
                {access?.can_generate_qr ? "Authorized ✓" : "Restricted"}
              </Text>
            </View>
          </Card>

          {/* Real Backend Settlement Summary */}
          {settlement ? (
            <Card style={{ gap: 8 }}>
              <Text style={{ color: theme.subtle, fontSize: 11, fontWeight: "800", letterSpacing: 0.5 }}>
                SETTLEMENT OVERVIEW
              </Text>
              <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                <Text style={{ color: theme.muted, fontSize: 13 }}>Total Settled</Text>
                <Text style={{ color: theme.text, fontSize: 13, fontWeight: "700" }}>
                  {formatMoney(settlement.total_settled_amount, settlement.currency)}
                </Text>
              </View>
              <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                <Text style={{ color: theme.muted, fontSize: 13 }}>Total Fees</Text>
                <Text style={{ color: theme.subtle, fontSize: 13 }}>
                  {formatMoney(settlement.total_fees, settlement.currency)}
                </Text>
              </View>
              <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                <Text style={{ color: theme.muted, fontSize: 13 }}>Batches</Text>
                <Text style={{ color: theme.text, fontSize: 13 }}>{settlement.batch_count}</Text>
              </View>
            </Card>
          ) : null}

          {/* Controls & Nav */}
          <Card style={{ padding: 0, gap: 0, overflow: "hidden" }}>
            <MenuRow
              icon="qr-code-outline"
              label="Merchant QR"
              color={theme.primary}
              background={theme.scheme === "dark" ? "#1e3a8a" : "#eff6ff"}
              onPress={() => router.push("/merchant/qr")}
            />
            <MenuRow
              icon="time-outline"
              label="Merchant Activity"
              color={theme.primary}
              background={theme.scheme === "dark" ? "#1e3a8a" : "#eff6ff"}
              onPress={() => router.push("/merchant/activity")}
            />
            <MenuRow
              icon="person-outline"
              label="Switch to Customer Mode"
              color="#047857"
              background={theme.scheme === "dark" ? "#052e1c" : "#ecfdf5"}
              onPress={() => {
                setMode("customer");
                router.replace("/customer");
              }}
              last
            />
          </Card>

          {/* Log out */}
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
