"""Health and readiness endpoints.

/health performs real component checks (embedder, vector store, LLM backend)
and reports a per-component breakdown. Useful for the admin dashboard's
"vectorstore status" card in a later slice, and for Docker healthchecks.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.container import Container, get_container
from app.schemas.rag import ComponentHealth, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health(container: Container = Depends(get_container)) -> HealthResponse:
    """Report overall and per-component health.

    status: "ok"       - everything ready
            "degraded" - app runs but RAG retrieval is unavailable
            "down"     - should not normally happen (process would not serve)
    """
    components: dict[str, ComponentHealth] = {}

    # Embedder
    if container.embedder.ready:
        components["embedder"] = ComponentHealth(
            status="ok",
            detail=f"model={container.embedder.model_name} "
            f"dim={container.embedder.dimension}",
        )
    else:
        components["embedder"] = ComponentHealth(
            status="down",
            detail=container.embedder.load_error or "not loaded",
        )

    # Vector store
    if container.store.ready:
        info = container.store.info
        components["vector_store"] = ComponentHealth(
            status="ok",
            detail=f"vectors={container.store.size} "
            f"built_with={info.get('embedding_model', 'unknown')}",
        )
    else:
        components["vector_store"] = ComponentHealth(
            status="down",
            detail=container.store.load_error or "not loaded",
        )

    # LLM backend (configuration check only - no network call here)
    backend = container.settings.llm_backend
    components["llm_backend"] = ComponentHealth(
        status="ok",
        detail=f"backend={backend}"
        + ("" if backend != "openai"
           else f" key_set={bool(container.settings.openai_api_key)}"),
    )

    rag_ready = container.embedder.ready and container.store.ready
    overall = "ok" if rag_ready else "degraded"

    return HealthResponse(
        status=overall,
        app_env=container.settings.app_env,
        components=components,
    )
