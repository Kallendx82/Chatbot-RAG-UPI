"use client";

import { AnimatePresence, motion } from "framer-motion";
import { X, FileText, Globe, Hash, Layers, Tag } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SourceCard } from "@/components/citations/SourceCard";
import { useUIStore } from "@/store/settingsStore";
import type { SourceChunk } from "@/types";
import { scorePercent } from "@/lib/utils";

/** The grid of citation cards shown beneath an assistant answer. */
export function SourceList({ sources }: { sources: SourceChunk[] }) {
  if (!sources?.length) return null;
  return (
    <div className="mt-4">
      <div className="mb-2 flex items-center gap-2">
        <Layers className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Sumber ({sources.length})
        </span>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {sources.map((s, i) => (
          <SourceCard key={s.chunk_id || i} source={s} index={i} />
        ))}
      </div>
    </div>
  );
}

/** Slide-over drawer showing the full chunk text + all metadata of one source. */
export function SourceInspector() {
  const inspected = useUIStore((s) => s.inspectedSource);
  const inspectSource = useUIStore((s) => s.inspectSource);

  return (
    <AnimatePresence>
      {inspected && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => inspectSource(null)}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
          />
          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 320 }}
            className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l border-border bg-surface shadow-2xl"
          >
            <header className="flex items-start justify-between gap-3 border-b border-border p-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-accent-foreground">
                  {inspected.url ? (
                    <Globe className="h-5 w-5" />
                  ) : (
                    <FileText className="h-5 w-5" />
                  )}
                </div>
                <div className="min-w-0">
                  <h3 className="font-serif text-base font-semibold leading-tight">
                    {inspected.title}
                  </h3>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Detail sumber retrieval
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => inspectSource(null)}
                aria-label="Tutup"
              >
                <X className="h-4 w-4" />
              </Button>
            </header>

            <div className="flex-1 space-y-4 overflow-y-auto p-4 scrollbar-thin">
              {/* Metadata grid */}
              <div className="grid grid-cols-2 gap-2">
                <Meta icon={<Hash className="h-3.5 w-3.5" />} label="Skor">
                  <Badge variant="accent" className="font-mono">
                    {scorePercent(inspected.score)} ({inspected.score.toFixed(4)})
                  </Badge>
                </Meta>
                <Meta icon={<Layers className="h-3.5 w-3.5" />} label="Peringkat">
                  #{inspected.rank}
                </Meta>
                {inspected.category && (
                  <Meta icon={<Tag className="h-3.5 w-3.5" />} label="Kategori">
                    {inspected.category}
                  </Meta>
                )}
                {inspected.page != null && (
                  <Meta icon={<FileText className="h-3.5 w-3.5" />} label="Halaman">
                    {inspected.page}
                  </Meta>
                )}
              </div>

              <DetailRow label="Chunk ID" value={inspected.chunk_id} mono />
              <DetailRow label="Document ID" value={inspected.doc_id} mono />
              {inspected.section && (
                <DetailRow label="Bagian" value={inspected.section} />
              )}
              {inspected.source_type && (
                <DetailRow label="Tipe sumber" value={inspected.source_type} />
              )}
              {inspected.source && (
                <DetailRow label="Asal" value={inspected.source} mono />
              )}
              {inspected.url && (
                <div>
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    URL
                  </p>
                  <a
                    href={inspected.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="break-all text-sm text-primary underline underline-offset-2 hover:opacity-80"
                  >
                    {inspected.url}
                  </a>
                </div>
              )}

              {/* The retrieved chunk text (the grounded context) */}
              <div>
                <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Konteks yang diambil
                </p>
                <div className="rounded-lg border border-accent/30 bg-accent/5 p-3 text-sm leading-relaxed text-foreground">
                  {inspected.text}
                </div>
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function Meta({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface-muted/50 p-2.5">
      <div className="mb-1 flex items-center gap-1.5 text-xs text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="text-sm font-medium">{children}</div>
    </div>
  );
}

function DetailRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className={`break-all text-sm ${mono ? "font-mono text-[13px]" : ""}`}>
        {value}
      </p>
    </div>
  );
}
