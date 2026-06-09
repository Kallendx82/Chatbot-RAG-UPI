# Chatbot RAG UPI

**Rancang Bangun Chatbot sebagai Sumber Informasi Sivitas Universitas Pendidikan Indonesia Berbasis Retrieval-Augmented Generation (RAG)**

Local-first RAG chatbot for the UPI academic community: ingest UPI PDFs, build a FAISS vector index, retrieve grounded context, and answer with citations using a local LLM via Ollama.

---

## Architecture

```
PDFs (UPI documents)
        |
        v
+---------------------+    +-----------------+    +------------------+
|  01 extraction      | -> |  02 chunking    | -> |  03 vectorstore  |
|  (PyMuPDF + OCR)    |    |  (recursive +   |    |  (FAISS local)   |
|  -> JSON / TXT / MD |    |   heading-aware)|    |  multilingual e5 |
+---------------------+    +-----------------+    +------------------+
                                                          |
                                                          v
                                              +-----------------------+
                                              |   FastAPI backend     |
                                              |   (retrieve + chat)   |
                                              +-----------------------+
                                                  |             |
                                                  v             v
                                          +---------------+ +-----------+
                                          | Next.js UI    | |  Ollama   |
                                          | (citations,   | |  (LLama / |
                                          |  multi-turn)  | |   Qwen)   |
                                          +---------------+ +-----------+
```

## Tech stack

- **Vector DB:** FAISS `IndexFlatIP` (exact cosine over normalised vectors), 100% local
- **Embeddings:** `intfloat/multilingual-e5-base` (768 dim, Indonesian-aware)
- **LLM:** Ollama (`llama3.1:8b` default, `llama3.2:3b`, `qwen2.5:3b` selectable)
- **Backend:** FastAPI + Pydantic
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind, Zustand
- **Pipeline:** Jupyter notebooks for extraction, chunking, indexing, evaluation

## Repository layout

```
.
├── Source code/                     Pipeline notebooks
│   ├── 01_cleaning_extraction_pipeline.ipynb   PDF/HTML -> cleaned JSON+TXT+MD
│   ├── 02_chunking_pipeline.ipynb              Cleaned text -> chunks.jsonl
│   ├── 03_vectorstore_rag_evaluation.ipynb     Chunks -> FAISS + first eval
│   ├── 04_update_pipeline.ipynb                Incremental update (New_Dataset/)
│   ├── 05_evaluation_ragas.ipynb               RAGAS-based eval (LLM judge)
│   ├── 06_evaluation_retrieval.ipynb           Classical IR metrics
│   ├── check_pipeline_health.py                Detects corruption / orphans
│   └── find_duplicate_pdfs.py                  Dedup the source corpus
│
├── Claude/
│   ├── backend/                     FastAPI (uvicorn) RAG service
│   │   ├── app/api/                 health + RAG routes
│   │   ├── app/rag/                 embedder, vectorstore, prompt, LLM dispatch
│   │   ├── app/services/            orchestration + logging
│   │   ├── app/schemas/             pydantic contracts
│   │   └── requirements.txt
│   ├── frontend/                    Next.js 14 chat UI
│   │   ├── app/                     routes + layout
│   │   ├── components/              chat, citations, debug, settings
│   │   ├── hooks/                   useChat
│   │   ├── store/                   zustand (settings + conversations)
│   │   └── package.json
│   ├── start.bat / start.ps1        One-shot launcher (Ollama + backend + frontend)
│   ├── stop.bat                     Stop everything
│   └── diagnose.ps1                 Layer-by-layer health probe
│
└── README.md
```

## Running locally (Windows)

### 1. Pipeline (one-time)

```powershell
cd "Source code"
# Open each notebook in Jupyter and run top-to-bottom:
#   01 -> 02 -> 03
# Outputs land in  ../Dataset/_pipeline/
```

### 2. Pull at least one LLM

```powershell
ollama pull llama3.1:8b      # default, best quality
ollama pull llama3.2:3b      # fast alternative
ollama pull qwen2.5:3b       # alternative
```

### 3. One-shot launcher

```powershell
cd Claude
.\start.bat                  # checks venv/env, starts Ollama + backend + frontend
```

This opens `http://localhost:3000` in your browser. Three PowerShell windows appear (Ollama, backend, frontend).

Stop everything later:

```powershell
.\stop.bat
```

### 4. Health check

```powershell
.\diagnose.ps1
```

Pings every layer (Ollama, backend `/health`, end-to-end `/api/chat`) and tells you exactly where any failure happens.

## Evaluation

Two complementary frameworks:

| Notebook | Framework | What it measures |
|---|---|---|
| `05_evaluation_ragas.ipynb` | RAGAS with Ollama judge | Faithfulness, Answer Relevancy, Context Precision, Context Recall |
| `06_evaluation_retrieval.ipynb` | Classical IR metrics | Hit Rate@k, Precision@k, Recall@k, MRR, nDCG@k, latency |

Queries are loaded from `Dataset/evaluation.csv` (columns: `query`, `context`). Results land in `Dataset/_pipeline/eval/`.

## Key design notes

- **All-local, all-offline:** FAISS on disk, Ollama for generation, no cloud APIs.
- **Numbered-citation prompt:** every factual sentence in the answer must carry `[1] [2]` references to the numbered sources.
- **Auto-language detection:** Indonesian queries get Indonesian answers, English queries get English answers — no setting required.
- **Content-fingerprint dedup at retrieval:** the corpus has ~50% duplicate boilerplate (Surat Rekomendasi PMBP templates). The backend oversamples by 3x and drops near-duplicate chunks before they reach the LLM, so top-5 always shows 5 *different* perspectives.
- **Low-content chunk filter:** chunks that are >65% digits/punctuation (corrupted tuition tables) are removed at prompt time. They retrieve well but the LLM can't extract anything from them.

## Data not in the repo

The `Dataset/` folder contains thousands of PDFs and a 180 MB FAISS index — too big for git. Reproduce by:

1. Drop your UPI source PDFs into `Dataset/<category>/`.
2. Run notebooks 01 -> 02 -> 03.
3. Result is `Dataset/_pipeline/index/faiss.index` etc. The backend's `.env` already points at this location.

## License / Acknowledgements

Thesis project at Universitas Pendidikan Indonesia. Built on:
- FAISS (Meta AI)
- Sentence-Transformers, `intfloat/multilingual-e5-base` (Microsoft / community)
- Ollama (with Llama 3 / Qwen 2.5)
- FastAPI, Next.js, RAGAS
