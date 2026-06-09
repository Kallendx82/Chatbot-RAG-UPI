"""FAISS vector store: loading, integrity checks, and retrieval.

Loads the three artefacts produced by 03_vectorstore_rag_evaluation.ipynb:
  - faiss.index        the FAISS index (IndexFlatIP on normalised vectors)
  - chunks_meta.json   chunk metadata, row-aligned to the index
  - index_info.json    model name + dim recorded at build time

The class is deliberately a thin adapter over FAISS. Swapping to Chroma later
means writing a class with the same `search()` / `ready` / `info` surface;
nothing else in the backend needs to change.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.rag.embedder import Embedder

logger = get_logger(__name__)


class VectorStoreError(RuntimeError):
    """Raised when the vector store cannot serve retrieval requests."""


class FaissVectorStore:
    """Loads a FAISS index + chunk metadata and serves top-k retrieval."""

    def __init__(self, settings: Settings, embedder: Embedder) -> None:
        self._settings = settings
        self._embedder = embedder
        self._index = None
        self._meta: list[dict[str, Any]] = []
        self._info: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._load_error: str | None = None

    # -- lifecycle ---------------------------------------------------------
    def load(self) -> None:
        """Load index + metadata. Idempotent. Records failure instead of raising."""
        if self._index is not None or self._load_error is not None:
            return
        with self._lock:
            if self._index is not None or self._load_error is not None:
                return
            try:
                self._do_load()
            except Exception as exc:  # noqa: BLE001
                self._load_error = str(exc)
                logger.error("Vector store load failed: %s", exc)

    def _do_load(self) -> None:
        import faiss

        idx_path = self._settings.faiss_index_file
        meta_path = self._settings.chunks_meta_file
        info_path = self._settings.index_info_file

        # --- existence checks with actionable messages ---
        missing = [str(p) for p in (idx_path, meta_path) if not p.exists()]
        if missing:
            raise VectorStoreError(
                "Missing vector store files: "
                + ", ".join(missing)
                + ". Run 03_vectorstore_rag_evaluation.ipynb and copy its "
                "index/ artefacts to the paths in your .env file."
            )

        t0 = time.time()
        index = faiss.read_index(str(idx_path))
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        info = {}
        if info_path.exists():
            info = json.loads(info_path.read_text(encoding="utf-8"))
        else:
            logger.warning("index_info.json not found - skipping model check.")

        # --- integrity checks ---
        if not isinstance(meta, list):
            raise VectorStoreError("chunks_meta.json must be a JSON list.")
        if index.ntotal != len(meta):
            raise VectorStoreError(
                f"Index/metadata mismatch: {index.ntotal} vectors vs "
                f"{len(meta)} metadata records. The index and metadata are "
                "out of sync - rebuild both together."
            )
        recorded_model = info.get("embedding_model")
        if recorded_model and recorded_model != self._settings.embedding_model:
            # Not fatal, but retrieval quality will be wrong - surface loudly.
            logger.warning(
                "Embedding model mismatch: index built with '%s' but config "
                "uses '%s'. Set EMBEDDING_MODEL to match, or rebuild the index.",
                recorded_model, self._settings.embedding_model,
            )

        self._index = index
        self._meta = meta
        self._info = info
        logger.info(
            "Vector store loaded: %d vectors, dim=%d, %.2fs",
            index.ntotal, index.d, time.time() - t0,
        )

    # -- properties --------------------------------------------------------
    @property
    def ready(self) -> bool:
        return self._index is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def size(self) -> int:
        return self._index.ntotal if self._index is not None else 0

    @property
    def info(self) -> dict[str, Any]:
        """Build-time metadata (model, dim, n_vectors, built_at)."""
        return dict(self._info)

    # -- retrieval ---------------------------------------------------------
    def search(
        self,
        query: str,
        top_k: int,
        score_threshold: float = 0.0,
    ) -> tuple[list[dict[str, Any]], dict[str, float]]:
        """Retrieve top-k chunks for a query.

        Returns (results, timings). Each result is the stored chunk metadata
        with an added float `score`. `timings` has embedding/search/total in ms.

        Raises VectorStoreError if the store is not ready.
        """
        if self._index is None:
            raise VectorStoreError(
                self._load_error or "Vector store is not loaded."
            )
        if not query.strip():
            return [], {"embedding_ms": 0.0, "search_ms": 0.0, "total_ms": 0.0}

        # Clamp top_k to the configured ceiling and the index size.
        k = max(1, min(top_k, self._settings.max_top_k, self._index.ntotal))

        t0 = time.time()
        qvec = self._embedder.encode([query], kind="query")
        t1 = time.time()
        scores, idxs = self._index.search(qvec, k)
        t2 = time.time()

        results: list[dict[str, Any]] = []
        for rank, (score, idx) in enumerate(zip(scores[0], idxs[0]), start=1):
            if idx < 0:  # FAISS pads with -1 when fewer than k results exist
                continue
            if float(score) < score_threshold:
                continue
            chunk = dict(self._meta[idx])
            chunk["score"] = float(score)
            chunk["rank"] = rank
            results.append(chunk)

        timings = {
            "embedding_ms": round((t1 - t0) * 1000, 2),
            "search_ms": round((t2 - t1) * 1000, 2),
            "total_ms": round((t2 - t0) * 1000, 2),
        }
        return results, timings
