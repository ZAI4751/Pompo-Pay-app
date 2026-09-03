import { useRouter, type Href } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { AmountDisplay, FadeIn, InitialsAvatar } from "@/components/glass";
import { Card, EmptyState, ErrorBanner, formatMoney, Muted, PrimaryButton, Screen, SecondaryButton, useTheme } from "@/components/ui";
import { paymentMethodChargeable, paymentMethodStateLabel } from "@/domain/paymentMethod";
import { useAuth } from "@/state/AuthProvider";
import { useCheckout } from "@/state/CheckoutProvider";
import type { PaymentMethod } from "@/types";

function preferredChargeable(list: PaymentMethod[]): PaymentMethod | undefined {
  return list.find((row) => row.is_default && paymentMethodChargeable(row)) ?? list.find(paymentMethodChargeable);
}

export default function ConfirmScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const { session, selectPaymentMethod } = useCheckout();
  const [methods, setMethods] = useState<PaymentMethod[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const result = await api.listPaymentMethods();
    if (!result.ok) {
      setLoadError(result.error.message || "Payment methods could not be loaded.");
      setMethods(null);
      return;
    }
    setLoadError(null);
    setMethods(result.data);
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!methods) {
      return;
    }
    const current = session?.paymentMethodId
      ? methods.find((row) => row.id === session.paymentMethodId)
      : undefined;
    if (current && paymentMethodChargeable(current)) {
      return;
    }
    const nextId = preferredChargeable(methods)?.id ?? null;
    if ((session?.paymentMethodId ?? null) !== nextId) {
      selectPaymentMethod(nextId);
    }
  }, [methods, selectPaymentMethod, session?.paymentMethodId]);

  const selectedMethod = useMemo(() => {
    if (!methods || !session?.paymentMethodId) {
      return null;
    }
    return methods.find((row) => row.id === session.paymentMethodId) ?? null;
  }, [methods, session?.paymentMethodId]);
  const canPay = selectedMethod != null && paymentMethodChargeable(selectedMethod);

  if (!session) {
    return (
      <Screen>
        <Text style={{ color: theme.text, fontWeight: "800", fontSize: 22 }}>Nothing to confirm</Text>
        <SecondaryButton label="Back to home" onPress={() => router.replace("/customer")} />
      </Screen>
    );
  }

  const amount = session.inspect.qr_type === "dynamic" ? (session.inspect.amount ?? session.amount) : session.amount;
  const loaded = methods !== null;
  const usable = loaded ? methods.filter(paymentMethodChargeable) : [];

  return (
    <Screen>
      <Text style={[styles.kicker, { color: theme.subtle }]}>CONFIRM</Text>
      <Text style={[styles.title, { color: theme.text }]}>PAY {formatMoney(amount, session.inspect.currency)}</Text>
      <Muted>{session.inspect.merchant_name}</Muted>
      <FadeIn>
        <Card>
          <View style={styles.identity}>
            <InitialsAvatar name={session.inspect.merchant_name} size={48} active />
            <View style={{ flex: 1 }}>
              <Text style={{ color: theme.subtle, fontSize: 12 }}>Paying</Text>
              <Text style={[styles.merchant, { color: theme.text }]}>{session.inspect.merchant_name}</Text>
            </View>
          </View>
          <AmountDisplay value={formatMoney(amount, session.inspect.currency)} />
          <Text style={{ color: theme.muted }}>
            {session.inspect.branch_name} · {session.inspect.till_name}
          </Text>
          {session.inspect.qr_type === "dynamic" ? (
            <Text style={{ color: theme.subtle, marginTop: 8, fontSize: 12 }}>
              Amount comes from the QR on the server. You cannot change it here.
            </Text>
          ) : null}
        </Card>
      </FadeIn>
      <Text style={{ color: theme.text, fontWeight: "800", marginTop: 4 }}>How would you like to pay?</Text>
      <Text style={{ color: theme.subtle, fontSize: 12 }}>
        Pick a saved method. POMPO chooses the provider from that method.
      </Text>
      {loadError ? (
        <>
          <ErrorBanner message={`Payment methods could not be loaded. ${loadError}`} />
          <SecondaryButton
            label="Retry"
            onPress={() => {
              setLoadError(null);
              setMethods(null);
              void load();
            }}
          />
        </>
      ) : null}
      {!loaded && !loadError ? <Text style={{ color: theme.muted }}>Loading methods…</Text> : null}
      {loaded && usable.length === 0 ? (
        <EmptyState
          title="Add a payment method"
          body="Checkout needs an available method. TNM and Standard Bank are not usable yet."
        />
      ) : null}
      {loaded
        ? methods.map((row) => {
            const selected = session.paymentMethodId === row.id;
            const chargeable = paymentMethodChargeable(row);
            return (
              <Pressable
                key={row.id}
                disabled={!chargeable}
                accessibilityRole="button"
                accessibilityState={{ selected, disabled: !chargeable }}
                onPress={() => chargeable && selectPaymentMethod(row.id)}
              >
                <Card
                  style={{
                    borderWidth: 2,
                    borderColor: selected ? theme.primary : theme.border,
                    opacity: chargeable ? 1 : 0.55,
                  }}
                >
                  <Text style={{ color: theme.text, fontWeight: "800" }}>{row.display_name}</Text>
                  <Text style={{ color: theme.muted }}>{row.masked_identifier}</Text>
                  <Text style={{ color: theme.subtle, fontSize: 12, marginTop: 4 }}>{paymentMethodStateLabel(row)}</Text>
                </Card>
              </Pressable>
            );
          })
        : null}
      {loaded ? (
        <SecondaryButton label="+ Add payment method" onPress={() => router.push("/customer/methods/add" as Href)} />
      ) : null}
      <PrimaryButton
        label={`PAY ${formatMoney(amount, session.inspect.currency)}`}
        disabled={!canPay}
        onPress={() => {
          const current = methods?.find((row) => row.id === session.paymentMethodId);
          if (!current || !paymentMethodChargeable(current)) {
            selectPaymentMethod(preferredChargeable(methods ?? [])?.id ?? null);
            return;
          }
          router.push("/customer/processing");
        }}
      />
      <SecondaryButton label="Cancel" onPress={() => router.replace("/customer")} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  kicker: { fontSize: 11, fontWeight: "800", letterSpacing: 1.4 },
  title: { fontSize: 26, fontWeight: "800", letterSpacing: -0.6, lineHeight: 32 },
  identity: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 8 },
  merchant: { fontSize: 20, fontWeight: "800" },
});
