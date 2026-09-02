import { Appearance } from "react-native";

export type ThemeName = "light" | "dark";

export const palette = {
  primary: "#2563eb",
  primaryHover: "#1d4ed8",
  darkBlue: "#0b2545",
  success: "#047857",
  successBg: "#ecfdf5",
  error: "#b91c1c",
  errorBg: "#fef2f2",
  warning: "#b45309",
};

export function getTheme(scheme: ThemeName) {
  if (scheme === "dark") {
    return {
      background: "#000000",
      surface: "#0f172a",
      surfaceRaised: "#1e293b",
      border: "#1e293b",
      text: "#f8fafc",
      muted: "#94a3b8",
      subtle: "#64748b",
      primary: "#93c5fd",
      primaryForeground: "#020617",
      darkBlue: "#0f172a",
      success: "#34d399",
      successBg: "#052e1c",
      error: "#fca5a5",
      errorBg: "#3f1010",
    };
  }
  return {
    background: "#f8fafc",
    surface: "#ffffff",
    surfaceRaised: "#f1f5f9",
    border: "#e2e8f0",
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
  };
}

export type Theme = ReturnType<typeof getTheme>;

export function currentScheme(): ThemeName {
  return Appearance.getColorScheme() === "dark" ? "dark" : "light";
}
