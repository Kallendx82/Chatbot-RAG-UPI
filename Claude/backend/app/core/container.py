"""Application dependency container.

Holds the singletons (embedder, vector store, LLM, RAG service) that are
expensive to build. Created once at startup, stored on app.state, and exposed
to routes via FastAPI dependencies.
"""
from __future__ import annotations

from fastapi import Request

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.rag.embedder import Embedder
from app.rag.llm import LLMService
from app.rag.vectorstore import FaissVectorStore
from app.services.rag_service import RagService

logger = get_logger(__name__)


class Container:
    """Owns the long-lived application singletons."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embedder = Embedder(settings)
        self.store = FaissVectorStore(settings, self.embedder)
        self.llm = LLMService(settings)
        self.rag = RagService(settings, self.embedder, self.store, self.llm)

    def startup(self) -> None:
        """Load heavy resources. Failures are recorded, not raised, so the app
        still boots and /health can report what is wrong."""
        logger.info("Container startup: loading embedder and vector store...")
        self.embedder.load()
        self.store.load()
        if self.rag.ready:
            logger.info("RAG pipeline ready (index size: %d).", self.store.size)
        else:
            logger.warning(
                "RAG pipeline NOT ready: %s. The API will serve /health but "
                "retrieval endpoints will return 503 until this is fixed.",
                self.rag.readiness_detail(),
            )


def build_container() -> Container:
    """Construct the container from cached settings."""
    return Container(get_settings())


# --- FastAPI dependency accessors -------------------------------------------
def get_container(request: Request) -> Container:
    return request.app.state.container


def get_rag_service(request: Request) -> RagService:
    return request.app.state.container.rag
