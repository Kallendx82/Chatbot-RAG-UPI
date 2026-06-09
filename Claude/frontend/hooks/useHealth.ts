/**
 * useHealth - polls the backend /health endpoint so the UI can show an
 * online/degraded/offline indicator and disable input when the RAG pipeline
 * is not ready.
 */
"use client";

import { useEffect, useState } from "react";

import { api } from "@/services/api";
import type { HealthResponse } from "@/types";

export type ConnectionState = "checking" | "online" | "degraded" | "offline";

export function useHealth(pollMs = 30_000) {
  const [state, setState] = useState<ConnectionState>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const h = await api.health();
        if (cancelled) return;
        setHealth(h);
        setState(h.status === "ok" ? "online" : "degraded");
      } catch {
        if (cancelled) return;
        setHealth(null);
        setState("offline");
      }
    };

    check();
    const id = setInterval(check, pollMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [pollMs]);

  return { state, health };
}
