from app.core.config import get_settings
from app.integrations.llm.base import BaseLLMProvider
from app.integrations.llm.fake import FakeLLMProvider
from app.integrations.llm.real import HTTPClientLLMProvider
from app.integrations.llm.schemas import (
    CandidateClaim,
    EvidenceStatus,
    ExtractedEducation,
    ExtractedExperience,
    ExtractedProject,
    ExtractedResumeProfile,
    ExtractedSkill,
    ExtractionResult,
    SourceQuote,
)


def get_llm_provider() -> BaseLLMProvider:
    """Factory creating configured LLM provider according to application settings."""
    settings = get_settings()
    if settings.LLM_PROVIDER == "fake":
        return FakeLLMProvider()

    # Real configurable HTTP client provider (e.g. OpenAI / Anthropic / Gemini gateway)
    return HTTPClientLLMProvider(
        api_key=settings.LLM_API_KEY,
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL,
        provider_name=settings.LLM_PROVIDER,
    )


__all__ = [
    "BaseLLMProvider",
    "FakeLLMProvider",
    "HTTPClientLLMProvider",
    "CandidateClaim",
    "EvidenceStatus",
    "ExtractedEducation",
    "ExtractedExperience",
    "ExtractedProject",
    "ExtractedResumeProfile",
    "ExtractedSkill",
    "ExtractionResult",
    "SourceQuote",
    "get_llm_provider",
]
