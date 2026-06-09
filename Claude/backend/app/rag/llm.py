"""LLM answer-generation backends.

Three interchangeable backends, selected by Settings.llm_backend:
  - "extractive": no LLM. Returns the top chunk plus source references.
                  Always works - ideal for first run, CI, and offline demos.
  - "ollama":     local LLM via an Ollama server.
  - "openai":     any OpenAI-compatible chat completions API.

Every backend exposes the same generate() signature. Failures in ollama/openai
fall back to extractive so the /chat endpoint never hard-fails.
"""
from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.rag.prompt import build_prompt, system_prompt

logger = get_logger(__name__)


def _extractive_answer(query: str, chunks: list[dict[str, Any]], language: str) -> str:
    """LLM-free answer: top chunk text + up to three source references."""
    if not chunks:
        if language == "en":
            return ("Sorry, that information is not available in the documents "
                    "I currently have.")
        return ("Maaf, informasi tersebut tidak tersedia dalam dokumen yang "
                "saya miliki saat ini.")
    top = chunks[0]
    refs = "; ".join(
        f"{c.get('title', 'Dokumen')}"
        + (f", hal. {c['page']}" if c.get("page") is not None else "")
        for c in chunks[:3]
    )
    return f"{top.get('text', '').strip()}\n\n[Sumber: {refs}]"


class LLMService:
    """Dispatches answer generation to the configured backend."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def backend(self) -> str:
        return self._settings.llm_backend

    def generate(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        language: str = "id",
        temperature: float | None = None,
        model: str | None = None,
    ) -> tuple[str, str]:
        """Generate an answer. Returns (answer_text, backend_actually_used).

        `model` is an optional per-request override (e.g. "llama3.1:8b"). When
        a model is specified, Ollama is used regardless of the server's default
        backend; this lets the UI's model dropdown actually switch models.
        Pass model="extractive" to force extractive (no LLM) for this request.
        """
        backend = self._settings.llm_backend
        temp = self._settings.llm_temperature if temperature is None else temperature

        # Resolve effective backend taking the per-request model override into account.
        if model == "extractive":
            return _extractive_answer(query, chunks, language), "extractive"
        effective_backend = backend
        if model and model != "extractive":
            # A real model name was passed -> always route through Ollama.
            effective_backend = "ollama"

        if effective_backend == "extractive":
            return _extractive_answer(query, chunks, language), "extractive"

        try:
            if effective_backend == "ollama":
                return self._generate_ollama(query, chunks, language, temp, model), "ollama"
            if effective_backend == "openai":
                return self._generate_openai(query, chunks, language, temp), "openai"
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "LLM backend '%s' failed (%s) - falling back to extractive.",
                effective_backend, exc,
            )
        return _extractive_answer(query, chunks, language), "extractive_fallback"

    # -- backends ----------------------------------------------------------
    def _generate_ollama(
        self, query: str, chunks: list[dict[str, Any]], language: str, temp: float,
        model: str | None = None,
    ) -> str:
        import httpx

        prompt = build_prompt(query, chunks, language)
        effective_model = model if (model and model != "extractive") else self._settings.ollama_model
        resp = httpx.post(
            f"{self._settings.ollama_base_url}/api/generate",
            json={
                "model": effective_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temp,
                    "num_predict": self._settings.llm_max_tokens,
                },
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        return (resp.json().get("response") or "").strip()

    def _generate_openai(
        self, query: str, chunks: list[dict[str, Any]], language: str, temp: float
    ) -> str:
        import httpx
        from app.rag.prompt import format_context

        if not self._settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        context = format_context(chunks)
        resp = httpx.post(
            f"{self._settings.openai_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.openai_api_key}"},
            json={
                "model": self._settings.openai_model,
                "temperature": temp,
                "max_tokens": self._settings.llm_max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt(language)},
                    {
                        "role": "user",
                        "content": f"=== KONTEKS / CONTEXT ===\n{context}\n\n"
                        f"PERTANYAAN / QUESTION: {query}",
                    },
                ],
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
