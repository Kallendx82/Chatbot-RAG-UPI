import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes with conflict resolution (shadcn/ui convention). */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Generate a reasonably unique id without pulling in a uuid dependency. */
export function uid(prefix = ""): string {
  const rand = Math.random().toString(36).slice(2, 10);
  const time = Date.now().toString(36);
  return `${prefix}${time}${rand}`;
}

/** Format a unix-ms timestamp as a short, locale-aware time. */
export function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Relative day grouping label for the sidebar (Today / Yesterday / date). */
export function dayGroup(ts: number): string {
  const d = new Date(ts);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 86_400_000;
  if (ts >= startOfToday) return "Hari ini";
  if (ts >= startOfYesterday) return "Kemarin";
  return d.toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" });
}

/** Clamp a number into [min, max]. */
export function clamp(n: number, min: number, max: number): number {
  return Math.min(Math.max(n, min), max);
}

/** Derive a conversation title from the first user message. */
export function deriveTitle(text: string, max = 48): string {
  const clean = text.trim().replace(/\s+/g, " ");
  if (clean.length <= max) return clean || "Percakapan baru";
  return clean.slice(0, max).trimEnd() + "…";
}

/** Score -> percent label for citation chips. */
export function scorePercent(score: number): string {
  return `${Math.round(clamp(score, 0, 1) * 100)}%`;
}
