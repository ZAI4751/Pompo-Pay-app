import { randomUUID } from "expo-crypto";
import { useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Share, Text, View } from "react-native";
import QRCode from "react-native-qrcode-svg";

import { AmountDisplay, GlassInput, GlassSurface } from "@/components/glass";
import { BottomNav } from "@/components/nav";
import { Card, ErrorBanner, formatMoney, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
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
  const canCreate = user ? canCreateQr(user.role_code) : false;

  const load = useCallback(async () => {
    const listed = await api.listQrs();
    if (listed.ok) {
      setQrs(listed.data);
    } else if (listed.error.kind !== "forbidden") {
      setError({ message: listed.error.message, requestId: listed.error.requestId });
    }
    if (user?.merchant_id) {
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
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 12, gap: 12 }}>
        <Title>QR</Title>
        {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
        {active ? (
          <GlassSurface style={{ alignItems: "center", gap: 12 }}>
            <View
              style={{
                backgroundColor: "#ffffff",
                padding: 16,
                borderRadius: 16,
                shadowColor: theme.primary,
                shadowOpacity: active.qr_type === "dynamic" ? 0.22 : 0.08,
                shadowRadius: 18,
                shadowOffset: { width: 0, height: 0 },
              }}
            >
              <QRCode value={active.encoded_payload} size={200} backgroundColor="#ffffff" color="#0f172a" />
            </View>
            <Text style={{ color: theme.text, fontWeight: "700" }}>{active.merchant_name}</Text>
            {active.qr_type === "dynamic" ? (
              <AmountDisplay value={formatMoney(active.amount ?? "0", active.currency)} />
            ) : (
              <Text style={{ color: theme.muted }}>Static · customer enters amount</Text>
            )}
            {tillContext ? (
              <Text style={{ color: theme.subtle }}>
                {tillContext.till.name} · {active.status}
              </Text>
            ) : (
              <Text style={{ color: theme.subtle }}>{active.status}</Text>
            )}
            <SecondaryButton
              label="Share"
              onPress={() =>
                void Share.share({
                  message: `Pay ${active.merchant_name} with POMPO\n${active.encoded_payload}`,
                })
              }
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
          </GlassSurface>
        ) : (
          <Card>
            <Text style={{ color: theme.muted }}>No QR codes yet.</Text>
          </Card>
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
          <Text
            key={qr.public_identifier}
            onPress={() => router.push(`/merchant/qr/${qr.public_identifier}`)}
            style={{ color: theme.primary, fontWeight: "600" }}
          >
            {qr.qr_type} · {qr.status} · {qr.public_identifier}
          </Text>
        ))}
      </View>
      <BottomNav active="qr" />
    </Screen>
  );
}
