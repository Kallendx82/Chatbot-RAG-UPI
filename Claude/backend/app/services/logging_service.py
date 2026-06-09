"""Retrieval / evaluation logging.

Appends one JSON line per retrieval and per chat call to log files on disk.
Later slices (admin dashboard, evaluation tools) read these. Kept as JSONL so
they are append-only, crash-safe, and trivially parseable into pandas.

Failed retrievals (zero results) are also written to a dedicated file so the
thesis "failed retrieval" analysis has a ready dataset.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_LOG_DIR = Path("./app/data/logs")
_RETRIEVAL_LOG = _LOG_DIR / "retrieval.jsonl"
_CHAT_LOG = _LOG_DIR / "chat.jsonl"
_FAILED_LOG = _LOG_DIR / "failed_retrieval.jsonl"

_write_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(path: Path, record: dict[str, Any]) -> None:
    """Append one JSON line. Best-effort: a logging failure never breaks a request."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _write_lock:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not write log %s: %s", path.name, exc)


def log_retrieval(
    query: str,
    top_k: int,
    n_results: int,
    latency_ms: float,
    top_score: float | None,
) -> None:
    """Record a /retrieve call. Zero-result calls also go to the failed log."""
    record = {
        "ts": _now(),
        "query": query,
        "top_k": top_k,
        "n_results": n_results,
        "latency_ms": latency_ms,
        "top_score": top_score,
    }
    _append(_RETRIEVAL_LOG, record)
    if n_results == 0:
        _append(_FAILED_LOG, record)


def log_chat(
    query: str,
    backend: str,
    grounded: bool,
    n_sources: int,
    retrieval_ms: float,
    generation_ms: float,
    total_ms: float,
) -> None:
    """Record a /chat call for analytics and evaluation."""
    _append(
        _CHAT_LOG,
        {
            "ts": _now(),
            "query": query,
            "backend": backend,
            "grounded": grounded,
            "n_sources": n_sources,
            "retrieval_ms": retrieval_ms,
            "generation_ms": generation_ms,
            "total_ms": total_ms,
        },
    )
