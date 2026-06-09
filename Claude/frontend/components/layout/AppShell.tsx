"use client";

import { AnimatePresence, motion } from "framer-motion";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { DebugPanel } from "@/components/debug/DebugPanel";
import { SettingsModal } from "@/components/settings/SettingsModal";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { SourceInspector } from "@/components/citations/SourceInspector";
import { TopBar } from "@/components/layout/TopBar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useMounted } from "@/hooks/useMounted";
import { useUIStore } from "@/store/settingsStore";

/**
 * Top-level application shell.
 *
 * Layout: collapsible sidebar (overlay on mobile via responsive widths) +
 * main column (top bar + chat). Slide-over panels (source inspector, debug)
 * and the settings modal mount here so they overlay everything.
 *
 * Gated on `useMounted` so the localStorage-backed stores hydrate on the client
 * before first paint, preventing hydration mismatches.
 */
export function AppShell() {
  const mounted = useMounted();
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setSidebar = useUIStore((s) => s.setSidebar);

  if (!mounted) {
    // Minimal skeleton during hydration - avoids SSR/client store mismatch.
    return (
      <div className="flex h-dvh items-center justify-center bg-background">
        <div className="h-8 w-8 animate-pulse rounded-lg bg-surface-muted" />
      </div>
    );
  }

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex h-dvh overflow-hidden bg-background paper-grain">
        {/* Sidebar: inline on lg+, overlay on small screens */}
        <AnimatePresence>
          {sidebarOpen && (
            <>
              {/* Mobile scrim */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setSidebar(false)}
                className="fixed inset-0 z-30 bg-black/40 lg:hidden"
              />
              <motion.div
                initial={{ x: -288 }}
                animate={{ x: 0 }}
                exit={{ x: -288 }}
                transition={{ type: "spring", damping: 30, stiffness: 320 }}
                className="fixed z-40 h-full lg:relative lg:z-auto"
              >
                <Sidebar />
              </motion.div>
            </>
          )}
        </AnimatePresence>

        {/* Main column */}
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <main className="min-h-0 flex-1">
            <ChatPanel />
          </main>
        </div>

        {/* Overlays */}
        <SourceInspector />
        <DebugPanel />
        <SettingsModal />
      </div>
    </TooltipProvider>
  );
}
