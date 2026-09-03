import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { FlatList, Share, Text, View } from "react-native";

import { Card, EmptyState, ErrorBanner, GlassInput, PrimaryButton, Screen, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import type { PaymentRequest } from "@/types";

const EXPIRY_OPTIONS = [
  { label: "1 hour", seconds: 3600 },
  { label: "24 hours", seconds: 86400 },
  { label: "7 days", seconds: 604800 },
] as const;

export default function PaymentRequestsScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const { from } = useLocalSearchParams<{ from?: string }>();
  const [rows, setRows] = useState<PaymentRequest[]>([]);
  const [sourceReference, setSourceReference] = useState(from ?? "");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("Bill share");
  const [splitTotal, setSplitTotal] = useState("");
  const [shareA, setShareA] = useState("");
  const [shareB, setShareB] = useState("");
  const [shareC, setShareC] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [expiresIn, setExpiresIn] = useState(86400);

  const load = useCallback(async () => {
    const result = await api.listPaymentRequests();
    if (result.ok) setRows(result.data);
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (from) {
      setSourceReference(from);
      return;
    }
    void api.listMyPayments({ status: "success" }).then((result) => {
      if (result.ok && result.data[0] && !sourceReference) {
        setSourceReference(result.data[0].reference);
      }
    });
    // Default destination from the latest successful payment only once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, from]);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8 }}>
        <Title>Payment requests</Title>
        <Text style={{ color: theme.subtle, marginBottom: 12 }}>
          Ask someone to pay a merchant. POMPO does not hold the money.
        </Text>
        {error ? <ErrorBanner message={error} /> : null}
        <Card>
          <Text style={{ color: theme.text, fontWeight: "700", marginBottom: 8 }}>Create a request</Text>
          <GlassInput
            placeholder="Previous payment reference"
            value={sourceReference}
            onChangeText={setSourceReference}
          />
          <GlassInput placeholder="Amount MWK" keyboardType="decimal-pad" value={amount} onChangeText={setAmount} />
          <GlassInput placeholder="Description" value={description} onChangeText={setDescription} />
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12, marginBottom: 8 }}>
            {EXPIRY_OPTIONS.map((option) => (
              <Text
                key={option.seconds}
                accessibilityRole="button"
                onPress={() => setExpiresIn(option.seconds)}
                style={{
                  color: expiresIn === option.seconds ? theme.primary : theme.muted,
                  fontWeight: "700",
                  fontSize: 12,
                }}
              >
                Expires {option.label}
              </Text>
            ))}
          </View>
          <PrimaryButton
            label="Create request"
            loading={loading}
            onPress={async () => {
              setError(null);
              if (!sourceReference.trim()) {
                setError("Choose a previous successful payment so the request has a merchant destination.");
                return;
              }
              setLoading(true);
              const result = await api.createPaymentRequest({
                amount,
                description,
                source_payment_reference: sourceReference.trim(),
                expires_in_seconds: expiresIn,
                idempotency_key: `req-${Date.now()}`,
              });
              setLoading(false);
              if (!result.ok) {
                setError(result.error.message);
                return;
              }
              setAmount("");
              await load();
              void Share.share({
                message: `POMPO payment request ${result.data.share_code} for ${result.data.amount} ${result.data.currency} to ${result.data.merchant_name ?? "a merchant"}.`,
              });
            }}
          />
        </Card>
        <Card>
          <Text style={{ color: theme.text, fontWeight: "700", marginBottom: 8 }}>Split a bill</Text>
          <Text style={{ color: theme.subtle, marginBottom: 8 }}>
            Each person gets their own request. Amounts must add up to the total.
          </Text>
          <GlassInput
            placeholder="Total MWK"
            keyboardType="decimal-pad"
            value={splitTotal}
            onChangeText={(value) => {
              setSplitTotal(value);
              const total = Number(value);
              if (Number.isFinite(total) && total > 0) {
                const share = (total / 3).toFixed(2);
                setShareA(share);
                setShareB(share);
                setShareC((total - Number(share) * 2).toFixed(2));
              }
            }}
          />
          <GlassInput placeholder="Person A MWK" keyboardType="decimal-pad" value={shareA} onChangeText={setShareA} />
          <GlassInput placeholder="Person B MWK" keyboardType="decimal-pad" value={shareB} onChangeText={setShareB} />
          <GlassInput placeholder="Person C MWK" keyboardType="decimal-pad" value={shareC} onChangeText={setShareC} />
          <PrimaryButton
            label="Create split"
            loading={loading}
            onPress={async () => {
              setError(null);
              if (!sourceReference.trim()) {
                setError("Choose a previous successful payment so the split has a merchant destination.");
                return;
              }
              setLoading(true);
              const result = await api.createBillSplit({
                total_amount: splitTotal,
                description,
                source_payment_reference: sourceReference.trim(),
                expires_in_seconds: expiresIn,
                participants: [
                  { amount: shareA, label: "Person A" },
                  { amount: shareB, label: "Person B" },
                  { amount: shareC, label: "Person C" },
                ],
                idempotency_key: `split-${Date.now()}`,
              });
              setLoading(false);
              if (!result.ok) {
                setError(result.error.message);
                return;
              }
              await load();
              const codes = result.data.requests.map((item) => item.share_code).join("\n");
              void Share.share({
                message: `POMPO bill split ${result.data.public_identifier}\n${codes}`,
              });
            }}
          />
        </Card>
        <FlatList
          data={rows}
          keyExtractor={(item) => item.id}
          ListEmptyComponent={
            <EmptyState
              title="No requests yet"
              body="Create a request or split. Recipients pay the merchant directly. POMPO does not hold the money."
            />
          }
          renderItem={({ item }) => (
            <Card>
              <Text style={{ color: theme.text, fontWeight: "700" }}>
                {item.merchant_name ?? "Merchant"} · {item.status.toUpperCase()}
              </Text>
              <Text style={{ color: theme.muted }}>
                {item.amount} {item.currency}
                {item.description ? ` · ${item.description}` : ""}
              </Text>
              {item.expires_at ? (
                <Text style={{ color: theme.subtle, marginTop: 4, fontSize: 12 }}>Expires {item.expires_at}</Text>
              ) : null}
              <Text
                accessibilityRole="link"
                style={{ color: theme.primary, marginTop: 8 }}
                onPress={() =>
                  router.push({
                    pathname: "/customer/requests/[publicId]",
                    params: { publicId: item.public_identifier },
                  })
                }
              >
                Open
              </Text>
            </Card>
          )}
        />
      </View>
    </Screen>
  );
}
