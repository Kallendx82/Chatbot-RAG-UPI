"""Embedding service.

Wraps a SentenceTransformer model. Loaded lazily and once per process so the
heavy model load happens at startup, not on the first request.

The notebooks use intfloat/multilingual-e5-base, which expects "query: " /
"passage: " prefixes; that prefixing is centralised here so callers never have
to remember it.
"""
from __future__ import annotations

import threading
import time

import numpy as np

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Embedder:
    """Thread-safe lazy wrapper around a SentenceTransformer model."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = None
        self._dim: int | None = None
        self._lock = threading.Lock()
        self._load_error: str | None = None

    # -- lifecycle ---------------------------------------------------------
    def load(self) -> None:
        """Load the model. Idempotent. Records any failure instead of raising."""
        if self._model is not None or self._load_error is not None:
            return
        with self._lock:
            if self._model is not None or self._load_error is not None:
                return
            try:
                from sentence_transformers import SentenceTransformer

                t0 = time.time()
                logger.info("Loading embedding model: %s",
                            self._settings.embedding_model)
                model = SentenceTransformer(self._settings.embedding_model)
                self._dim = model.get_sentence_embedding_dimension()
                self._model = model
                logger.info("Embedding model loaded in %.1fs (dim=%d)",
                            time.time() - t0, self._dim)
            except Exception as exc:  # noqa: BLE001 - want to capture anything
                self._load_error = str(exc)
                logger.error("Failed to load embedding model: %s", exc)

    # -- properties --------------------------------------------------------
    @property
    def ready(self) -> bool:
        return self._model is not None

    @property
    def dimension(self) -> int | None:
        return self._dim

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def model_name(self) -> str:
        return self._settings.embedding_model

    # -- encoding ----------------------------------------------------------
    def _prefix(self, texts: list[str], kind: str) -> list[str]:
        if not self._settings.use_e5_prefixes:
            return texts
        tag = "query: " if kind == "query" else "passage: "
        return [tag + t for t in texts]

    def encode(self, texts: list[str], kind: str = "passage") -> np.ndarray:
        """Encode texts to L2-normalised float32 vectors (cosine-ready).

        kind: "query" or "passage" - controls the e5 prefix.
        Raises RuntimeError if the model failed to load.
        """
        if self._model is None:
            raise RuntimeError(
                f"Embedding model not available: {self._load_error or 'not loaded'}"
            )
        prepared = self._prefix(texts, kind)
        vecs = self._model.encode(
            prepared,
            batch_size=self._settings.embedding_batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vecs.astype("float32")
