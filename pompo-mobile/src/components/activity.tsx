import { Ionicons } from "@expo/vector-icons";
import { type ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { IconWell, PressScale, StatusPill } from "@/components/glass";
import { formatMoney, useTheme } from "@/components/ui";
import { formatWhen, merchantHue } from "@/format";
import { mapPaymentStatus, paymentStatusLabel } from "@/domain/paymentStatus";
import type { Payment } from "@/types";

export function SectionHeader({
  title,
  action,
  onAction,
}: {
  title: string;
  action?: string;
  onAction?: () => void;
}) {
  const theme = useTheme();
  return (
    <View style={styles.section}>
      <Text style={[styles.sectionTitle, { color: theme.text }]}>{title}</Text>
      {action && onAction ? (
        <PressScale accessibilityRole="button" onPress={onAction} hitSlop={8}>
          <Text style={{ color: theme.primary, fontSize: 12, fontWeight: "700" }}>{action}</Text>
        </PressScale>
      ) : null}
    </View>
  );
}

export function ActionTile({
  label,
  icon,
  onPress,
}: {
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
}) {
  const theme = useTheme();
  return (
    <PressScale accessibilityRole="button" accessibilityLabel={label} onPress={onPress} style={styles.tile}>
      <View
        style={[
          styles.tileIcon,
          {
            backgroundColor: theme.surface,
            borderColor: theme.border,
            shadowColor: theme.shadow,
          },
        ]}
      >
        <Ionicons name={icon} size={20} color={theme.primary} />
      </View>
      <Text style={[styles.tileLabel, { color: theme.muted }]}>{label}</Text>
    </PressScale>
  );
}

export function PaymentRow({
  payment,
  onPress,
  emphasizeAmount = false,
}: {
  payment: Payment;
  onPress: () => void;
  emphasizeAmount?: boolean;
}) {
  const theme = useTheme();
  const phase = mapPaymentStatus(payment.status);
  const tone = phase === "success" ? "success" : phase === "failed" || phase === "timeout" ? "error" : "pending";
  const name = payment.merchant_name ?? "Merchant";
  return (
    <PressScale accessibilityRole="button" onPress={onPress} style={styles.row}>
      <IconWell background={merchantHue(name)}>
        <Text style={{ color: theme.text, fontWeight: "800", fontSize: 13 }}>{name.slice(0, 1).toUpperCase()}</Text>
      </IconWell>
      <View style={styles.rowBody}>
        <Text style={[styles.rowTitle, { color: theme.text }]} numberOfLines={1}>
          {emphasizeAmount ? formatMoney(payment.amount, payment.currency) : name}
        </Text>
        <Text style={[styles.rowMeta, { color: theme.subtle }]} numberOfLines={1}>
          {emphasizeAmount ? payment.reference : formatWhen(payment.created_at) || payment.reference}
        </Text>
      </View>
      <View style={styles.rowTrail}>
        {emphasizeAmount ? null : (
          <Text style={[styles.rowAmount, { color: theme.text }]}>
            {formatMoney(payment.amount, payment.currency)}
          </Text>
        )}
        <StatusPill label={paymentStatusLabel(payment.status)} tone={tone} />
      </View>
    </PressScale>
  );
}

export function MenuRow({
  icon,
  label,
  color,
  background,
  onPress,
  trailing,
  last = false,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  color: string;
  background: string;
  onPress?: () => void;
  trailing?: ReactNode;
  last?: boolean;
}) {
  const theme = useTheme();
  return (
    <PressScale
      accessibilityRole={onPress ? "button" : undefined}
      onPress={onPress}
      disabled={!onPress}
      style={[styles.menuRow, !last && { borderBottomWidth: 1, borderBottomColor: theme.border }]}
    >
      <IconWell background={background} size={36}>
        <Ionicons name={icon} size={17} color={color} />
      </IconWell>
      <Text style={[styles.menuLabel, { color: theme.text }]}>{label}</Text>
      {trailing ?? <Ionicons name="chevron-forward" size={16} color={theme.subtle} />}
    </PressScale>
  );
}

const styles = StyleSheet.create({
  section: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  sectionTitle: { fontSize: 16, fontWeight: "800" },
  tile: { flex: 1, alignItems: "center", gap: 8 },
  tileIcon: {
    width: 56,
    height: 56,
    borderRadius: 16,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 1,
    shadowRadius: 10,
    elevation: 2,
  },
  tileLabel: { fontSize: 12, fontWeight: "700" },
  row: { flexDirection: "row", alignItems: "center", gap: 12, paddingHorizontal: 14, paddingVertical: 12 },
  rowBody: { flex: 1, minWidth: 0, gap: 2 },
  rowTitle: { fontSize: 14, fontWeight: "700" },
  rowMeta: { fontSize: 12, fontWeight: "500" },
  rowTrail: { alignItems: "flex-end", gap: 6 },
  rowAmount: { fontSize: 13, fontWeight: "800" },
  menuRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 14,
    paddingVertical: 14,
  },
  menuLabel: { flex: 1, fontSize: 14, fontWeight: "700" },
});
