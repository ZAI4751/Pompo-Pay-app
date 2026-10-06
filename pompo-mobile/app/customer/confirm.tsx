import { useRouter } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { AmountDisplay, FadeIn, GlassInput, InitialsAvatar } from "@/components/glass";
import { Card, EmptyState, ErrorBanner, formatMoney, Muted, PrimaryButton, Screen, SecondaryButton, useTheme } from "@/components/ui";
import { catalogMethodSelectable, catalogOfferLabel } from "@/domain/paymentMethod";
import { useAuth } from "@/state/AuthProvider";
import { useCheckout } from "@/state/CheckoutProvider";
import type { PaymentMethodCatalogItem } from "@/types";

function sameMethod(left: PaymentMethodCatalogItem | null, right: PaymentMethodCatalogItem | null): boolean {
  return (
    left?.provider_code === right?.provider_code &&
    left?.instrument_type === right?.instrument_type
  );
}

export default function ConfirmScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const { session, selectPaymentMethod, setCustomerPhone } = useCheckout();
  const [methods, setMethods] = useState<PaymentMethodCatalogItem[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const result = await api.paymentMethodCatalog();
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
    const current = methods.find((method) => sameMethod(method, session?.paymentMethod ?? null));
    if (current && catalogMethodSelectable(current)) {
      if (current !== session?.paymentMethod) {
        selectPaymentMethod(current);
      }
      return;
    }
    const next = methods.find(catalogMethodSelectable) ?? null;
    if (!sameMethod(next, session?.paymentMethod ?? null)) {
      selectPaymentMethod(next);
    }
  }, [methods, selectPaymentMethod, session?.paymentMethod]);

  const selectedMethod = useMemo(() => {
    if (!methods || !session?.paymentMethod) {
      return null;
    }
    return methods.find((method) => sameMethod(method, session.paymentMethod)) ?? null;
  }, [methods, session?.paymentMethod]);
  const canPay = selectedMethod != null && catalogMethodSelectable(selectedMethod);

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
  const hasSelectableMethod = loaded && methods.some(catalogMethodSelectable);

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
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
          Available payment options are provided by POMPO.
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
        {!loaded && !loadError ? <Text style={{ color: theme.muted }}>Loading payment options…</Text> : null}
        {loaded && !hasSelectableMethod ? (
          <EmptyState
            title="No payment methods available"
            body="There are no payment options available for checkout right now."
          />
        ) : null}
        {loaded
          ? methods.map((method) => {
              const selectable = catalogMethodSelectable(method);
              const selected = sameMethod(session.paymentMethod, method);
              return (
                <Pressable
                  key={`${method.provider_code}:${method.instrument_type}`}
                  disabled={!selectable}
                  accessibilityRole="button"
                  accessibilityLabel={`${method.label}${method.is_sandbox ? " sandbox" : ""}`}
                  accessibilityState={{ selected, disabled: !selectable }}
                  onPress={() => selectable && selectPaymentMethod(method)}
                >
                  <Card
                    style={{
                      borderWidth: 2,
                      borderColor: selected ? theme.primary : theme.border,
                      opacity: selectable ? 1 : 0.55,
                    }}
                  >
                    <Text style={{ color: theme.text, fontWeight: "800" }}>{method.label}</Text>
                    <Text style={{ color: theme.subtle, fontSize: 12, marginTop: 4 }}>
                      {catalogOfferLabel(method)}
                    </Text>
                  </Card>
                </Pressable>
              );
            })
          : null}
        {selectedMethod?.instrument_type === "mobile_money" ? (
          <View style={{ gap: 8 }}>
            <Text style={{ color: theme.muted }}>Mobile-money number (optional)</Text>
            <GlassInput
              accessibilityLabel="Mobile-money number"
              placeholder="+265 88…"
              keyboardType="phone-pad"
              value={session.customerPhone}
              onChangeText={setCustomerPhone}
            />
          </View>
        ) : null}
        <PrimaryButton
          label={`PAY ${formatMoney(amount, session.inspect.currency)}`}
          disabled={!canPay}
          onPress={() => {
            if (!selectedMethod || !catalogMethodSelectable(selectedMethod)) {
              return;
            }
            selectPaymentMethod(selectedMethod);
            router.push("/customer/processing");
          }}
        />
        <SecondaryButton label="Cancel" onPress={() => router.replace("/customer")} />
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 16, paddingBottom: 24 },
  kicker: { fontSize: 11, fontWeight: "800", letterSpacing: 1.4 },
  title: { fontSize: 26, fontWeight: "800", letterSpacing: -0.6, lineHeight: 32 },
  identity: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 8 },
  merchant: { fontSize: 20, fontWeight: "800" },
});
