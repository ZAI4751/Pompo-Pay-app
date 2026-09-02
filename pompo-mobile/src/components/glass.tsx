import { useEffect, useState, type ReactNode } from "react";
import {
  Animated,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type PressableProps,
  type StyleProp,
  type TextInputProps,
  type TextStyle,
  type ViewStyle,
} from "react-native";

import { duration, pressIn, pressOut } from "@/motion";
import { radius, space, useTheme } from "@/theme";

export function Atmosphere({ children }: { children?: ReactNode }) {
  const theme = useTheme();
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <View style={[styles.glow, styles.glowA, { backgroundColor: theme.glowA }]} />
      <View style={[styles.glow, styles.glowB, { backgroundColor: theme.glowB }]} />
      <View style={[styles.glow, styles.glowC, { backgroundColor: theme.glowC }]} />
      {children}
    </View>
  );
}

export function GlassSurface({
  children,
  style,
  solid = false,
}: {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  solid?: boolean;
}) {
  const theme = useTheme();
  return (
    <View
      style={[
        styles.glass,
        {
          backgroundColor: solid ? theme.glassSolid : theme.glassFill,
          borderColor: theme.glassBorder,
          shadowColor: theme.shadow,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

export function GlassCard({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  const theme = useTheme();
  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: theme.sheet,
          borderColor: theme.border,
          shadowColor: theme.shadow,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

export function PressScale({
  children,
  style,
  onPressIn,
  onPressOut,
  ...rest
}: PressableProps & { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  const [scale] = useState(() => new Animated.Value(1));
  return (
    <Pressable
      {...rest}
      onPressIn={(event) => {
        pressIn(scale);
        onPressIn?.(event);
      }}
      onPressOut={(event) => {
        pressOut(scale);
        onPressOut?.(event);
      }}
    >
      <Animated.View style={[{ transform: [{ scale }] }, style]}>{children}</Animated.View>
    </Pressable>
  );
}

export function GlassPill({
  children,
  onPress,
  accessibilityLabel,
}: {
  children: ReactNode;
  onPress?: () => void;
  accessibilityLabel?: string;
}) {
  const theme = useTheme();
  const inner = (
    <View
      style={[
        styles.pill,
        { backgroundColor: theme.glassFill, borderColor: theme.glassBorder },
      ]}
    >
      {typeof children === "string" ? (
        <Text style={[styles.pillLabel, { color: theme.muted }]}>{children}</Text>
      ) : (
        children
      )}
    </View>
  );
  if (!onPress) {
    return inner;
  }
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      onPress={onPress}
      hitSlop={8}
    >
      {inner}
    </PressScale>
  );
}

export function GlassInput(props: TextInputProps) {
  const theme = useTheme();
  return (
    <TextInput
      placeholderTextColor={theme.subtle}
      {...props}
      style={[
        styles.input,
        {
          borderColor: theme.border,
          color: theme.text,
          backgroundColor: theme.surface,
        },
        props.style,
      ]}
    />
  );
}

export function AmountDisplay({
  value,
  style,
}: {
  value: string;
  style?: StyleProp<TextStyle>;
}) {
  const theme = useTheme();
  return <Text style={[styles.amount, { color: theme.darkBlue }, style]}>{value}</Text>;
}

export function StatusPill({ label, tone }: { label: string; tone: "success" | "error" | "pending" | "neutral" }) {
  const theme = useTheme();
  const map = {
    success: { bg: theme.successBg, fg: theme.success },
    error: { bg: theme.errorBg, fg: theme.error },
    pending: { bg: theme.scheme === "dark" ? "#1e293b" : "#eff6ff", fg: theme.primary },
    neutral: { bg: theme.surfaceRaised, fg: theme.muted },
  }[tone];
  return (
    <View style={[styles.status, { backgroundColor: map.bg }]}>
      <Text style={[styles.statusLabel, { color: map.fg }]}>{label}</Text>
    </View>
  );
}

export function FadeIn({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  const [opacity] = useState(() => new Animated.Value(0));
  const [translate] = useState(() => new Animated.Value(10));
  useEffect(() => {
    const timer = setTimeout(() => {
      Animated.parallel([
        Animated.timing(opacity, {
          toValue: 1,
          duration: duration.component,
          useNativeDriver: true,
        }),
        Animated.timing(translate, {
          toValue: 0,
          duration: duration.component,
          useNativeDriver: true,
        }),
      ]).start();
    }, delay);
    return () => clearTimeout(timer);
  }, [delay, opacity, translate]);
  return <Animated.View style={{ opacity, transform: [{ translateY: translate }] }}>{children}</Animated.View>;
}

export function ScanLine() {
  const theme = useTheme();
  const [y] = useState(() => new Animated.Value(0));
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(y, { toValue: 1, duration: 1600, useNativeDriver: true }),
        Animated.timing(y, { toValue: 0, duration: 1600, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [y]);
  const translateY = y.interpolate({ inputRange: [0, 1], outputRange: [8, 168] });
  return (
    <Animated.View
      pointerEvents="none"
      style={[styles.scanLine, { backgroundColor: theme.primary, transform: [{ translateY }] }]}
    />
  );
}

export function ProcessingPulse() {
  const theme = useTheme();
  const [scale] = useState(() => new Animated.Value(0.86));
  const [opacity] = useState(() => new Animated.Value(0.55));
  useEffect(() => {
    const loop = Animated.loop(
      Animated.parallel([
        Animated.sequence([
          Animated.timing(scale, { toValue: 1.08, duration: 900, useNativeDriver: true }),
          Animated.timing(scale, { toValue: 0.86, duration: 900, useNativeDriver: true }),
        ]),
        Animated.sequence([
          Animated.timing(opacity, { toValue: 0.18, duration: 900, useNativeDriver: true }),
          Animated.timing(opacity, { toValue: 0.55, duration: 900, useNativeDriver: true }),
        ]),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [opacity, scale]);
  return (
    <View style={styles.pulseWrap}>
      <Animated.View
        style={[
          styles.pulse,
          { borderColor: theme.primary, opacity, transform: [{ scale }] },
        ]}
      />
      <View style={[styles.pulseCore, { backgroundColor: theme.primary }]} />
    </View>
  );
}

export function SuccessMark() {
  const theme = useTheme();
  const [scale] = useState(() => new Animated.Value(0.6));
  const [opacity] = useState(() => new Animated.Value(0));
  useEffect(() => {
    Animated.parallel([
      Animated.spring(scale, { toValue: 1, friction: 6, tension: 80, useNativeDriver: true }),
      Animated.timing(opacity, { toValue: 1, duration: duration.component, useNativeDriver: true }),
    ]).start();
  }, [opacity, scale]);
  return (
    <Animated.View
      style={[
        styles.successMark,
        { backgroundColor: theme.successBg, opacity, transform: [{ scale }] },
      ]}
    >
      <Text style={[styles.successGlyph, { color: theme.success }]}>✓</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  glow: { position: "absolute", borderRadius: 999 },
  glowA: { width: 340, height: 340, top: -120, left: -80 },
  glowB: { width: 280, height: 280, top: -40, right: -90 },
  glowC: { width: 260, height: 260, bottom: 80, right: -40 },
  glass: {
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: space.md,
    overflow: "hidden",
  },
  card: {
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: 18,
    gap: 8,
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.18,
    shadowRadius: 24,
    elevation: 4,
  },
  pill: {
    alignSelf: "flex-start",
    borderRadius: radius.pill,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  pillLabel: { fontSize: 13, fontWeight: "600" },
  input: {
    borderWidth: 1,
    borderRadius: radius.sm,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 16,
  },
  amount: { fontSize: 34, fontWeight: "800", letterSpacing: -0.8 },
  status: { alignSelf: "flex-start", borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 4 },
  statusLabel: { fontSize: 12, fontWeight: "700" },
  scanLine: { position: "absolute", left: 18, right: 18, height: 2, borderRadius: 2, opacity: 0.85 },
  pulseWrap: { width: 96, height: 96, alignItems: "center", justifyContent: "center", alignSelf: "center" },
  pulse: { position: "absolute", width: 96, height: 96, borderRadius: 48, borderWidth: 3 },
  pulseCore: { width: 18, height: 18, borderRadius: 9 },
  successMark: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: "center",
    justifyContent: "center",
    alignSelf: "center",
  },
  successGlyph: { fontSize: 34, fontWeight: "800" },
});
