# UPI RAG Chatbot — Frontend (Slice 3)

Next.js 14 (App Router) frontend for the thesis *“Rancang Bangun Chatbot
sebagai Sumber Informasi Sivitas Universitas Pendidikan Indonesia Berbasis
RAG.”* It connects to the **Slice 1 FastAPI backend** and provides a polished,
citation-forward, Indonesian-first chat experience.

---

## Stack

- **Next.js 14** (App Router, React Server + Client Components)
- **TypeScript** (strict)
- **Tailwind CSS** + **shadcn/ui**-style primitives (Radix UI)
- **Zustand** for state (conversations, settings, UI) with localStorage persistence
- **Framer Motion** for animation
- **react-markdown** + **rehype-highlight** for rich answer rendering

Design direction: *editorial-academic* — Spectral serif display, Asap body,
JetBrains Mono for code/metrics; warm-paper light mode, deep ink-navy dark mode,
amber accent for citations, teal for the retrieval-debug surface.

---

## Features in this slice

| Feature | Where |
|---------|-------|
| Chat UI (markdown, code highlight, copy, regenerate, typing/streaming render) | `components/chat/` |
| Citation system (source cards + slide-over inspector with full chunk + metadata) | `components/citations/` |
| Retrieval debug panel (chunks, cosine scores, per-stage latency, prompt preview) | `components/debug/` |
| Sidebar (history, new/rename/delete, search, day-grouping, collapse) | `components/sidebar/` |
| Settings modal (top-k, temperature, model, language, theme, debug mode) | `components/settings/` |
| Dark / light / system theme | `components/layout/ThemeProvider.tsx` |
| Connection health indicator + offline/degraded banners | `components/layout/TopBar.tsx`, `hooks/useHealth.ts` |
| Responsive layout (sidebar overlays on mobile) | `components/layout/AppShell.tsx` |

---

## Backend contract (real, from Slice 1)

Types in `types/index.ts` mirror `backend/app/schemas/rag.py` exactly. The
client (`services/api.ts`) calls:

- `GET  /health`
- `POST /api/chat`
- `POST /api/retrieve`
- `GET  /api/retrieve/debug?query=…&top_k=…`

> The spec mentioned `POST /chat`, `GET /chat/history`, etc. Those do **not**
> match the real backend. This frontend targets the **actual** Slice 1 routes.
> `chat/history` does not exist yet, so conversation history is persisted
> **client-side** (localStorage) until Slice 2 adds server-side persistence.

---

## Setup

Requires **Node.js 18.18+** (Node 20 LTS recommended).

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev    # http://localhost:3000
```

Make sure the Slice 1 backend is running on `http://localhost:8000`. The dev
server proxies `/backend-api/*` → the backend (see `next.config.mjs`), so there
are **no CORS issues** in development.

### Environment

```
NEXT_PUBLIC_API_BASE_URL=/backend-api   # browser → Next proxy → backend
BACKEND_ORIGIN=http://localhost:8000     # where the proxy forwards (server-side)
```

For a direct (non-proxied) connection, set
`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` and ensure the backend's CORS
allows `http://localhost:3000` (it does by default).

---

## Scripts

```bash
npm run dev        # dev server
npm run build      # production build
npm run start      # serve production build
npm run typecheck  # tsc --noEmit
npm run lint       # next lint
```

---

## Streaming

The architecture is **streaming-capable** but the backend has no SSE endpoint
yet. `hooks/useChat.ts` renders answers progressively (token-by-token) on the
client and `services/api.ts#fetchChat` is the single swap point: when
`/api/chat/stream` lands, replace that function's body with a `ReadableStream`
reader that calls `appendToMessage` on each delta. No component changes needed.

---

## Verification performed

- `npm run typecheck` — **passes** (strict, 0 errors).
- `npx next build` — **compiles successfully**, 0 warnings, 4 routes generated.
  (In a no-network sandbox the Google Fonts fetch must be reachable; on any
  machine with internet the build with `next/font/google` works as written.)

---

## Architecture notes & honest limitations

**State.** Three Zustand stores: `conversationStore` (persisted),
`settingsStore` (persisted), `settingsStore`'s `useUIStore` (ephemeral). The
persistence layer is isolated so Slice 2 can swap localStorage for API-backed
history by changing only the store actions.

**Hydration.** `AppShell` gates on `useMounted` so localStorage-backed stores
hydrate before first paint (no SSR/client mismatch).

**Known limitations (intentional for this slice):**
- *No real streaming yet* — simulated client-side (see above).
- *No auth* — every action is local/anonymous. Login + protected routes are
  Slice 2.
- *History is browser-local* — clearing site data clears chats; not shared
  across devices until Slice 2.
- *Model selector is informational* — the actual LLM backend is chosen by the
  server (`LLM_BACKEND` in the backend `.env`). The UI selector is a label for
  this slice; wiring it to a per-request backend override is a later change.
- *No virtualisation* — very long conversations render all messages. Fine for a
  demo; add windowing (e.g. virtua/react-virtuoso) before heavy production use.
```
