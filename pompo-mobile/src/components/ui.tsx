import { useEffect, useState, type ReactNode } from "react";
import {
  Appearance,
  Pressable,
  StyleSheet,
  Text,
  View,
  type PressableProps,
  type TextStyle,
  type ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { currentScheme, getTheme, type Theme } from "@/theme";

export function useTheme(): Theme {
  const [scheme, setScheme] = useState(currentScheme);
  useEffect(() => {
    const sub = Appearance.addChangeListener(({ colorScheme }) => {
      setScheme(colorScheme === "dark" ? "dark" : "light");
    });
    return () => sub.remove();
  }, []);
  return getTheme(scheme);
}

export function Screen({
  children,
  padded = true,
}: {
  children: ReactNode;
  padded?: boolean;
}) {
  const theme = useTheme();
  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: theme.background }]} edges={["top", "left", "right"]}>
      <View style={[styles.body, padded && styles.padded]}>{children}</View>
    </SafeAreaView>
  );
}

export function Title({ children }: { children: ReactNode }) {
  const theme = useTheme();
  return <Text style={[styles.title, { color: theme.text }]}>{children}</Text>;
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
    <Pressable
      accessibilityRole="button"
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: theme.primary, opacity: isDisabled ? 0.55 : pressed ? 0.86 : 1 },
      ]}
      {...rest}
    >
      <Text style={[styles.buttonLabel, { color: theme.primaryForeground }]}>
        {loading ? "Please wait…" : label}
      </Text>
    </Pressable>
  );
}

export function SecondaryButton({ label, ...rest }: PressableProps & { label: string }) {
  const theme = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.secondary,
        { borderColor: theme.border, backgroundColor: theme.surface, opacity: pressed ? 0.86 : 1 },
      ]}
      {...rest}
    >
      <Text style={[styles.secondaryLabel, { color: theme.text }]}>{label}</Text>
    </Pressable>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  const theme = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }, style]}>
      {children}
    </View>
  );
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
    <View style={styles.empty}>
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
  padded: { paddingHorizontal: 20, paddingTop: 12 },
  title: { fontSize: 28, fontWeight: "700", letterSpacing: -0.4 },
  muted: { fontSize: 15, lineHeight: 22 },
  button: { borderRadius: 16, paddingVertical: 16, alignItems: "center" },
  buttonLabel: { fontSize: 16, fontWeight: "700" },
  secondary: { borderRadius: 16, paddingVertical: 14, alignItems: "center", borderWidth: 1 },
  secondaryLabel: { fontSize: 15, fontWeight: "600" },
  card: { borderRadius: 20, padding: 18, borderWidth: 1, gap: 8 },
  error: { borderRadius: 14, padding: 12, gap: 4 },
  errorText: { fontSize: 14, fontWeight: "600" },
  requestId: { fontSize: 12 },
  empty: { alignItems: "center", paddingVertical: 48, gap: 8 },
  emptyTitle: { fontSize: 18, fontWeight: "700" },
});

export const textStyle = (color: string, extra?: TextStyle): TextStyle => ({ color, ...extra });
