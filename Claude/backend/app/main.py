"""FastAPI application entry point.

Wires together: settings, logging, the dependency container (loaded at
startup via the lifespan handler), CORS, exception handling, and routers.

Run locally:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health_routes, rag_routes
from app.core.config import get_settings
from app.core.container import build_container
from app.core.logging import get_logger, setup_logging

settings = get_settings()
setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown: build the container and load heavy RAG resources once."""
    logger.info("Starting %s (env=%s)", settings.app_name, settings.app_env)
    container = build_container()
    container.startup()  # loads embedder + FAISS index; never raises
    app.state.container = container
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend core + RAG integration for the UPI RAG chatbot "
    "(thesis: Rancang Bangun Chatbot Sumber Informasi Sivitas UPI Berbasis RAG).",
    lifespan=lifespan,
)

# --- CORS: the Next.js frontend (later slice) will call this API ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Uniform error envelope -------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all so the client always receives JSON, never a bare stack trace."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error.", "path": request.url.path},
    )


# --- Routers ----------------------------------------------------------------
# Health is unprefixed so Docker/uptime checks can hit /health directly.
app.include_router(health_routes.router)
app.include_router(rag_routes.router, prefix=settings.api_prefix)


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    """Tiny landing payload so a bare GET / is not a 404."""
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "api_prefix": settings.api_prefix,
    }
