from app.core.config import get_settings
from app.integrations.llm.base import BaseLLMProvider
from app.integrations.llm.fake import FakeLLMProvider
from app.integrations.llm.schemas import (
    CandidateClaim,
    EvidenceStatus,
    ExtractionResult,
    SourceQuote,
)


def get_llm_provider() -> BaseLLMProvider:
    """Factory creating configured LLM provider according to application settings."""
    settings = get_settings()
    if settings.LLM_PROVIDER == "fake":
        return FakeLLMProvider()

    # Extension point for production LLM adapters (OpenAI, Anthropic, Google Vertex / Gemini)
    # Return fake fallback for Phase 1 boilerplate to ensure zero external startup dependencies
    return FakeLLMProvider(provider_name=settings.LLM_PROVIDER, model_name=settings.LLM_MODEL)


__all__ = [
    "BaseLLMProvider",
    "FakeLLMProvider",
    "CandidateClaim",
    "EvidenceStatus",
    "ExtractionResult",
    "SourceQuote",
    "get_llm_provider",
]
