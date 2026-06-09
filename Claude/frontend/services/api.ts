/**
 * Typed API client for the UPI RAG FastAPI backend (Slice 1 contract).
 *
 * Base URL comes from NEXT_PUBLIC_API_BASE_URL. In development this defaults to
 * the Next.js rewrite path "/backend-api" (see next.config.mjs), which proxies
 * to the backend and sidesteps CORS. In production, point it at the deployed
 * backend origin.
 *
 * Endpoints used (real, verified against Slice 1):
 *   GET  /health
 *   POST /api/chat
 *   POST /api/retrieve
 *   GET  /api/retrieve/debug?query=...&top_k=...
 *
 * Streaming note: the backend does NOT yet expose /api/chat/stream (deferred to
 * a later slice). `streamChat` is written so that when that endpoint lands, only
 * the marked block changes; today it falls back to the non-streaming /api/chat
 * and emits the answer progressively on the client (see useChat hook).
 */
import {
  ApiError,
  type ChatRequest,
  type ChatResponse,
  type HealthResponse,
  type RetrievalDebugResponse,
  type RetrieveRequest,
  type RetrieveResponse,
} from "@/types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "/backend-api";

/** Core fetch wrapper: JSON in/out, uniform error handling, timeouts. */
async function request<T>(
  path: string,
  options: RequestInit & { timeoutMs?: number } = {},
): Promise<T> {
  const { timeoutMs = 60_000, ...init } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers || {}),
      },
    });
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError("Permintaan melebihi batas waktu (timeout).", 408);
    }
    // Network failure / backend down.
    throw new ApiError(
      "Tidak dapat terhubung ke server. Pastikan backend berjalan.",
      0,
      err,
    );
  }
  clearTimeout(timer);

  if (!res.ok) {
    let detail: unknown = undefined;
    try {
      detail = await res.json();
    } catch {
      /* response had no JSON body */
    }
    const message =
      (detail as { detail?: string })?.detail ||
      `Permintaan gagal (HTTP ${res.status}).`;
    throw new ApiError(
      typeof message === "string" ? message : `HTTP ${res.status}`,
      res.status,
      detail,
    );
  }

  return (await res.json()) as T;
}

export const api = {
  health(): Promise<HealthResponse> {
    return request<HealthResponse>("/health", {
      method: "GET",
      timeoutMs: 8_000,
    });
  },

  chat(body: ChatRequest): Promise<ChatResponse> {
    return request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify(body),
      timeoutMs: 120_000,
    });
  },

  retrieve(body: RetrieveRequest): Promise<RetrieveResponse> {
    return request<RetrieveResponse>("/api/retrieve", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  retrieveDebug(
    query: string,
    topK?: number,
    scoreThreshold?: number,
    language: "id" | "en" = "id",
  ): Promise<RetrievalDebugResponse> {
    const params = new URLSearchParams({ query, language });
    if (topK != null) params.set("top_k", String(topK));
    if (scoreThreshold != null) params.set("score_threshold", String(scoreThreshold));
    return request<RetrievalDebugResponse>(
      `/api/retrieve/debug?${params.toString()}`,
      { method: "GET" },
    );
  },
};

/**
 * Streaming chat.
 *
 * Contract: yields incremental text deltas, then resolves with the full
 * ChatResponse (including sources + metrics) via the onComplete callback.
 *
 * TODAY: there is no SSE endpoint, so this calls /api/chat once and the caller
 * (useChat) animates the text. When the backend gains /api/chat/stream, replace
 * ONLY the body of this function with an EventSource/ReadableStream reader that
 * yields deltas as they arrive; the hook's interface does not change.
 */
export async function fetchChat(body: ChatRequest): Promise<ChatResponse> {
  return api.chat(body);
}
