"""RAG API routes: /retrieve, /retrieve/debug, /chat.

Routes are intentionally thin - they validate input, call RagService, and map
the result onto response schemas. All orchestration lives in the service layer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.container import get_rag_service
from app.schemas.rag import (
    ChatRequest,
    ChatResponse,
    RetrievalDebugResponse,
    RetrieveRequest,
    RetrieveResponse,
    SourceChunk,
)
from app.services.rag_service import RagService

router = APIRouter()


def _require_ready(rag: RagService) -> None:
    """Raise 503 with an actionable message if the RAG pipeline is not loaded."""
    if not rag.ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "RAG pipeline is not ready.",
                "readiness": rag.readiness_detail(),
                "hint": "Check FAISS_INDEX_PATH / CHUNKS_META_PATH in .env and "
                "verify the index artefacts from "
                "03_vectorstore_rag_evaluation.ipynb exist.",
            },
        )


def _validate_query(text: str, settings: Settings) -> str:
    text = text.strip()
    if not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Query must not be empty.")
    if len(text) > settings.max_query_chars:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Query exceeds {settings.max_query_chars} characters.",
        )
    return text


@router.post("/retrieve", response_model=RetrieveResponse, tags=["retrieval"])
def retrieve(
    body: RetrieveRequest,
    rag: RagService = Depends(get_rag_service),
    settings: Settings = Depends(get_settings),
) -> RetrieveResponse:
    """Return the top-k chunks for a query, with similarity scores and timing."""
    _require_ready(rag)
    query = _validate_query(body.query, settings)
    result = rag.retrieve(
        query=query, top_k=body.top_k, score_threshold=body.score_threshold
    )
    return RetrieveResponse(
        query=result["query"],
        top_k=result["top_k"],
        embedding_model=result["embedding_model"],
        retrieval_latency_ms=result["timings"]["total_ms"],
        n_results=len(result["results"]),
        results=[SourceChunk(**c) for c in result["results"]],
    )


@router.get("/retrieve/debug", response_model=RetrievalDebugResponse,
            tags=["retrieval"])
def retrieve_debug(
    query: str,
    top_k: int | None = None,
    score_threshold: float | None = None,
    language: str = "id",
    rag: RagService = Depends(get_rag_service),
    settings: Settings = Depends(get_settings),
) -> RetrievalDebugResponse:
    """Verbose retrieval inspection for the thesis retrieval-debugging tool.

    Returns retrieved chunks, per-stage latency, index size, the embedding
    model, and the exact grounded prompt /chat would build for this query.
    """
    _require_ready(rag)
    query = _validate_query(query, settings)
    result = rag.retrieve_debug(
        query=query, top_k=top_k, score_threshold=score_threshold, language=language
    )
    timings = result["timings"]
    return RetrievalDebugResponse(
        query=result["query"],
        embedding_model=result["embedding_model"],
        use_e5_prefixes=settings.use_e5_prefixes,
        top_k=result["top_k"],
        score_threshold=result["score_threshold"],
        embedding_latency_ms=timings["embedding_ms"],
        search_latency_ms=timings["search_ms"],
        total_latency_ms=timings["total_ms"],
        index_size=result["index_size"],
        n_results=len(result["results"]),
        results=[SourceChunk(**c) for c in result["results"]],
        prompt_preview=result["prompt_preview"],
    )


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
def chat(
    body: ChatRequest,
    rag: RagService = Depends(get_rag_service),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """Full RAG turn: retrieve grounded context, then generate a cited answer."""
    _require_ready(rag)
    message = _validate_query(body.message, settings)
    result = rag.chat(
        message=message,
        top_k=body.top_k,
        temperature=body.temperature,
        language=body.language or "id",
        model=body.model,
    )
    return ChatResponse(
        answer=result["answer"],
        backend=result["backend"],
        grounded=result["grounded"],
        sources=[SourceChunk(**c) for c in result["sources"]],
        retrieval_latency_ms=result["retrieval_latency_ms"],
        generation_latency_ms=result["generation_latency_ms"],
        total_latency_ms=result["total_latency_ms"],
    )
