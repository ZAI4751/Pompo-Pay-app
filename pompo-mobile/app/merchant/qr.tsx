import { randomUUID } from "expo-crypto";
import { useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { ScrollView, Share, StyleSheet, Text, View } from "react-native";
import QRCode from "react-native-qrcode-svg";

import { AmountDisplay, FadeIn, GlassInput } from "@/components/glass";
import { BottomNav } from "@/components/nav";
import { Card, EmptyState, ErrorBanner, formatMoney, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { canCreateQr, canRevokeQr } from "@/domain/roles";
import { useAuth } from "@/state/AuthProvider";
import type { QrRecord, Till } from "@/types";

export default function MerchantQrScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { user, api } = useAuth();
  const [qrs, setQrs] = useState<QrRecord[]>([]);
  const [tillContext, setTillContext] = useState<{ branchId: string; till: Till } | null>(null);
  const [amount, setAmount] = useState("50.00");
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const canCreate = user ? canCreateQr(user.role_code) : false;

  const load = useCallback(async () => {
    setLoading(true);
    const listed = await api.listQrs();
    if (listed.ok) {
      setQrs(listed.data);
    } else if (listed.error.kind !== "forbidden") {
      setError({ message: listed.error.message, requestId: listed.error.requestId });
    }

    const accessResult = await api.getMerchantAccess();
    if (accessResult.ok && accessResult.data.allowed) {
      const access = accessResult.data;
      const opBranchId = access.operating_branch_id ?? (access.branches[0] ? access.branches[0].id : null);
      if (opBranchId) {
        const foundTill = access.tills.find(
          (t) => t.id === access.operating_till_id && t.branch_id === opBranchId
        ) ?? access.tills.find((t) => t.branch_id === opBranchId) ?? access.tills[0];

        if (foundTill) {
          setTillContext({
            branchId: opBranchId,
            till: {
              id: foundTill.id,
              branch_id: foundTill.branch_id,
              merchant_id: foundTill.merchant_id,
              code: foundTill.code,
              name: foundTill.name,
              is_active: foundTill.is_active,
            },
          });
        }
      }
    } else if (user?.merchant_id) {
      const branchId = user.branch_id;
      if (branchId) {
        const tillResult = await api.listTills(branchId);
        if (tillResult.ok) {
          const till = tillResult.data.find((item) => item.is_active);
          if (till) {
            setTillContext({ branchId, till });
          }
        }
      } else {
        const branches = await api.listBranches(user.merchant_id);
        if (branches.ok) {
          const branch = branches.data.find((item) => item.is_active);
          if (branch) {
            const tillResult = await api.listTills(branch.id);
            if (tillResult.ok) {
              const till = tillResult.data.find((item) => item.is_active);
              if (till) {
                setTillContext({ branchId: branch.id, till });
              }
            }
          }
        }
      }
    }
    setLoading(false);
  }, [api, user?.branch_id, user?.merchant_id]);

  useEffect(() => {
    void load();
  }, [load]);

  const active = qrs.find((qr) => qr.status === "active") ?? qrs[0];

  async function create(kind: "static" | "dynamic") {
    if (!user?.merchant_id || !tillContext || busy) {
      setError({ message: "A branch till is required to create a QR." });
      return;
    }
    setBusy(true);
    setError(null);
    const result =
      kind === "static"
        ? await api.createStaticQr({
            merchant_id: user.merchant_id,
            branch_id: tillContext.branchId,
            till_id: tillContext.till.id,
          })
        : await api.createDynamicQr({
            merchant_id: user.merchant_id,
            branch_id: tillContext.branchId,
            till_id: tillContext.till.id,
            amount: Number(amount).toFixed(2),
            idempotency_key: randomUUID(),
          });
    setBusy(false);
    if (!result.ok) {
      setError({ message: result.error.message, requestId: result.error.requestId });
      return;
    }
    await load();
  }

  return (
    <Screen padded={false}>
      <View style={{ flex: 1 }}>
        <View style={{ paddingHorizontal: 20, paddingTop: 8 }}>
          <Title>QR</Title>
          <Text style={{ color: theme.subtle, marginTop: 4 }}>Show this code. Keep the plate solid white.</Text>
        </View>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
          {loading && !active ? (
            <Text style={{ color: theme.muted }}>Loading QR codes…</Text>
          ) : active ? (
            <FadeIn>
              <View style={[styles.frame, { backgroundColor: theme.glassFill, borderColor: theme.glassBorder }]}>
                <View style={styles.plate}>
                  <QRCode
                    value={active.payment_url || `https://pay.pompo.mw/p/${active.public_identifier}`}
                    size={200}
                    backgroundColor="#ffffff"
                    color="#0f172a"
                  />
                </View>
                <Text style={{ color: theme.text, fontWeight: "800", fontSize: 18 }}>{active.merchant_name}</Text>
                {active.qr_type === "dynamic" ? (
                  <AmountDisplay value={formatMoney(active.amount ?? "0", active.currency)} />
                ) : (
                  <Text style={{ color: theme.muted }}>Static · customer enters amount</Text>
                )}
                <Text style={{ color: theme.subtle }}>
                  {tillContext ? `${tillContext.till.name} · ` : ""}
                  {active.status}
                </Text>
                <SecondaryButton
                  label="Share"
                  onPress={() => {
                    const shareUrl = active.payment_url || `https://pay.pompo.mw/p/${active.public_identifier}`;
                    void Share.share({
                      message: `Pay ${active.merchant_name} with POMPO:\n${shareUrl}`,
                    });
                  }}
                />
                {canRevokeQr(user?.role_code ?? "") && active.status === "active" ? (
                  <SecondaryButton
                    label="Revoke"
                    onPress={async () => {
                      const revoked = await api.revokeQr(active.public_identifier);
                      if (!revoked.ok) {
                        setError({ message: revoked.error.message, requestId: revoked.error.requestId });
                        return;
                      }
                      await load();
                    }}
                  />
                ) : null}
              </View>
            </FadeIn>
          ) : (
            <EmptyState
              title="No QR yet"
              body={
                tillContext
                  ? "Generate a static or dynamic QR for this till. Customers scan it to pay."
                  : "A branch till is required before you can generate a QR."
              }
            />
          )}
          {canCreate ? (
            <View style={{ gap: 10 }}>
              <GlassInput value={amount} onChangeText={setAmount} keyboardType="decimal-pad" />
              <PrimaryButton label="New dynamic QR" loading={busy} onPress={() => void create("dynamic")} />
              <SecondaryButton label="New static QR" onPress={() => void create("static")} />
            </View>
          ) : (
            <Text style={{ color: theme.muted }}>Ask a merchant owner to generate QR codes.</Text>
          )}
          {qrs.slice(0, 6).map((qr) => (
            <Card key={qr.public_identifier}>
              <Text
                onPress={() => router.push(`/merchant/qr/${qr.public_identifier}`)}
                style={{ color: theme.text, fontWeight: "800" }}
              >
                {qr.qr_type === "dynamic" ? "Dynamic QR" : "Static QR"}
              </Text>
              <Text style={{ color: theme.subtle, marginTop: 4 }}>
                {qr.status}
                {qr.amount ? ` · ${formatMoney(qr.amount, qr.currency)}` : ""}
              </Text>
              <Text
                onPress={() => router.push(`/merchant/qr/${qr.public_identifier}`)}
                style={{ color: theme.primary, fontWeight: "700", marginTop: 8 }}
              >
                Open
              </Text>
            </Card>
          ))}
        </ScrollView>
      </View>
      <BottomNav active="qr" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: { paddingHorizontal: 20, paddingTop: 16, paddingBottom: 20, gap: 16 },
  frame: {
    borderWidth: 1,
    borderRadius: 28,
    padding: 18,
    alignItems: "center",
    gap: 12,
  },
  plate: {
    backgroundColor: "#ffffff",
    padding: 16,
    borderRadius: 20,
  },
});
