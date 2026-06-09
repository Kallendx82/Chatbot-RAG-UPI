"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Check,
  Copy,
  GraduationCap,
  RefreshCw,
  ShieldCheck,
  ShieldAlert,
  Timer,
  User,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { MarkdownMessage } from "@/components/chat/MarkdownMessage";
import { SourceList } from "@/components/citations/SourceInspector";
import { useSettingsStore } from "@/store/settingsStore";
import type { ChatMessage } from "@/types";
import { cn } from "@/lib/utils";

export function MessageBubble({
  message,
  onRetry,
}: {
  message: ChatMessage;
  onRetry?: (m: ChatMessage) => void;
}) {
  const isUser = message.role === "user";
  const debugMode = useSettingsStore((s) => s.debugMode);
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}
    >
      {/* Avatar */}
      <div
        className={cn(
          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-accent/15 text-accent-foreground",
        )}
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : (
          <GraduationCap className="h-4 w-4" />
        )}
      </div>

      {/* Body */}
      <div className={cn("min-w-0 max-w-[min(46rem,85%)]", isUser && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3",
            isUser
              ? "bg-primary text-primary-foreground"
              : "border border-border bg-surface",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap text-[15px] leading-7">
              {message.content}
            </p>
          ) : message.status === "error" ? (
            <div className="flex items-start gap-2 text-sm text-destructive">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{message.error || "Gagal memuat jawaban."}</span>
            </div>
          ) : message.status === "streaming" && !message.content ? (
            <TypingDots />
          ) : (
            <>
              <MarkdownMessage content={message.content} />
              {message.status === "streaming" && (
                <span className="ml-0.5 inline-block h-4 w-[2px] animate-blink bg-accent align-middle" />
              )}
            </>
          )}
        </div>

        {/* Assistant: grounding badge + metrics + actions + sources */}
        {!isUser && message.status === "complete" && (
          <div className="mt-2 w-full">
            <div className="flex flex-wrap items-center gap-2">
              {message.metrics && (
                <>
                  {message.metrics.grounded ? (
                    <Badge variant="teal" className="gap-1">
                      <ShieldCheck className="h-3 w-3" />
                      Terverifikasi sumber
                    </Badge>
                  ) : (
                    <Badge variant="muted" className="gap-1">
                      <ShieldAlert className="h-3 w-3" />
                      Tanpa sumber
                    </Badge>
                  )}
                  {debugMode && (
                    <Badge variant="outline" className="gap-1 font-mono">
                      <Timer className="h-3 w-3" />
                      {Math.round(message.metrics.totalMs)}ms
                    </Badge>
                  )}
                  {debugMode && (
                    <Badge variant="outline" className="font-mono">
                      {message.metrics.backend}
                    </Badge>
                  )}
                </>
              )}

              <div className="ml-auto flex items-center gap-1">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon-sm" onClick={copy}>
                      {copied ? (
                        <Check className="h-3.5 w-3.5" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Salin jawaban</TooltipContent>
                </Tooltip>
                {onRetry && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => onRetry(message)}
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Hasilkan ulang</TooltipContent>
                  </Tooltip>
                )}
              </div>
            </div>

            {message.sources && <SourceList sources={message.sources} />}
          </div>
        )}

        {/* Error retry */}
        {!isUser && message.status === "error" && onRetry && (
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => onRetry(message)}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Coba lagi
          </Button>
        )}
      </div>
    </motion.div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-2 w-2 rounded-full bg-muted-foreground/60"
          style={{
            animation: "blink 1.2s ease-in-out infinite",
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
    </div>
  );
}
