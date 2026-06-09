"use client";

import { Monitor, Moon, RotateCcw, Sun } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSettingsStore, useUIStore } from "@/store/settingsStore";
import type { Language, ThemeMode } from "@/types";
import { cn } from "@/lib/utils";

export function SettingsModal() {
  const open = useUIStore((s) => s.settingsOpen);
  const setOpen = useUIStore((s) => s.setSettingsOpen);

  const settings = useSettingsStore();

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Pengaturan</DialogTitle>
          <DialogDescription>
            Konfigurasi retrieval, model, tampilan, dan bahasa.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-1">
          {/* Theme */}
          <div className="space-y-2">
            <Label>Tema</Label>
            <div className="grid grid-cols-3 gap-2">
              {(
                [
                  { v: "light", icon: Sun, label: "Terang" },
                  { v: "dark", icon: Moon, label: "Gelap" },
                  { v: "system", icon: Monitor, label: "Sistem" },
                ] as { v: ThemeMode; icon: typeof Sun; label: string }[]
              ).map(({ v, icon: Icon, label }) => (
                <button
                  key={v}
                  onClick={() => settings.set("theme", v)}
                  className={cn(
                    "flex flex-col items-center gap-1.5 rounded-lg border p-3 text-xs transition-colors",
                    settings.theme === v
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border hover:bg-surface-muted",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Language */}
          <div className="space-y-2">
            <Label>Bahasa jawaban</Label>
            <Select
              value={settings.language}
              onValueChange={(v) => settings.set("language", v as Language)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="id">Bahasa Indonesia</SelectItem>
                <SelectItem value="en">English</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Top-k */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Top-K retrieval</Label>
              <span className="font-mono text-sm text-muted-foreground">
                {settings.topK}
              </span>
            </div>
            <Slider
              min={1}
              max={20}
              step={1}
              value={[settings.topK]}
              onValueChange={([v]) => settings.set("topK", v)}
            />
            <p className="text-xs text-muted-foreground">
              Jumlah potongan dokumen yang diambil sebagai konteks.
            </p>
          </div>

          {/* Temperature */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Temperature</Label>
              <span className="font-mono text-sm text-muted-foreground">
                {settings.temperature.toFixed(2)}
              </span>
            </div>
            <Slider
              min={0}
              max={1}
              step={0.05}
              value={[settings.temperature]}
              onValueChange={([v]) => settings.set("temperature", v)}
            />
            <p className="text-xs text-muted-foreground">
              Semakin rendah, semakin faktual dan konsisten (disarankan ≤ 0.2).
            </p>
          </div>

          {/* Model label */}
          <div className="space-y-2">
            <Label>Backend model</Label>
            <Select
              value={settings.model}
              onValueChange={(v) => settings.set("model", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="llama3.1:8b">Llama 3.1 8B (default)</SelectItem>
                <SelectItem value="llama3.2:3b">Llama 3.2 3B (cepat, ringan)</SelectItem>
                <SelectItem value="qwen2.5:3b">Qwen 2.5 3B</SelectItem>
                <SelectItem value="qwen3.5:4b">Qwen 3.5 4B (eksperimen)</SelectItem>
                <SelectItem value="extractive">Extractive (tanpa LLM)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Model lokal melalui Ollama. Llama 3.1 8B paling akurat;
              Llama 3.2 3B paling cepat.
            </p>
          </div>

          {/* Debug mode */}
          <div className="flex items-center justify-between rounded-lg border border-border p-3">
            <div>
              <Label>Mode debug</Label>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Tampilkan latensi & backend pada tiap jawaban.
              </p>
            </div>
            <Switch
              checked={settings.debugMode}
              onCheckedChange={(v) => settings.set("debugMode", v)}
            />
          </div>
        </div>

        <div className="flex justify-between border-t border-border pt-4">
          <Button variant="ghost" size="sm" onClick={settings.reset}>
            <RotateCcw className="h-3.5 w-3.5" />
            Atur ulang
          </Button>
          <Button size="sm" onClick={() => setOpen(false)}>
            Selesai
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
