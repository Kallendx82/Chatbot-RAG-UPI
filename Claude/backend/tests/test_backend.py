"""Backend test suite (Slice 1).

Two tiers:
  - Unit tests: prompt building, schema validation, config. No heavy deps.
  - Integration tests: full app via FastAPI TestClient against a TINY in-memory
    FAISS index built with a fake embedder, so they run fast and need no model
    download or network.

Run:  pytest -q
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.rag.prompt import build_prompt, format_context, system_prompt


# ===========================================================================
# Unit tests - prompt
# ===========================================================================
def test_system_prompt_language_switch():
    assert "Bahasa Indonesia" in system_prompt("id")
    assert "concisely" in system_prompt("en")


def test_format_context_empty():
    assert "tidak ada konteks" in format_context([]).lower()


def test_format_context_numbers_and_attributes_sources():
    chunks = [
        {"title": "Doc A", "page": 2, "section": "BAB I", "text": "isi A"},
        {"title": "Doc B", "page": 5, "text": "isi B"},
    ]
    out = format_context(chunks)
    assert "[1]" in out and "[2]" in out
    assert "Doc A" in out and "hal. 2" in out and "BAB I" in out
    assert "isi A" in out and "isi B" in out


def test_build_prompt_contains_rules_context_and_question():
    prompt = build_prompt("Apa itu PPID?",
                          [{"title": "Pedoman", "page": 1, "text": "PPID adalah ..."}],
                          language="id")
    assert "ATURAN WAJIB" in prompt          # system rules present
    assert "PPID adalah" in prompt           # context injected
    assert "Apa itu PPID?" in prompt         # question present
    assert prompt.rstrip().endswith("JAWABAN:")


# ===========================================================================
# Unit tests - schemas
# ===========================================================================
def test_retrieve_request_rejects_empty_query():
    from pydantic import ValidationError
    from app.schemas.rag import RetrieveRequest

    with pytest.raises(ValidationError):
        RetrieveRequest(query="")


def test_chat_request_temperature_bounds():
    from pydantic import ValidationError
    from app.schemas.rag import ChatRequest

    ChatRequest(message="hi", temperature=0.5)  # ok
    with pytest.raises(ValidationError):
        ChatRequest(message="hi", temperature=9.0)


# ===========================================================================
# Integration fixtures - fake embedder + tiny FAISS index
# ===========================================================================
class FakeEmbedder:
    """Deterministic bag-of-words embedder for tests.

    Each word is hashed into a fixed bucket; the vector counts word buckets,
    then is L2-normalised. This is a proper test double: texts that share words
    produce vectors with POSITIVE cosine similarity, so retrieval behaves
    realistically (relevant chunks rank above irrelevant ones) and nothing is
    accidentally filtered by the non-negative score threshold.

    It is fully deterministic - no model download, no PYTHONHASHSEED dependence
    (md5 is used, not Python's randomised hash()).
    """

    _DIM = 64

    def __init__(self, *_args, **_kwargs):
        self._ready = True

    def load(self):  # noqa: D401 - matches Embedder API
        return None

    @property
    def ready(self):
        return True

    @property
    def dimension(self):
        return self._DIM

    @property
    def load_error(self):
        return None

    @property
    def model_name(self):
        return "fake-embedder-test"

    @staticmethod
    def _bucket(word: str) -> int:
        import hashlib

        return int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16) % 64

    def encode(self, texts, kind="passage"):
        vecs = []
        for t in texts:
            v = np.zeros(self._DIM, dtype="float32")
            for word in t.lower().split():
                v[self._bucket(word)] += 1.0
            norm = np.linalg.norm(v)
            if norm > 0:
                v /= norm
            else:
                v[0] = 1.0  # empty text -> a valid unit vector, never all-zero
            vecs.append(v)
        return np.vstack(vecs)


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    """A TestClient backed by a tiny FAISS index built with the fake embedder."""
    import faiss

    from app.core import container as container_mod
    from app.rag.vectorstore import FaissVectorStore
    from app.rag.llm import LLMService
    from app.services.rag_service import RagService

    # --- build a tiny index on disk ---
    chunks = [
        {"chunk_id": "c0", "doc_id": "d0", "title": "Pedoman PPID UPI",
         "category": "PPID", "source_type": "pdf", "page": 1,
         "section": "LAYANAN", "source": "ppid.pdf",
         "text": "PPID UPI menyediakan layanan informasi publik."},
        {"chunk_id": "c1", "doc_id": "d1", "title": "Panduan PMB UPI",
         "category": "PMB", "source_type": "pdf", "page": 2,
         "section": "PENDAFTARAN", "source": "pmb.pdf",
         "text": "Pendaftaran mahasiswa baru UPI dilakukan secara daring."},
    ]
    fake = FakeEmbedder()
    vecs = fake.encode([c["text"] for c in chunks])
    index = faiss.IndexFlatIP(fake.dimension)
    index.add(vecs)

    idx_path = tmp_path / "faiss.index"
    meta_path = tmp_path / "chunks_meta.json"
    info_path = tmp_path / "index_info.json"
    faiss.write_index(index, str(idx_path))
    meta_path.write_text(json.dumps(chunks), encoding="utf-8")
    info_path.write_text(json.dumps(
        {"embedding_model": "fake-embedder-test", "embedding_dim": fake.dimension,
         "n_vectors": len(chunks)}), encoding="utf-8")

    settings = Settings(
        faiss_index_path=str(idx_path),
        chunks_meta_path=str(meta_path),
        index_info_path=str(info_path),
        embedding_model="fake-embedder-test",
        llm_backend="extractive",
    )

    # --- container with the fake embedder swapped in ---
    class TestContainer(container_mod.Container):
        def __init__(self, s):
            self.settings = s
            self.embedder = FakeEmbedder()
            self.store = FaissVectorStore(s, self.embedder)
            self.llm = LLMService(s)
            self.rag = RagService(s, self.embedder, self.store, self.llm)

    monkeypatch.setattr(container_mod, "build_container",
                        lambda: TestContainer(settings))
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    from app.main import app
    with TestClient(app) as c:
        yield c


# ===========================================================================
# Integration tests
# ===========================================================================
def test_health_reports_ok_when_loaded(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["components"]["vector_store"]["status"] == "ok"
    assert body["components"]["embedder"]["status"] == "ok"


def test_root_endpoint(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "/health" in r.json()["health"]


def test_retrieve_returns_scored_results(client):
    r = client.post("/api/retrieve", json={"query": "layanan informasi publik"})
    assert r.status_code == 200
    body = r.json()
    assert body["n_results"] >= 1
    scores = [c["score"] for c in body["results"]]
    assert scores == sorted(scores, reverse=True)        # ordered by score
    assert all("title" in c and "text" in c for c in body["results"])
    assert body["retrieval_latency_ms"] >= 0


def test_retrieve_ranks_relevant_chunk_first(client):
    """The deterministic bag-of-words embedder must rank the PPID chunk top for
    a query whose words overlap it - a real retrieval-quality assertion."""
    r = client.post("/api/retrieve",
                     json={"query": "layanan informasi publik", "top_k": 2})
    assert r.status_code == 200
    results = r.json()["results"]
    assert results, "expected at least one result"
    # 'layanan informasi publik' overlaps the PPID chunk, not the PMB chunk.
    assert "PPID" in results[0]["title"]


def test_retrieve_rejects_empty_query(client):
    r = client.post("/api/retrieve", json={"query": "   "})
    assert r.status_code == 422


def test_retrieve_respects_top_k(client):
    r = client.post("/api/retrieve", json={"query": "UPI", "top_k": 1})
    assert r.status_code == 200
    assert len(r.json()["results"]) <= 1


def test_retrieve_debug_includes_prompt_preview(client):
    r = client.get("/api/retrieve/debug", params={"query": "pendaftaran mahasiswa"})
    assert r.status_code == 200
    body = r.json()
    assert "prompt_preview" in body and "ATURAN WAJIB" in body["prompt_preview"]
    assert body["embedding_latency_ms"] >= 0
    assert body["search_latency_ms"] >= 0
    assert body["index_size"] == 2


def test_chat_returns_grounded_answer_with_sources(client):
    r = client.post("/api/chat", json={"message": "Apa layanan PPID UPI?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"].strip()
    assert body["grounded"] is True
    assert len(body["sources"]) >= 1
    assert body["backend"] == "extractive"
    assert body["total_latency_ms"] >= 0


def test_chat_rejects_empty_message(client):
    r = client.post("/api/chat", json={"message": ""})
    assert r.status_code == 422
