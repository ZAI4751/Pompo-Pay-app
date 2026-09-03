import { useEffect, useState } from "react";
import { Appearance } from "react-native";

export type ThemeName = "light" | "dark";

/** POMPO brand — same tokens as Master Admin `globals.css`. */
export const palette = {
  primary: "#2563eb",
  primaryHover: "#1d4ed8",
  primaryLight: "#eff6ff",
  darkBlue: "#0b2545",
  darkBlueBrand: "#0b468d",
  success: "#047857",
  successBg: "#ecfdf5",
  error: "#b91c1c",
  errorBg: "#fef2f2",
  warning: "#b45309",
  warningBg: "#fffbeb",
  glowViolet: "rgba(196, 181, 253, 0.16)",
  glowWarm: "rgba(253, 186, 116, 0.10)",
  glowPrimary: "rgba(37, 99, 235, 0.12)",
};

export const space = {
  xs: 6,
  sm: 10,
  md: 16,
  lg: 24,
  xl: 32,
};

export const radius = {
  sm: 12,
  md: 16,
  lg: 24,
  xl: 28,
  pill: 999,
};

export const heroGradient = {
  light: ["#1d4ed8", "#2563eb", "#0b468d"] as const,
  dark: ["#1e3a8a", "#1d4ed8", "#0b2545"] as const,
};

export function getTheme(scheme: ThemeName) {
  if (scheme === "dark") {
    return {
      scheme: "dark" as const,
      background: "#020617",
      surface: "#0f172a",
      surfaceRaised: "#1e293b",
      sheet: "#0f172a",
      border: "rgba(148, 163, 184, 0.16)",
      glassBorder: "rgba(147, 197, 253, 0.18)",
      glassFill: "rgba(15, 23, 42, 0.78)",
      glassSolid: "rgba(15, 23, 42, 0.94)",
      text: "#f8fafc",
      muted: "#94a3b8",
      subtle: "#64748b",
      primary: "#93c5fd",
      primaryForeground: "#020617",
      darkBlue: "#93c5fd",
      success: "#34d399",
      successBg: "#052e1c",
      error: "#fca5a5",
      errorBg: "#3f1010",
      warning: "#fbbf24",
      warningBg: "#3b2a05",
      glowA: "rgba(59, 130, 246, 0.22)",
      glowB: "rgba(99, 102, 241, 0.12)",
      glowC: "rgba(15, 23, 42, 0.9)",
      shadow: "rgba(0, 0, 0, 0.45)",
      navFill: "rgba(15, 23, 42, 0.88)",
    };
  }
  return {
    scheme: "light" as const,
    background: "#f8fafc",
    surface: "#ffffff",
    surfaceRaised: "#f8fafc",
    sheet: "#ffffff",
    border: "#f1f5f9",
    glassBorder: "rgba(226, 232, 240, 0.9)",
    glassFill: "rgba(255, 255, 255, 0.82)",
    glassSolid: "rgba(255, 255, 255, 0.94)",
    text: "#0f172a",
    muted: "#64748b",
    subtle: "#94a3b8",
    primary: palette.primary,
    primaryForeground: "#ffffff",
    darkBlue: palette.darkBlue,
    success: palette.success,
    successBg: palette.successBg,
    error: palette.error,
    errorBg: palette.errorBg,
    warning: palette.warning,
    glowA: palette.glowPrimary,
    glowB: palette.glowViolet,
    glowC: palette.glowWarm,
    shadow: "rgba(15, 23, 42, 0.10)",
    navFill: "rgba(255, 255, 255, 0.88)",
  };
}

export type Theme = ReturnType<typeof getTheme>;

export function currentScheme(): ThemeName {
  return Appearance.getColorScheme() === "dark" ? "dark" : "light";
}

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
