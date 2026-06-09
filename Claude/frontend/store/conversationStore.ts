/**
 * Conversation store (Zustand + persist).
 *
 * Holds all conversations and the active id. Persisted to localStorage so chat
 * history survives reloads WITHOUT a backend (this slice's requirement). The
 * persistence layer is isolated here: when Slice 2 adds server-side history,
 * swap the `persist` storage for API-backed actions and nothing else in the UI
 * needs to change.
 */
"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { ChatMessage, Conversation, SourceChunk } from "@/types";
import { deriveTitle, uid } from "@/lib/utils";

interface ConversationState {
  conversations: Conversation[];
  activeId: string | null;

  // selectors-as-helpers
  getActive: () => Conversation | undefined;

  // mutations
  newConversation: () => string;
  deleteConversation: (id: string) => void;
  renameConversation: (id: string, title: string) => void;
  setActive: (id: string) => void;

  addUserMessage: (conversationId: string, content: string) => string;
  addAssistantPlaceholder: (conversationId: string) => string;
  appendToMessage: (
    conversationId: string,
    messageId: string,
    delta: string,
  ) => void;
  finalizeAssistantMessage: (
    conversationId: string,
    messageId: string,
    payload: {
      content: string;
      sources: SourceChunk[];
      metrics: NonNullable<ChatMessage["metrics"]>;
    },
  ) => void;
  setMessageError: (
    conversationId: string,
    messageId: string,
    error: string,
  ) => void;
  removeMessage: (conversationId: string, messageId: string) => void;
}

function touch(conv: Conversation): Conversation {
  return { ...conv, updatedAt: Date.now() };
}

export const useConversationStore = create<ConversationState>()(
  persist(
    (set, get) => ({
      conversations: [],
      activeId: null,

      getActive: () => {
        const { conversations, activeId } = get();
        return conversations.find((c) => c.id === activeId);
      },

      newConversation: () => {
        const id = uid("conv_");
        const now = Date.now();
        const conv: Conversation = {
          id,
          title: "Percakapan baru",
          messages: [],
          createdAt: now,
          updatedAt: now,
        };
        set((s) => ({
          conversations: [conv, ...s.conversations],
          activeId: id,
        }));
        return id;
      },

      deleteConversation: (id) =>
        set((s) => {
          const remaining = s.conversations.filter((c) => c.id !== id);
          const activeId =
            s.activeId === id ? (remaining[0]?.id ?? null) : s.activeId;
          return { conversations: remaining, activeId };
        }),

      renameConversation: (id, title) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === id ? touch({ ...c, title: title.trim() || c.title }) : c,
          ),
        })),

      setActive: (id) => set({ activeId: id }),

      addUserMessage: (conversationId, content) => {
        const msgId = uid("msg_");
        const msg: ChatMessage = {
          id: msgId,
          role: "user",
          content,
          createdAt: Date.now(),
          status: "complete",
        };
        set((s) => ({
          conversations: s.conversations.map((c) => {
            if (c.id !== conversationId) return c;
            const isFirst = c.messages.length === 0;
            return touch({
              ...c,
              title: isFirst ? deriveTitle(content) : c.title,
              messages: [...c.messages, msg],
            });
          }),
        }));
        return msgId;
      },

      addAssistantPlaceholder: (conversationId) => {
        const msgId = uid("msg_");
        const msg: ChatMessage = {
          id: msgId,
          role: "assistant",
          content: "",
          createdAt: Date.now(),
          status: "streaming",
        };
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? touch({ ...c, messages: [...c.messages, msg] })
              : c,
          ),
        }));
        return msgId;
      },

      appendToMessage: (conversationId, messageId, delta) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === messageId
                      ? { ...m, content: m.content + delta }
                      : m,
                  ),
                }
              : c,
          ),
        })),

      finalizeAssistantMessage: (conversationId, messageId, payload) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? touch({
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === messageId
                      ? {
                          ...m,
                          content: payload.content,
                          sources: payload.sources,
                          metrics: payload.metrics,
                          status: "complete",
                        }
                      : m,
                  ),
                })
              : c,
          ),
        })),

      setMessageError: (conversationId, messageId, error) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === messageId
                      ? { ...m, status: "error", error }
                      : m,
                  ),
                }
              : c,
          ),
        })),

      removeMessage: (conversationId, messageId) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? { ...c, messages: c.messages.filter((m) => m.id !== messageId) }
              : c,
          ),
        })),
    }),
    {
      name: "upi-rag-conversations",
      version: 1,
    },
  ),
);
