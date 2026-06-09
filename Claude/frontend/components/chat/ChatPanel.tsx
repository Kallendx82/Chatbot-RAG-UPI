"use client";

import { useEffect, useRef } from "react";

import { ChatInput } from "@/components/chat/ChatInput";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { WelcomeScreen } from "@/components/chat/WelcomeScreen";
import { useChat } from "@/hooks/useChat";
import { useHealth } from "@/hooks/useHealth";
import { useConversationStore } from "@/store/conversationStore";

/**
 * The central chat column: welcome screen when empty, otherwise the message
 * stream with auto-scroll, plus the composer pinned to the bottom.
 */
export function ChatPanel() {
  const active = useConversationStore((s) =>
    s.conversations.find((c) => c.id === s.activeId),
  );
  const { send, stop, retry, isSending } = useChat();
  const { state } = useHealth();

  const scrollRef = useRef<HTMLDivElement>(null);
  const messages = active?.messages ?? [];
  const lastContent = messages[messages.length - 1]?.content ?? "";

  // Auto-scroll to the newest message as content streams in.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length, lastContent]);

  const offline = state === "offline";
  const degraded = state === "degraded";

  return (
    <div className="flex h-full flex-col">
      {messages.length === 0 ? (
        <WelcomeScreen onPick={send} />
      ) : (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto scrollbar-thin"
        >
          <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6">
            {messages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                onRetry={m.role === "assistant" ? retry : undefined}
              />
            ))}
          </div>
        </div>
      )}

      {(offline || degraded) && (
        <div className="mx-auto mb-2 w-full max-w-3xl px-4">
          <div
            className={`rounded-lg border px-3 py-2 text-xs ${
              offline
                ? "border-destructive/30 bg-destructive/10 text-destructive"
                : "border-accent/40 bg-accent/10 text-accent-foreground"
            }`}
          >
            {offline
              ? "Tidak dapat terhubung ke server backend. Periksa apakah FastAPI berjalan di port 8000."
              : "Backend aktif namun pipeline RAG belum siap (indeks vektor belum dimuat). Periksa konfigurasi indeks FAISS."}
          </div>
        </div>
      )}

      <ChatInput
        onSend={send}
        onStop={stop}
        isSending={isSending}
        disabled={offline}
        disabledReason="Server tidak tersedia"
      />
    </div>
  );
}
