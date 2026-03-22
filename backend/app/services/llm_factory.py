"""Provider-aware LLM factory for OpenAI-compatible chat models."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import settings

SUPPORTED_LLM_PROVIDERS = {"openai", "gemini"}


def normalize_llm_provider(provider: str | None) -> str:
    normalized = (provider or "gemini").strip().lower()
    if normalized not in SUPPORTED_LLM_PROVIDERS:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    return normalized


def default_model_for_provider(provider: str) -> str:
    normalized = normalize_llm_provider(provider)
    if normalized == "gemini":
        return settings.GEMINI_DEFAULT_MODEL
    return settings.OPENAI_DEFAULT_MODEL


def create_chat_model(
    *,
    provider: str,
    model: str | None,
    temperature: float,
) -> ChatOpenAI:
    normalized = normalize_llm_provider(provider)
    selected_model = (model or default_model_for_provider(normalized)).strip()

    if normalized == "gemini":
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        return ChatOpenAI(
            model=selected_model,
            temperature=temperature,
            api_key=settings.GEMINI_API_KEY,
            base_url=settings.GEMINI_OPENAI_BASE_URL,
            default_headers={"x-goog-api-client": "aeroswarm-oai/0.1.0"},
        )

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")
    return ChatOpenAI(
        model=selected_model,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
    )
