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
  glowViolet: "rgba(196, 181, 253, 0.34)",
  glowWarm: "rgba(253, 186, 116, 0.18)",
  glowPrimary: "rgba(37, 99, 235, 0.22)",
};

export const space = {
  xs: 6,
  sm: 10,
  md: 16,
  lg: 24,
  xl: 32,
};

export const radius = {
  sm: 14,
  md: 20,
  lg: 28,
  xl: 36,
  pill: 999,
};

export function getTheme(scheme: ThemeName) {
  if (scheme === "dark") {
    return {
      scheme: "dark" as const,
      background: "#000000",
      surface: "#0f172a",
      surfaceRaised: "#1e293b",
      sheet: "#0b1220",
      border: "rgba(148, 163, 184, 0.18)",
      glassBorder: "rgba(147, 197, 253, 0.22)",
      glassFill: "rgba(15, 23, 42, 0.72)",
      glassSolid: "rgba(15, 23, 42, 0.92)",
      text: "#f1f5f9",
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
      glowA: "rgba(59, 130, 246, 0.28)",
      glowB: "rgba(99, 102, 241, 0.18)",
      glowC: "rgba(15, 23, 42, 0.9)",
      shadow: "rgba(0, 0, 0, 0.45)",
    };
  }
  return {
    scheme: "light" as const,
    background: "#f3f5fb",
    surface: "#ffffff",
    surfaceRaised: "#f8fafc",
    sheet: "#ffffff",
    border: "#e2e8f0",
    glassBorder: "rgba(255, 255, 255, 0.72)",
    glassFill: "rgba(255, 255, 255, 0.58)",
    glassSolid: "rgba(255, 255, 255, 0.92)",
    text: "#0f172a",
    muted: "#334155",
    subtle: "#64748b",
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
    shadow: "rgba(15, 23, 42, 0.16)",
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
