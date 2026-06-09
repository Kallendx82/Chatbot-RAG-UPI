/**
 * useChat - orchestrates sending a message and rendering the response.
 *
 * STREAMING-CAPABLE ARCHITECTURE:
 * The backend has no SSE endpoint yet (deferred to a later slice). To make the
 * UI feel like a streaming chat today AND make the future swap trivial, this
 * hook treats answer rendering as a stream of deltas:
 *
 *   1. add user message + assistant placeholder (status "streaming")
 *   2. await the /api/chat response (full answer + sources + metrics)
 *   3. animate the answer into the placeholder token-by-token via appendToMessage
 *   4. finalize with sources + metrics (status "complete")
 *
 * When /api/chat/stream lands, replace step 2-3 with a real reader that calls
 * appendToMessage on each delta as it arrives. Steps 1 and 4 stay identical, so
 * no component changes are needed.
 */
"use client";

import { useCallback, useRef, useState } from "react";

import { fetchChat } from "@/services/api";
import { useConversationStore } from "@/store/conversationStore";
import { useSettingsStore } from "@/store/settingsStore";
import { ApiError, type ChatMessage } from "@/types";

/** Animate text into the store as if streamed. Resolves when fully written. */
async function animateInto(
  text: string,
  onDelta: (delta: string) => void,
  signal: AbortSignal,
) {
  // Chunk by words for a natural cadence; keep it quick for long answers.
  const tokens = text.match(/\S+\s*/g) ?? [text];
  const perTick = tokens.length > 120 ? 3 : 1;
  for (let i = 0; i < tokens.length; i += perTick) {
    if (signal.aborted) return;
    onDelta(tokens.slice(i, i + perTick).join(""));
    // ~14ms/word feels responsive without being instant.
    await new Promise((r) => setTimeout(r, 14 * perTick));
  }
}

export function useChat() {
  const [isSending, setIsSending] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const {
    getActive,
    newConversation,
    addUserMessage,
    addAssistantPlaceholder,
    appendToMessage,
    finalizeAssistantMessage,
    setMessageError,
    removeMessage,
  } = useConversationStore();

  const send = useCallback(
    async (rawText: string) => {
      const text = rawText.trim();
      if (!text || isSending) return;

      // Ensure there is an active conversation.
      let convId = getActive()?.id;
      if (!convId) convId = newConversation();

      setIsSending(true);
      const abort = new AbortController();
      abortRef.current = abort;

      addUserMessage(convId, text);
      const assistantId = addAssistantPlaceholder(convId);

      const { topK, temperature, language, model } = useSettingsStore.getState();

      try {
        const res = await fetchChat({
          message: text,
          top_k: topK,
          temperature,
          language,
          model,
        });

        // Render progressively, then finalize with the canonical content.
        await animateInto(
          res.answer,
          (delta) => appendToMessage(convId!, assistantId, delta),
          abort.signal,
        );

        finalizeAssistantMessage(convId!, assistantId, {
          content: res.answer,
          sources: res.sources,
          metrics: {
            backend: res.backend,
            grounded: res.grounded,
            retrievalMs: res.retrieval_latency_ms,
            generationMs: res.generation_latency_ms,
            totalMs: res.total_latency_ms,
          },
        });
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : "Terjadi kesalahan tak terduga saat menghubungi server.";
        setMessageError(convId!, assistantId, message);
      } finally {
        setIsSending(false);
        abortRef.current = null;
      }
    },
    [
      isSending,
      getActive,
      newConversation,
      addUserMessage,
      addAssistantPlaceholder,
      appendToMessage,
      finalizeAssistantMessage,
      setMessageError,
    ],
  );

  /** Stop an in-flight render (the animation; network is fire-and-forget here). */
  const stop = useCallback(() => {
    abortRef.current?.abort();
    setIsSending(false);
  }, []);

  /** Retry: drop the failed assistant message, resend the preceding user text. */
  const retry = useCallback(
    async (failedMessage: ChatMessage) => {
      // Snapshot the active conversation BEFORE mutating; retry must stay in
      // the same conversation even if something else (e.g. a stale active id)
      // would otherwise trigger newConversation() inside send().
      const conv = getActive();
      if (!conv) return;
      const idx = conv.messages.findIndex((m) => m.id === failedMessage.id);
      if (idx < 1) return;
      const prevUser = conv.messages[idx - 1];
      if (prevUser?.role !== "user") return;
      // Pin the active id to this conv so send() reuses it (no new chat).
      useConversationStore.getState().setActive(conv.id);
      removeMessage(conv.id, failedMessage.id);
      await send(prevUser.content);
    },
    [getActive, removeMessage, send],
  );

  return { send, stop, retry, isSending };
}
