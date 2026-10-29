import re
import uuid

from app.integrations.llm.base import BaseLLMProvider
from app.integrations.llm.schemas import (
    CandidateClaim,
    EvidenceStatus,
    ExtractionResult,
    SourceQuote,
)


class FakeLLMProvider(BaseLLMProvider):
    """
    Deterministic LLM provider for tests, local development, and offline evaluation.
    Matches criteria against resume text and yields grounded quotes with verifiable page references.
    """

    def __init__(self, provider_name: str = "fake", model_name: str = "deterministic-stub-v1"):
        self.provider_name = provider_name
        self.model_name = model_name

    async def extract_claims(
        self,
        resume_pages: dict[int, str],
        criteria: list[str],
        document_hash: str,
    ) -> ExtractionResult:
        claims: list[CandidateClaim] = []

        for criterion in criteria:
            criterion_clean = criterion.strip().lower()
            found_quote: SourceQuote | None = None
            is_ambiguous = False

            # Search across pages in order
            for page_num, text in sorted(resume_pages.items()):
                # Case-insensitive search for criterion keyword or pattern
                match = re.search(re.escape(criterion_clean), text, re.IGNORECASE)
                if match:
                    # Find enclosing sentence or window for grounded excerpt
                    start_idx = max(0, match.start() - 40)
                    end_idx = min(len(text), match.end() + 60)
                    excerpt = text[start_idx:end_idx].strip()

                    # Check for ambiguity indicators near the match
                    context_snippet = text[
                        max(0, match.start() - 100) : min(len(text), match.end() + 100)
                    ].lower()
                    if any(
                        term in context_snippet
                        for term in ["familiar with", "basic", "exposure", "learning", "student"]
                    ):
                        is_ambiguous = True

                    found_quote = SourceQuote(
                        page_number=page_num,
                        exact_excerpt=excerpt,
                        start_char=start_idx,
                        end_char=end_idx,
                    )
                    break

            if found_quote and is_ambiguous:
                claims.append(
                    CandidateClaim(
                        claim_id=str(uuid.uuid4()),
                        criterion_name=criterion,
                        status=EvidenceStatus.AMBIGUOUS,
                        confidence=0.65,
                        source_quotes=[found_quote],
                        rationale=f"Found mention of '{criterion}' with qualifying language indicating limited depth.",
                    )
                )
            elif found_quote:
                claims.append(
                    CandidateClaim(
                        claim_id=str(uuid.uuid4()),
                        criterion_name=criterion,
                        status=EvidenceStatus.SUPPORTED,
                        confidence=0.95,
                        source_quotes=[found_quote],
                        rationale=f"Direct evidence found on page {found_quote.page_number}.",
                    )
                )
            else:
                claims.append(
                    CandidateClaim(
                        claim_id=str(uuid.uuid4()),
                        criterion_name=criterion,
                        status=EvidenceStatus.NOT_FOUND,
                        confidence=0.90,
                        source_quotes=[],
                        rationale=f"No direct evidence for '{criterion}' identified in uploaded document.",
                    )
                )

        return ExtractionResult(
            claims=claims,
            document_hash=document_hash,
            provider=self.provider_name,
            model_name=self.model_name,
        )
