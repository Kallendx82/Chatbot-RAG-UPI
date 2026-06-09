# UPI RAG Chatbot — Backend (Slice 1: Core + RAG Integration)

Backend for the thesis project *“Rancang Bangun Chatbot sebagai Sumber
Informasi Sivitas Universitas Pendidikan Indonesia Berbasis RAG.”*

This slice delivers a **fully runnable** FastAPI service that connects to the
FAISS vector index produced by the RAG pipeline notebooks
(`03_vectorstore_rag_evaluation.ipynb`) and exposes retrieval, retrieval
debugging, and grounded chat.

Later slices add authentication & persistence, the Next.js frontend, the admin
dashboard, and Docker orchestration.

---

## What is in this slice

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Per-component readiness (embedder, vector store, LLM backend) |
| `/` | GET | Service landing payload |
| `/api/retrieve` | POST | Top-k chunk retrieval with similarity scores + latency |
| `/api/retrieve/debug` | GET | Verbose retrieval inspection + exact grounded prompt preview |
| `/api/chat` | POST | Full RAG turn: retrieve → grounded prompt → cited answer |

Interactive API docs are at `/docs` once the server is running.

---

## Project structure

```
backend/
├── app/
│   ├── api/                health_routes.py, rag_routes.py
│   ├── core/               config.py, logging.py, container.py
│   ├── rag/                embedder.py, vectorstore.py, prompt.py, llm.py
│   ├── schemas/            rag.py  (the API contract)
│   ├── services/           rag_service.py, logging_service.py
│   ├── data/               vector index artefacts + retrieval logs (gitignored)
│   └── main.py             FastAPI entry point
├── scripts/
│   └── build_sample_index.py   synthetic index so the API runs before
│                               real notebook artefacts are ready
├── tests/
│   └── test_backend.py     14 unit + integration tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

Requires **Python 3.11+**.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### Provide a vector index

The backend needs three files from the notebooks (set their paths in `.env`):
`faiss.index`, `chunks_meta.json`, `index_info.json`.

**Option A — use your real notebook output.** Download the `index/` folder that
`03_vectorstore_rag_evaluation.ipynb` writes to Google Drive
(`_pipeline/index/`) and point `FAISS_INDEX_PATH`, `CHUNKS_META_PATH`,
`INDEX_INFO_PATH` at the three files. **`EMBEDDING_MODEL` in `.env` must match
the model recorded in `index_info.json`** — a mismatch is detected at startup
and reported by `/health`.

**Option B — synthetic fixture (run the app immediately).**

```bash
python -m scripts.build_sample_index
```

This builds a tiny 5-chunk UPI-flavoured index into `app/data/`, exactly where
`.env.example` points. Replace those files with real artefacts later — no code
change needed.

> Option B downloads the `multilingual-e5-base` embedding model (~1 GB) on
> first run; it is cached afterwards.

---

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

- API docs: <http://localhost:8000/docs>
- Health:   <http://localhost:8000/health>

If no valid index is configured, the app **still starts**: `/health` reports
`degraded` and retrieval endpoints return `503` with an actionable message.
This is intentional — the service never crashes on a missing index.

---

## Example requests

```bash
# Health
curl http://localhost:8000/health

# Retrieve top-k chunks
curl -X POST http://localhost:8000/api/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "layanan informasi publik PPID UPI", "top_k": 5}'

# Retrieval debugging (note: GET with query params)
curl "http://localhost:8000/api/retrieve/debug?query=pendaftaran%20mahasiswa%20baru&top_k=5"

# Grounded chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Bagaimana prosedur pendaftaran mahasiswa baru UPI?", "language": "id"}'
```

---

## LLM backends

Set `LLM_BACKEND` in `.env`:

- **`extractive`** (default) — no LLM. Returns the top retrieved chunk plus
  source references. Always works; ideal for first run, CI, and offline demos.
- **`ollama`** — local LLM. Run Ollama and `ollama pull llama3.1`, then set
  `LLM_BACKEND=ollama`.
- **`openai`** — any OpenAI-compatible API. Set `OPENAI_API_KEY` (and
  `OPENAI_BASE_URL` if not OpenAI itself).

If `ollama`/`openai` fails at request time, the backend falls back to
`extractive` so `/chat` never hard-fails (reported as `extractive_fallback`).

---

## Testing

```bash
pytest -q
```

14 tests: prompt construction, schema validation, and full-app integration
tests that build a tiny in-memory FAISS index with a fake embedder — so they
run in well under a second and need no model download or network.

---

## Retrieval logs

Every retrieval and chat call appends a JSON line to `app/data/logs/`:

- `retrieval.jsonl` — all retrievals
- `chat.jsonl` — all chat turns
- `failed_retrieval.jsonl` — zero-result retrievals (for thesis failure analysis)

These feed the admin dashboard and evaluation tools in later slices.

---

## Architecture notes & known limitations

**Design.** Routes are thin; all orchestration is in `RagService`. The RAG
components (`Embedder`, `FaissVectorStore`, `LLMService`) are independent and
injected via a `Container` built once at startup. The vector store is a thin
adapter — swapping FAISS for Chroma later means writing one class with the same
`search()` / `ready` / `info` surface.

**Integrity checks.** On load, the backend verifies that the index vector count
matches the metadata length and warns loudly if the embedding model in
`index_info.json` differs from `EMBEDDING_MODEL`.

**Honest limitations of this slice (to be addressed later):**

- *No streaming yet.* `/chat` is request/response. `/chat/stream` arrives with
  the frontend slice (Server-Sent Events).
- *No auth.* Every endpoint is open. JWT + roles is the next slice; do not
  expose this build publicly as-is.
- *Single-process, in-RAM index.* `IndexFlatIP` is exact and fine to ~10⁵–10⁶
  chunks. Larger corpora need `IndexIVFFlat`/`IndexHNSW` — the adapter makes
  that a contained change.
- *Retrieval is pure dense vector search.* Exact-token queries (regulation
  numbers like “SE No. 12/2024”) may retrieve poorly; hybrid BM25 + dense
  search is a candidate improvement, justified by the `failed_retrieval.jsonl`
  evidence.
- *No rate limiting.* Add a limiter before any public deployment.
```
```
