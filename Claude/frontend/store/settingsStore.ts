/**
 * Settings + ephemeral UI state stores.
 *
 * Settings persist to localStorage (top-k, temperature, language, theme, debug).
 * UI store is in-memory only (sidebar open, active panels, modals).
 */
"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { Settings, SourceChunk } from "@/types";

// ---------------------------------------------------------------------------
// Settings store (persisted)
// ---------------------------------------------------------------------------
interface SettingsState extends Settings {
  set: <K extends keyof Settings>(key: K, value: Settings[K]) => void;
  reset: () => void;
}

const DEFAULT_SETTINGS: Settings = {
  topK: 5,
  temperature: 0.1,
  language: "id",
  model: "llama3.1:8b", // informational; backend chooses the real backend
  theme: "system",
  debugMode: false,
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...DEFAULT_SETTINGS,
      set: (key, value) => set({ [key]: value } as Partial<SettingsState>),
      reset: () => set({ ...DEFAULT_SETTINGS }),
    }),
    { name: "upi-rag-settings", version: 1 },
  ),
);

// ---------------------------------------------------------------------------
// UI store (ephemeral)
// ---------------------------------------------------------------------------
interface UIState {
  sidebarOpen: boolean;
  settingsOpen: boolean;
  /** The source chunk currently expanded in the citation drawer, if any. */
  inspectedSource: SourceChunk | null;
  /** Whether the retrieval debug panel is open. */
  debugPanelOpen: boolean;

  toggleSidebar: () => void;
  setSidebar: (open: boolean) => void;
  setSettingsOpen: (open: boolean) => void;
  inspectSource: (s: SourceChunk | null) => void;
  setDebugPanelOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  settingsOpen: false,
  inspectedSource: null,
  debugPanelOpen: false,

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebar: (open) => set({ sidebarOpen: open }),
  setSettingsOpen: (open) => set({ settingsOpen: open }),
  inspectSource: (s) => set({ inspectedSource: s }),
  setDebugPanelOpen: (open) => set({ debugPanelOpen: open }),
}));
