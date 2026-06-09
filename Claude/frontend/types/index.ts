/**
 * API + domain types.
 *
 * The API types mirror the Slice 1 FastAPI contract EXACTLY (see backend
 * app/schemas/rag.py). Keeping them in sync is what makes the typed client
 * trustworthy. Domain types (Conversation, ChatMessage) are frontend-only for
 * this slice; chat history is persisted client-side until Slice 2 adds a
 * server-backed store.
 */

// ---------------------------------------------------------------------------
// Backend contract (must match backend/app/schemas/rag.py)
// ---------------------------------------------------------------------------
export interface SourceChunk {
  rank: number;
  score: number;
  chunk_id: string;
  doc_id: string;
  title: string;
  category?: string | null;
  source_type?: string | null;
  source?: string | null;
  url?: string | null;
  page?: number | null;
  section?: string | null;
  text: string;
}

export interface ChatRequest {
  message: string;
  top_k?: number | null;
  temperature?: number | null;
  language?: "id" | "en" | null;
  model?: string | null;
}

export interface ChatResponse {
  answer: string;
  backend: string;
  grounded: boolean;
  sources: SourceChunk[];
  retrieval_latency_ms: number;
  generation_latency_ms: number;
  total_latency_ms: number;
}

export interface RetrieveRequest {
  query: string;
  top_k?: number | null;
  score_threshold?: number | null;
}

export interface RetrieveResponse {
  query: string;
  top_k: number;
  embedding_model: string;
  retrieval_latency_ms: number;
  n_results: number;
  results: SourceChunk[];
}

export interface RetrievalDebugResponse {
  query: string;
  embedding_model: string;
  use_e5_prefixes: boolean;
  top_k: number;
  score_threshold: number;
  embedding_latency_ms: number;
  search_latency_ms: number;
  total_latency_ms: number;
  index_size: number;
  n_results: number;
  results: SourceChunk[];
  prompt_preview: string;
}

export type HealthStatus = "ok" | "degraded" | "down";

export interface ComponentHealth {
  status: HealthStatus;
  detail: string;
}

export interface HealthResponse {
  status: HealthStatus;
  app_env: string;
  components: Record<string, ComponentHealth>;
}

// ---------------------------------------------------------------------------
// Frontend domain types
// ---------------------------------------------------------------------------
export type MessageRole = "user" | "assistant";

export type MessageStatus =
  | "pending" // user message just added; assistant not started
  | "streaming" // assistant tokens arriving
  | "complete"
  | "error";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: number;
  status: MessageStatus;
  /** Assistant-only: retrieved sources for citation rendering. */
  sources?: SourceChunk[];
  /** Assistant-only: per-turn metrics for the debug panel. */
  metrics?: {
    backend: string;
    grounded: boolean;
    retrievalMs: number;
    generationMs: number;
    totalMs: number;
  };
  /** Error detail when status === "error". */
  error?: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

// ---------------------------------------------------------------------------
// Settings (persisted client-side)
// ---------------------------------------------------------------------------
export type ThemeMode = "light" | "dark" | "system";
export type Language = "id" | "en";

export interface Settings {
  topK: number;
  temperature: number;
  language: Language;
  model: string; // informational label for this slice (backend selects backend)
  theme: ThemeMode;
  debugMode: boolean;
}

// ---------------------------------------------------------------------------
// API error shape
// ---------------------------------------------------------------------------
export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}
