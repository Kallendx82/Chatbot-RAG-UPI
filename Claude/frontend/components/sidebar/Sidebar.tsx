"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Check,
  GraduationCap,
  MessageSquarePlus,
  PanelLeftClose,
  Pencil,
  Search,
  Settings,
  Trash2,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useConversationStore } from "@/store/conversationStore";
import { useUIStore } from "@/store/settingsStore";
import type { Conversation } from "@/types";
import { cn, dayGroup } from "@/lib/utils";

export function Sidebar() {
  const {
    conversations,
    activeId,
    newConversation,
    setActive,
    deleteConversation,
    renameConversation,
  } = useConversationStore();
  const setSidebar = useUIStore((s) => s.setSidebar);
  const setSettingsOpen = useUIStore((s) => s.setSettingsOpen);

  const [query, setQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  // Filter + group conversations by day for a scannable history list.
  const groups = useMemo(() => {
    const filtered = conversations.filter((c) =>
      c.title.toLowerCase().includes(query.toLowerCase()),
    );
    const byGroup = new Map<string, Conversation[]>();
    for (const c of filtered) {
      const g = dayGroup(c.updatedAt);
      if (!byGroup.has(g)) byGroup.set(g, []);
      byGroup.get(g)!.push(c);
    }
    return Array.from(byGroup.entries());
  }, [conversations, query]);

  const startEdit = (c: Conversation) => {
    setEditingId(c.id);
    setEditValue(c.title);
  };
  const commitEdit = () => {
    if (editingId) renameConversation(editingId, editValue);
    setEditingId(null);
  };

  return (
    <div className="flex h-full w-72 flex-col border-r border-border bg-surface-muted/40">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 p-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <GraduationCap className="h-4 w-4" />
          </div>
          <span className="font-serif text-sm font-semibold leading-tight">
            UPI&nbsp;RAG
            <span className="block text-[10px] font-normal text-muted-foreground">
              Asisten Informasi
            </span>
          </span>
        </div>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setSidebar(false)}
              aria-label="Tutup sidebar"
            >
              <PanelLeftClose className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Sembunyikan sidebar</TooltipContent>
        </Tooltip>
      </div>

      {/* New chat */}
      <div className="px-3">
        <Button
          variant="default"
          className="w-full justify-start gap-2"
          onClick={() => newConversation()}
        >
          <MessageSquarePlus className="h-4 w-4" />
          Percakapan baru
        </Button>
      </div>

      {/* Search */}
      <div className="relative px-3 py-3">
        <Search className="pointer-events-none absolute left-6 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Cari percakapan…"
          className="pl-8"
        />
      </div>

      {/* History */}
      <div className="flex-1 overflow-y-auto px-2 scrollbar-thin">
        {groups.length === 0 && (
          <p className="px-3 py-6 text-center text-xs text-muted-foreground">
            {query ? "Tidak ada hasil." : "Belum ada percakapan."}
          </p>
        )}
        {groups.map(([group, items]) => (
          <div key={group} className="mb-3">
            <p className="px-2 py-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              {group}
            </p>
            <ul className="space-y-0.5">
              <AnimatePresence initial={false}>
                {items.map((c) => (
                  <motion.li
                    key={c.id}
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    {editingId === c.id ? (
                      <div className="flex items-center gap-1 px-1">
                        <Input
                          autoFocus
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") commitEdit();
                            if (e.key === "Escape") setEditingId(null);
                          }}
                          className="h-8"
                        />
                        <Button variant="ghost" size="icon-sm" onClick={commitEdit}>
                          <Check className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => setEditingId(null)}
                        >
                          <X className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    ) : (
                      <div
                        className={cn(
                          "group flex items-center gap-1 rounded-lg px-2 py-1.5 transition-colors",
                          c.id === activeId
                            ? "bg-surface shadow-sm"
                            : "hover:bg-surface/70",
                        )}
                      >
                        <button
                          onClick={() => setActive(c.id)}
                          className="min-w-0 flex-1 truncate text-left text-sm"
                        >
                          {c.title}
                        </button>
                        <div className="flex shrink-0 items-center opacity-0 transition-opacity group-hover:opacity-100">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => startEdit(c)}
                            aria-label="Ganti nama"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => deleteConversation(c.id)}
                            aria-label="Hapus"
                            className="text-muted-foreground hover:text-destructive"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="border-t border-border p-3">
        <Button
          variant="ghost"
          className="w-full justify-start gap-2"
          onClick={() => setSettingsOpen(true)}
        >
          <Settings className="h-4 w-4" />
          Pengaturan
        </Button>
      </div>
    </div>
  );
}
