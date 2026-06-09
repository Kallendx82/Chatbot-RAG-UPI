"use client";

import * as React from "react";

import { useSettingsStore } from "@/store/settingsStore";

/**
 * Theme controller.
 *
 * Reads the persisted theme setting ("light" | "dark" | "system") and applies
 * the `.dark` class to <html>. For "system" it follows the OS preference and
 * updates live when that changes. Renders nothing.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useSettingsStore((s) => s.theme);

  React.useEffect(() => {
    const root = document.documentElement;
    const media = window.matchMedia("(prefers-color-scheme: dark)");

    const apply = () => {
      const dark = theme === "dark" || (theme === "system" && media.matches);
      root.classList.toggle("dark", dark);
    };

    apply();
    if (theme === "system") {
      media.addEventListener("change", apply);
      return () => media.removeEventListener("change", apply);
    }
  }, [theme]);

  return <>{children}</>;
}
