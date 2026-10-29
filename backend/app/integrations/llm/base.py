from abc import ABC, abstractmethod

from app.integrations.llm.schemas import ExtractionResult


class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM extraction and criterion mapping.

    CRITICAL SAFETY & GOVERNANCE RULES:
    1. The LLM must NEVER make hiring decisions (hire/reject/advance).
    2. The LLM must NEVER invent employer rejection reasons.
    3. The LLM must NEVER mark a criterion 'supported' without verified source quotes.
    4. Delimit untrusted document text so instructions inside resumes cannot alter system prompt rules.
    5. Flag contradictory or uncertain claims as 'ambiguous' for human review.
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

        Args:
            resume_pages: Mapping of 1-indexed page number to raw page text.
            criteria: List of target job requirements / evaluation criteria.
            document_hash: SHA-256 hash of the source document for provenance.

        Returns:
            ExtractionResult containing structured, grounded claims.
        """
        pass
