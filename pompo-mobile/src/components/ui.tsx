import { type ReactNode } from "react";
import {
  StyleSheet,
  Text,
  View,
  type PressableProps,
  type TextStyle,
  type ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Atmosphere, GlassCard, GlassInput, PressScale } from "@/components/glass";
import { radius, useTheme } from "@/theme";

export { useTheme } from "@/theme";
export { GlassInput };

export function Screen({
  children,
  padded = true,
  atmosphere = true,
}: {
  children: ReactNode;
  padded?: boolean;
  atmosphere?: boolean;
}) {
  const theme = useTheme();
  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: theme.background }]} edges={["top", "left", "right"]}>
      {atmosphere ? <Atmosphere /> : null}
      <View style={[styles.body, padded && styles.padded]}>{children}</View>
    </SafeAreaView>
  );
}

export function Title({ children }: { children: ReactNode }) {
  const theme = useTheme();
  return <Text style={[styles.title, { color: theme.text }]}>{children}</Text>;
}

export function Greeting({ name, subtitle }: { name: string; subtitle: string }) {
  const theme = useTheme();
  return (
    <View style={styles.greeting}>
      <Text style={[styles.hello, { color: theme.text }]}>Hello {name}</Text>
      <Text style={[styles.welcome, { color: theme.subtle }]}>{subtitle}</Text>
    </View>
  );
}

export function Muted({ children }: { children: string }) {
  const theme = useTheme();
  return <Text style={[styles.muted, { color: theme.muted }]}>{children}</Text>;
}

export function PrimaryButton({
  label,
  loading,
  disabled,
  ...rest
}: PressableProps & { label: string; loading?: boolean }) {
  const theme = useTheme();
  const isDisabled = Boolean(disabled || loading);
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: isDisabled }}
      disabled={isDisabled}
      {...rest}
      style={[
        styles.button,
        {
          backgroundColor: theme.primary,
          opacity: isDisabled ? 0.55 : 1,
          shadowColor: theme.primary,
        },
      ]}
    >
      <Text style={[styles.buttonLabel, { color: theme.primaryForeground }]}>
        {loading ? "Please wait…" : label}
      </Text>
    </PressScale>
  );
}

export function SecondaryButton({ label, ...rest }: PressableProps & { label: string }) {
  const theme = useTheme();
  return (
    <PressScale
      accessibilityRole="button"
      {...rest}
      style={[
        styles.secondary,
        { borderColor: theme.border, backgroundColor: theme.surface },
      ]}
    >
      <Text style={[styles.secondaryLabel, { color: theme.text }]}>{label}</Text>
    </PressScale>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  return <GlassCard style={style}>{children}</GlassCard>;
}

export function ErrorBanner({ message, requestId }: { message: string; requestId?: string }) {
  const theme = useTheme();
  return (
    <View style={[styles.error, { backgroundColor: theme.errorBg }]}>
      <Text style={[styles.errorText, { color: theme.error }]}>{message}</Text>
      {requestId ? (
        <Text style={[styles.requestId, { color: theme.subtle }]}>Support ID {requestId}</Text>
      ) : null}
    </View>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  const theme = useTheme();
  return (
    <View style={[styles.empty, { backgroundColor: theme.surface, borderColor: theme.border }]}>
      <View style={[styles.emptyMark, { backgroundColor: theme.scheme === "dark" ? "#1e293b" : "#eff6ff" }]}>
        <Text style={{ color: theme.primary, fontSize: 22, fontWeight: "800" }}>P</Text>
      </View>
      <Text style={[styles.emptyTitle, { color: theme.text }]}>{title}</Text>
      <Text style={[styles.muted, { color: theme.muted, textAlign: "center" }]}>{body}</Text>
    </View>
  );
}

export function formatMoney(amount: string, currency = "MWK"): string {
  const numeric = Number(amount);
  if (Number.isNaN(numeric)) {
    return `${currency} ${amount}`;
  }
  return `${currency} ${numeric.toLocaleString("en-MW", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  body: { flex: 1 },
  padded: { paddingHorizontal: 20, paddingTop: 8, gap: 16 },
  title: { fontSize: 22, fontWeight: "800", letterSpacing: -0.4 },
  greeting: { gap: 2 },
  hello: { fontSize: 20, fontWeight: "800", letterSpacing: -0.3 },
  welcome: { fontSize: 13, fontWeight: "500" },
  muted: { fontSize: 14, lineHeight: 20 },
  button: {
    borderRadius: radius.md,
    paddingVertical: 16,
    alignItems: "center",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.28,
    shadowRadius: 18,
    elevation: 5,
  },
  buttonLabel: { fontSize: 16, fontWeight: "700" },
  secondary: { borderRadius: radius.md, paddingVertical: 14, alignItems: "center", borderWidth: 1 },
  secondaryLabel: { fontSize: 15, fontWeight: "600" },
  error: { borderRadius: 14, padding: 12, gap: 4 },
  errorText: { fontSize: 14, fontWeight: "600" },
  requestId: { fontSize: 12 },
  empty: {
    alignItems: "center",
    paddingVertical: 36,
    paddingHorizontal: 20,
    gap: 8,
    borderRadius: radius.lg,
    borderWidth: 1,
  },
  emptyMark: {
    width: 52,
    height: 52,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  emptyTitle: { fontSize: 17, fontWeight: "800" },
});

export const textStyle = (color: string, extra?: TextStyle): TextStyle => ({ color, ...extra });
