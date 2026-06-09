"""Pydantic request/response schemas.

These define the API contract that the frontend (a later slice) will depend on.
Keeping them in one module makes the contract easy to review and version.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Shared
# --------------------------------------------------------------------------
class SourceChunk(BaseModel):
    """A single retrieved chunk, as surfaced to the client for citations."""

    rank: int = Field(..., description="1-based rank in the retrieval result")
    score: float = Field(..., description="Cosine similarity (higher = closer)")
    chunk_id: str
    doc_id: str
    title: str
    category: Optional[str] = None
    source_type: Optional[str] = None
    source: Optional[str] = Field(None, description="File path or URL of origin")
    url: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    text: str = Field(..., description="The chunk content")


# --------------------------------------------------------------------------
# /retrieve
# --------------------------------------------------------------------------
class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User query / search text")
    top_k: Optional[int] = Field(
        None, ge=1, description="Number of chunks to retrieve (capped by max_top_k)"
    )
    score_threshold: Optional[float] = Field(
        None, description="Drop hits below this similarity score"
    )


class RetrieveResponse(BaseModel):
    query: str
    top_k: int
    embedding_model: str
    retrieval_latency_ms: float
    n_results: int
    results: list[SourceChunk]


# --------------------------------------------------------------------------
# /retrieve/debug
# --------------------------------------------------------------------------
class RetrievalDebugResponse(BaseModel):
    """Verbose retrieval output for the thesis retrieval-debugging tool."""

    query: str
    embedding_model: str
    use_e5_prefixes: bool
    top_k: int
    score_threshold: float
    embedding_latency_ms: float
    search_latency_ms: float
    total_latency_ms: float
    index_size: int
    n_results: int
    results: list[SourceChunk]
    prompt_preview: str = Field(
        ..., description="The exact grounded prompt that /chat would build"
    )


# --------------------------------------------------------------------------
# /chat
# --------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    top_k: Optional[int] = Field(None, ge=1)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    language: Optional[Literal["id", "en"]] = Field(
        None, description="Preferred answer language; defaults to Indonesian"
    )
    model: Optional[str] = Field(
        None,
        description="Optional Ollama model override (e.g. 'llama3.1:8b'). "
                    "If unset or 'extractive', the server-configured backend is used.",
    )


class ChatResponse(BaseModel):
    answer: str
    backend: str = Field(..., description="LLM backend that produced the answer")
    grounded: bool = Field(
        ..., description="True if at least one source chunk was retrieved"
    )
    sources: list[SourceChunk]
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float


# --------------------------------------------------------------------------
# /health
# --------------------------------------------------------------------------
class ComponentHealth(BaseModel):
    status: Literal["ok", "degraded", "down"]
    detail: str = ""


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    app_env: str
    components: dict[str, ComponentHealth]


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    detail: str
