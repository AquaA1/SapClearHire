from enum import Enum

from pydantic import BaseModel, Field


class EvidenceStatus(str, Enum):
    """Categorization of evidence mapped to explicit job criteria."""

    SUPPORTED = "supported"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"


class SourceQuote(BaseModel):
    """Direct excerpt from candidate resume with exact page number reference."""

    page_number: int = Field(..., ge=1, description="1-indexed resume page number")
    exact_excerpt: str = Field(
        ..., min_length=1, description="Verbatim text extracted from document"
    )
    start_char: int | None = Field(
        default=None, description="Starting character offset if available"
    )
    end_char: int | None = Field(default=None, description="Ending character offset if available")


class CandidateClaim(BaseModel):
    """Structured claim extracted from resume and mapped to a criterion."""

    claim_id: str = Field(..., description="Unique claim identifier")
    criterion_name: str = Field(..., description="Target job requirement or skill")
    status: EvidenceStatus = Field(..., description="Supported, not_found, or ambiguous")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    source_quotes: list[SourceQuote] = Field(
        default_factory=list, description="Grounding excerpts validating the claim"
    )
    rationale: str = Field(..., description="Objective explanation linking evidence to criterion")


class ExtractionResult(BaseModel):
    """Result of structured claim extraction over a document."""

    claims: list[CandidateClaim]
    document_hash: str
    provider: str
    model_name: str
