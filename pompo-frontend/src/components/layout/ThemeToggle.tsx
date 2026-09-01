"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import { IconButton } from "@/components/ui/IconButton";

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Avoid a hydration mismatch: the server can't know the persisted theme.
  // This is next-themes' own documented pattern -- synchronizing with a
  // real external system (the browser's localStorage-backed theme) is
  // exactly what useEffect is for, so this one is a deliberate exception.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="h-9 w-9" />;

  const nextTheme = theme === "system" ? "light" : theme === "light" ? "dark" : "system";
  const label =
    theme === "system"
      ? `Theme follows system (${resolvedTheme ?? "light"}). Switch to light`
      : theme === "light"
        ? "Switch to dark mode"
        : "Follow system theme";

  return (
    <IconButton aria-label={label} title={label} onClick={() => setTheme(nextTheme)}>
      {theme === "system" ? (
        <Monitor className="h-4 w-4" />
      ) : resolvedTheme === "dark" ? (
        <Moon className="h-4 w-4" />
      ) : (
        <Sun className="h-4 w-4" />
      )}
    </IconButton>
  );
}
