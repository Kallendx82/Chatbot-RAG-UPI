"use client";

import { motion } from "framer-motion";
import { GraduationCap, Search, FileText, Building2, Newspaper } from "lucide-react";

const SUGGESTIONS = [
  {
    icon: Search,
    title: "Layanan PPID",
    prompt: "Apa saja layanan informasi publik yang disediakan PPID UPI?",
  },
  {
    icon: FileText,
    title: "Pendaftaran mahasiswa",
    prompt: "Bagaimana prosedur pendaftaran mahasiswa baru di UPI?",
  },
  {
    icon: Newspaper,
    title: "Penelitian & LPPM",
    prompt: "Apa fokus penelitian dan pengabdian masyarakat LPPM UPI?",
  },
  {
    icon: Building2,
    title: "Fasilitas kampus",
    prompt: "Fasilitas apa saja yang tersedia di kampus UPI?",
  },
];

export function WelcomeScreen({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center px-4 py-10">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col items-center text-center"
      >
        <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg">
          <GraduationCap className="h-8 w-8" />
        </div>
        <h1 className="font-serif text-3xl font-semibold tracking-tight">
          Asisten Informasi UPI
        </h1>
        <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
          Tanyakan informasi seputar Universitas Pendidikan Indonesia. Setiap
          jawaban didukung sumber dokumen resmi yang dapat Anda telusuri.
        </p>
      </motion.div>

      <div className="mt-8 grid w-full gap-3 sm:grid-cols-2">
        {SUGGESTIONS.map((s, i) => (
          <motion.button
            key={s.title}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.06, duration: 0.3 }}
            onClick={() => onPick(s.prompt)}
            className="group flex items-start gap-3 rounded-xl border border-border bg-surface p-4 text-left transition-all hover:border-primary/40 hover:shadow-sm"
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-muted text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
              <s.icon className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium">{s.title}</p>
              <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                {s.prompt}
              </p>
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
