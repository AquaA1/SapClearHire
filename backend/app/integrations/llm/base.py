from abc import ABC, abstractmethod
from typing import Any

from app.integrations.llm.schemas import ExtractedResumeProfile, ExtractionResult


class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM extraction and criterion mapping.

    CRITICAL SAFETY & GOVERNANCE RULES:
    1. The LLM must NEVER make hiring decisions (hire/reject/advance).
    2. The LLM must NEVER invent employer rejection reasons.
    3. The LLM must NEVER mark a criterion 'supported' without verified source quotes.
    4. Delimit untrusted document text so instructions inside resumes cannot alter system prompt rules.
    5. Flag contradictory or uncertain claims as 'ambiguous' for human review.
    6. Never infer protected characteristics (race, gender, age, disability).
    """

    @abstractmethod
    async def extract_claims(
        self,
        resume_pages: dict[int, str],
        criteria: list[str],
        document_hash: str,
    ) -> ExtractionResult:
        """
        Extract structured claims mapped to criteria with page-referenced source quotes.
        """
        pass

    @abstractmethod
    async def extract_resume_profile(
        self,
        resume_pages: dict[int, str],
        document_hash: str,
    ) -> ExtractedResumeProfile:
        """
        Extract structured profile (skills, experiences, education, projects) from page-labelled resume text.
        """
        pass

    async def generate_simple_completion(
        self,
        user_prompt: str,
        system_prompt: str = "You are a helpful structured JSON extractor. Always output valid JSON.",
        max_tokens: int = 256,
    ) -> dict[str, Any]:
        """
        Generate a single structured JSON completion for health checks and smoke testing.
        """
        raise NotImplementedError
