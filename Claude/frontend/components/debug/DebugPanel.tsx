"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bug,
  Clock,
  Cpu,
  Database,
  Loader2,
  Play,
  Search,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/services/api";
import { useSettingsStore, useUIStore } from "@/store/settingsStore";
import { ApiError, type RetrievalDebugResponse } from "@/types";
import { scorePercent } from "@/lib/utils";

/**
 * Retrieval debugging panel - a thesis-demonstration tool.
 *
 * Calls GET /api/retrieve/debug and shows: retrieved chunks with cosine
 * similarity, per-stage latency (embedding / search / total), index size,
 * embedding model, and the EXACT grounded prompt the backend would send to the
 * LLM. This is the explainability surface for hallucination-reduction claims.
 */
export function DebugPanel() {
  const open = useUIStore((s) => s.debugPanelOpen);
  const setOpen = useUIStore((s) => s.setDebugPanelOpen);
  const topK = useSettingsStore((s) => s.topK);
  const language = useSettingsStore((s) => s.language);

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<RetrievalDebugResponse | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);

  const run = async () => {
    const q = query.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.retrieveDebug(q, topK, undefined, language);
      setData(res);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Gagal menjalankan retrieval.",
      );
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
          />
          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 z-50 flex h-full w-full max-w-xl flex-col border-l border-teal/40 bg-surface shadow-2xl"
          >
            <header className="flex items-center justify-between gap-3 border-b border-border bg-teal/5 p-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal/15 text-teal">
                  <Bug className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-serif text-base font-semibold leading-tight">
                    Retrieval Debug
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Inspeksi retrieval untuk evaluasi tesis
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setOpen(false)}
                aria-label="Tutup"
              >
                <X className="h-4 w-4" />
              </Button>
            </header>

            {/* Query bar */}
            <div className="flex items-center gap-2 border-b border-border p-4">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && run()}
                  placeholder="Masukkan query untuk diuji…"
                  className="pl-9"
                />
              </div>
              <Button onClick={run} disabled={loading || !query.trim()}>
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                Jalankan
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
              {error && (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </div>
              )}

              {!data && !error && !loading && (
                <div className="flex flex-col items-center justify-center py-16 text-center text-sm text-muted-foreground">
                  <Bug className="mb-3 h-8 w-8 opacity-40" />
                  Masukkan query lalu jalankan untuk melihat chunk yang diambil,
                  skor kemiripan, latensi, dan pratinjau prompt.
                </div>
              )}

              {data && (
                <div className="space-y-4">
                  {/* Metric tiles */}
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    <MetricTile
                      icon={<Clock className="h-3.5 w-3.5" />}
                      label="Embedding"
                      value={`${data.embedding_latency_ms.toFixed(1)}ms`}
                    />
                    <MetricTile
                      icon={<Search className="h-3.5 w-3.5" />}
                      label="Search"
                      value={`${data.search_latency_ms.toFixed(1)}ms`}
                    />
                    <MetricTile
                      icon={<Clock className="h-3.5 w-3.5" />}
                      label="Total"
                      value={`${data.total_latency_ms.toFixed(1)}ms`}
                    />
                    <MetricTile
                      icon={<Database className="h-3.5 w-3.5" />}
                      label="Index"
                      value={data.index_size.toLocaleString()}
                    />
                  </div>

                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <Badge variant="teal" className="gap-1">
                      <Cpu className="h-3 w-3" />
                      {data.embedding_model}
                    </Badge>
                    <Badge variant="outline">top_k = {data.top_k}</Badge>
                    <Badge variant="outline">
                      threshold = {data.score_threshold}
                    </Badge>
                    <Badge variant="outline">
                      e5 prefix: {data.use_e5_prefixes ? "ya" : "tidak"}
                    </Badge>
                  </div>

                  {/* Prompt preview */}
                  <div className="rounded-lg border border-border">
                    <button
                      onClick={() => setShowPrompt((v) => !v)}
                      className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium hover:bg-surface-muted"
                    >
                      Pratinjau prompt (grounded)
                      <Badge variant="muted">
                        {showPrompt ? "sembunyikan" : "tampilkan"}
                      </Badge>
                    </button>
                    {showPrompt && (
                      <pre className="max-h-64 overflow-auto whitespace-pre-wrap border-t border-border bg-surface-muted/40 p-3 font-mono text-[12px] leading-5 scrollbar-thin">
                        {data.prompt_preview}
                      </pre>
                    )}
                  </div>

                  {/* Retrieved chunks */}
                  <div>
                    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Chunk diambil ({data.n_results})
                    </p>
                    <div className="space-y-2">
                      {data.results.map((r) => (
                        <div
                          key={r.chunk_id}
                          className="rounded-lg border border-border bg-surface p-3"
                        >
                          <div className="mb-1.5 flex items-center justify-between gap-2">
                            <span className="truncate text-sm font-medium">
                              #{r.rank} {r.title}
                            </span>
                            <Badge variant="teal" className="shrink-0 font-mono">
                              {scorePercent(r.score)}
                            </Badge>
                          </div>
                          <div className="mb-2 flex flex-wrap gap-1.5 text-xs text-muted-foreground">
                            {r.category && (
                              <Badge variant="muted">{r.category}</Badge>
                            )}
                            {r.page != null && <span>hal. {r.page}</span>}
                            <span className="font-mono">{r.chunk_id}</span>
                          </div>
                          <p className="text-xs leading-relaxed text-foreground/90">
                            {r.text}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function MetricTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface-muted/40 p-2.5">
      <div className="mb-1 flex items-center gap-1 text-xs text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="font-mono text-sm font-semibold">{value}</div>
    </div>
  );
}
