import { useEffect, useState, type ReactNode } from "react";
import { LinearGradient } from "expo-linear-gradient";
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

import { duration, pressIn, pressOut, slideUp } from "@/motion";
import { heroGradient, radius, space, useTheme } from "@/theme";

export function Atmosphere({ children }: { children?: ReactNode }) {
  const theme = useTheme();
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <View style={[styles.glow, styles.glowA, { backgroundColor: theme.glowA }]} />
      <View style={[styles.glow, styles.glowB, { backgroundColor: theme.glowB }]} />
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

export function HeroCard({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  const theme = useTheme();
  return (
    <LinearGradient
      colors={theme.scheme === "dark" ? heroGradient.dark : heroGradient.light}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={[styles.hero, style]}
    >
      <View style={styles.heroOrbA} />
      <View style={styles.heroOrbB} />
      <View style={styles.heroBody}>{children}</View>
    </LinearGradient>
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

export function CircleButton({
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
        styles.circle,
        { backgroundColor: theme.surface, borderColor: theme.border, shadowColor: theme.shadow },
      ]}
    >
      {children}
    </View>
  );
  if (!onPress) {
    return inner;
  }
  return (
    <PressScale accessibilityRole="button" accessibilityLabel={accessibilityLabel} onPress={onPress} hitSlop={8}>
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

export function InitialsAvatar({
  name,
  size = 40,
  active = false,
}: {
  name: string;
  size?: number;
  active?: boolean;
}) {
  const theme = useTheme();
  const letters = name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: active ? theme.primary : theme.scheme === "dark" ? "#1e293b" : "#e2e8f0",
      }}
    >
      <Text
        style={{
          color: active ? theme.primaryForeground : theme.muted,
          fontSize: size * 0.34,
          fontWeight: "800",
        }}
      >
        {letters || "P"}
      </Text>
    </View>
  );
}

export function IconWell({
  children,
  background,
  size = 40,
}: {
  children: ReactNode;
  background: string;
  size?: number;
}) {
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: 12,
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: background,
      }}
    >
      {children}
    </View>
  );
}

export function FadeIn({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  const [opacity] = useState(() => new Animated.Value(0));
  const [translate] = useState(() => new Animated.Value(14));
  useEffect(() => {
    const timer = setTimeout(() => {
      slideUp(opacity, translate);
    }, delay);
    return () => clearTimeout(timer);
  }, [delay, opacity, translate]);
  return <Animated.View style={{ opacity, transform: [{ translateY: translate }] }}>{children}</Animated.View>;
}

export function ScanFrame() {
  const theme = useTheme();
  const color = theme.scheme === "dark" ? "#93c5fd" : "#ffffff";
  return (
    <View pointerEvents="none" style={styles.scanFrame}>
      <View style={[styles.corner, styles.cornerTL, { borderColor: color }]} />
      <View style={[styles.corner, styles.cornerTR, { borderColor: color }]} />
      <View style={[styles.corner, styles.cornerBL, { borderColor: color }]} />
      <View style={[styles.corner, styles.cornerBR, { borderColor: color }]} />
    </View>
  );
}

export function ScanLine() {
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
  const translateY = y.interpolate({ inputRange: [0, 1], outputRange: [28, 196] });
  return (
    <Animated.View
      pointerEvents="none"
      style={[styles.scanLine, { transform: [{ translateY }] }]}
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
  const [glow] = useState(() => new Animated.Value(0.2));
  useEffect(() => {
    Animated.parallel([
      Animated.spring(scale, { toValue: 1, friction: 6, tension: 80, useNativeDriver: true }),
      Animated.timing(opacity, { toValue: 1, duration: duration.component, useNativeDriver: true }),
      Animated.timing(glow, { toValue: 1, duration: duration.screen, useNativeDriver: true }),
    ]).start();
  }, [glow, opacity, scale]);
  return (
    <View style={styles.successWrap}>
      <Animated.View
        style={[
          styles.successGlow,
          { backgroundColor: theme.success, opacity: glow.interpolate({ inputRange: [0, 1], outputRange: [0.08, 0.18] }) },
        ]}
      />
      <Animated.View
        style={[
          styles.successMark,
          { backgroundColor: theme.successBg, opacity, transform: [{ scale }] },
        ]}
      >
        <Text style={[styles.successGlyph, { color: theme.success }]}>✓</Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  glow: { position: "absolute", borderRadius: 999 },
  glowA: { width: 280, height: 280, top: -140, left: -90 },
  glowB: { width: 220, height: 220, top: -60, right: -80 },
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
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 1,
    shadowRadius: 18,
    elevation: 3,
  },
  hero: {
    borderRadius: radius.xl,
    overflow: "hidden",
    minHeight: 168,
    shadowColor: "#1d4ed8",
    shadowOffset: { width: 0, height: 14 },
    shadowOpacity: 0.28,
    shadowRadius: 24,
    elevation: 8,
  },
  heroOrbA: {
    position: "absolute",
    width: 128,
    height: 128,
    borderRadius: 64,
    backgroundColor: "rgba(255,255,255,0.12)",
    right: -32,
    top: -32,
  },
  heroOrbB: {
    position: "absolute",
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "rgba(255,255,255,0.08)",
    right: -8,
    top: 56,
  },
  heroBody: { padding: 20, minHeight: 168, justifyContent: "space-between" },
  pill: {
    alignSelf: "flex-start",
    borderRadius: radius.pill,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  pillLabel: { fontSize: 13, fontWeight: "600" },
  circle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 8,
    elevation: 2,
  },
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
  scanFrame: { position: "absolute", top: 36, right: 36, bottom: 36, left: 36 },
  corner: { position: "absolute", width: 28, height: 28 },
  cornerTL: { top: 0, left: 0, borderTopWidth: 3, borderLeftWidth: 3, borderTopLeftRadius: 8 },
  cornerTR: { top: 0, right: 0, borderTopWidth: 3, borderRightWidth: 3, borderTopRightRadius: 8 },
  cornerBL: { bottom: 0, left: 0, borderBottomWidth: 3, borderLeftWidth: 3, borderBottomLeftRadius: 8 },
  cornerBR: { bottom: 0, right: 0, borderBottomWidth: 3, borderRightWidth: 3, borderBottomRightRadius: 8 },
  scanLine: {
    position: "absolute",
    left: 52,
    right: 52,
    height: 2,
    borderRadius: 2,
    backgroundColor: "rgba(255,255,255,0.92)",
    shadowColor: "#93c5fd",
    shadowOpacity: 0.9,
    shadowRadius: 8,
    elevation: 4,
  },
  pulseWrap: { width: 96, height: 96, alignItems: "center", justifyContent: "center", alignSelf: "center" },
  pulse: { position: "absolute", width: 96, height: 96, borderRadius: 48, borderWidth: 3 },
  pulseCore: { width: 18, height: 18, borderRadius: 9 },
  successWrap: { width: 112, height: 112, alignItems: "center", justifyContent: "center", alignSelf: "center" },
  successGlow: { position: "absolute", width: 112, height: 112, borderRadius: 56 },
  successMark: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: "center",
    justifyContent: "center",
  },
  successGlyph: { fontSize: 34, fontWeight: "800" },
});
