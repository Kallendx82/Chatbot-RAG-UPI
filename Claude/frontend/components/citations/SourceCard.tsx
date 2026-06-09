"use client";

import { motion } from "framer-motion";
import { FileText, Globe, ChevronRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { useUIStore } from "@/store/settingsStore";
import type { SourceChunk } from "@/types";
import { cn, scorePercent } from "@/lib/utils";

/**
 * A compact, clickable citation card. Clicking opens the SourceInspector drawer
 * with the full chunk text + metadata. Designed to read at a glance: title,
 * page, category, and a score chip.
 */
export function SourceCard({
  source,
  index,
}: {
  source: SourceChunk;
  index: number;
}) {
  const inspectSource = useUIStore((s) => s.inspectSource);
  const isWeb = source.source_type === "html" || !!source.url;

  return (
    <motion.button
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.2 }}
      onClick={() => inspectSource(source)}
      className={cn(
        "group flex w-full items-start gap-3 rounded-lg border border-border bg-surface px-3 py-2.5 text-left transition-colors hover:border-accent/50 hover:bg-surface-muted",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
      )}
    >
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent/15 text-accent-foreground">
        {isWeb ? <Globe className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-foreground">
            {source.title}
          </span>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <Badge variant="accent" className="font-mono">
            {scorePercent(source.score)}
          </Badge>
          {source.category && (
            <Badge variant="muted">{source.category}</Badge>
          )}
          {source.page != null && (
            <span className="text-xs text-muted-foreground">
              hal. {source.page}
            </span>
          )}
        </div>
        <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
          {source.text}
        </p>
      </div>

      <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
    </motion.button>
  );
}
