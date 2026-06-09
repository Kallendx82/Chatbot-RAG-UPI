"""RAG orchestration service.

Ties together the embedder, FAISS vector store, prompt builder and LLM service.
The API layer talks only to this service, never to the RAG components directly,
so the endpoints stay thin and the orchestration logic is unit-testable.
"""
from __future__ import annotations

import time
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.rag.embedder import Embedder
from app.rag.llm import LLMService
from app.rag.prompt import build_prompt, detect_language
from app.rag.vectorstore import FaissVectorStore
from app.services import logging_service

logger = get_logger(__name__)


class RagService:
    """High-level retrieve + generate operations."""

    def __init__(
        self,
        settings: Settings,
        embedder: Embedder,
        store: FaissVectorStore,
        llm: LLMService,
    ) -> None:
        self._settings = settings
        self._embedder = embedder
        self._store = store
        self._llm = llm

    # -- readiness ---------------------------------------------------------
    @property
    def ready(self) -> bool:
        return self._embedder.ready and self._store.ready

    def readiness_detail(self) -> dict[str, Any]:
        return {
            "embedder_ready": self._embedder.ready,
            "embedder_error": self._embedder.load_error,
            "store_ready": self._store.ready,
            "store_error": self._store.load_error,
            "index_size": self._store.size,
        }

    # -- retrieval ---------------------------------------------------------
    @staticmethod
    def _dedupe_near_duplicates(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Drop chunks whose text is essentially identical to one already kept.

        Many UPI PDFs (Surat Rekomendasi PMBP, Pengumuman Hasil Seleksi, etc.)
        share boilerplate pages verbatim - the same 'Persyaratan Akademik'
        paragraph appears in 50+ doc variants. Without this filter, top-5
        retrieval returns five identical paragraphs and the LLM has no new
        information past rank 1.

        Fingerprint: first 200 chars of normalised text. Two chunks with the
        same fingerprint are treated as duplicates; the higher-scoring one wins.
        """
        seen: set[str] = set()
        kept: list[dict[str, Any]] = []
        for c in chunks:
            text = (c.get("text") or "").strip().lower()
            # Collapse whitespace so minor formatting differences don't matter.
            fingerprint = " ".join(text.split())[:200]
            if not fingerprint or fingerprint in seen:
                continue
            seen.add(fingerprint)
            kept.append(c)
        return kept

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> dict[str, Any]:
        """Run retrieval and return a structured result + timings.

        We oversample by 3x then dedupe by content fingerprint, then trim to
        the requested top_k. Net effect: the user sees k DIFFERENT chunks
        instead of k copies of the same boilerplate.
        """
        k = top_k or self._settings.default_top_k
        threshold = (
            self._settings.retrieval_score_threshold
            if score_threshold is None
            else score_threshold
        )
        # Oversample to give the deduper headroom; cap at max_top_k * 3.
        oversample = min(k * 3, max(self._settings.max_top_k * 3, 30))
        results, timings = self._store.search(query, oversample, threshold)

        # Drop near-duplicate paragraphs (same boilerplate across many docs).
        deduped = self._dedupe_near_duplicates(results)[:k]

        # Normalise each chunk into the SourceChunk shape the API promises.
        normalised = [self._to_source(c) for c in deduped]
        top_score = normalised[0]["score"] if normalised else None
        logging_service.log_retrieval(
            query=query,
            top_k=k,
            n_results=len(normalised),
            latency_ms=timings["total_ms"],
            top_score=top_score,
        )
        return {
            "query": query,
            "top_k": k,
            "score_threshold": threshold,
            "embedding_model": self._embedder.model_name,
            "timings": timings,
            "index_size": self._store.size,
            "results": normalised,
        }

    # -- chat --------------------------------------------------------------
    @staticmethod
    def _resolve_language(query: str, language: str | None) -> str:
        """Resolve the answer language: explicit value wins, else auto-detect from query."""
        if language and language not in ("auto", ""):
            return language
        return detect_language(query)

    def chat(
        self,
        message: str,
        top_k: int | None = None,
        temperature: float | None = None,
        language: str = "id",
        model: str | None = None,
    ) -> dict[str, Any]:
        """Full RAG turn: retrieve -> build grounded prompt -> generate answer."""
        t0 = time.time()
        retrieval = self.retrieve(message, top_k=top_k)
        chunks = retrieval["results"]
        retrieval_ms = retrieval["timings"]["total_ms"]

        t1 = time.time()
        answer, backend_used = self._llm.generate(
            query=message,
            chunks=chunks,
            language=self._resolve_language(message, language),
            temperature=temperature,
            model=model,
        )
        generation_ms = round((time.time() - t1) * 1000, 2)
        total_ms = round((time.time() - t0) * 1000, 2)

        logging_service.log_chat(
            query=message,
            backend=backend_used,
            grounded=bool(chunks),
            n_sources=len(chunks),
            retrieval_ms=retrieval_ms,
            generation_ms=generation_ms,
            total_ms=total_ms,
        )
        return {
            "answer": answer,
            "backend": backend_used,
            "grounded": bool(chunks),
            "sources": chunks,
            "retrieval_latency_ms": retrieval_ms,
            "generation_latency_ms": generation_ms,
            "total_latency_ms": total_ms,
        }

    # -- debug -------------------------------------------------------------
    def retrieve_debug(
        self,
        query: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
        language: str = "id",
    ) -> dict[str, Any]:
        """Verbose retrieval output including the exact prompt /chat would send."""
        retrieval = self.retrieve(query, top_k=top_k, score_threshold=score_threshold)
        prompt_preview = build_prompt(
            query, retrieval["results"], self._resolve_language(query, language)
        )
        return {**retrieval, "prompt_preview": prompt_preview}

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _to_source(chunk: dict[str, Any]) -> dict[str, Any]:
        """Project a raw stored chunk onto the SourceChunk schema fields.

        Tolerant of metadata variation across notebook versions: missing keys
        become None rather than raising.
        """
        return {
            "rank": chunk.get("rank", 0),
            "score": float(chunk.get("score", 0.0)),
            "chunk_id": str(chunk.get("chunk_id", chunk.get("chunk_index", ""))),
            "doc_id": str(chunk.get("doc_id", "")),
            "title": chunk.get("title", "Dokumen tanpa judul"),
            "category": chunk.get("category"),
            "source_type": chunk.get("source_type"),
            "source": chunk.get("source"),
            "url": chunk.get("url"),
            "page": chunk.get("page"),
            "section": chunk.get("section"),
            "text": chunk.get("text", ""),
        }
