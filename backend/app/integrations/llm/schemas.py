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


class ExtractedSkill(BaseModel):
    """Structured skill qualification extracted from resume."""

    skill_name: str = Field(..., min_length=1, description="Normalized skill name")
    category: str | None = Field(default=None, description="Domain or technology category")
    years_of_experience: float | None = Field(
        default=None, ge=0.0, description="Estimated years of experience if mentioned"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Model extraction confidence score"
    )
    source_quote: SourceQuote = Field(..., description="Exact quote grounding this skill")


class ExtractedExperience(BaseModel):
    """Structured employment or work experience claim."""

    job_title: str = Field(..., min_length=1, description="Job title or role")
    company: str | None = Field(default=None, description="Employer or organization name")
    start_date: str | None = Field(
        default=None, description="Start date string (e.g. YYYY-MM, YYYY, or text)"
    )
    end_date: str | None = Field(
        default=None, description="End date string (e.g. YYYY-MM, YYYY, 'Present')"
    )
    is_current: bool = Field(default=False, description="Whether this is a current position")
    responsibilities: list[str] = Field(
        default_factory=list, description="Key duties and achievements"
    )
    source_quote: SourceQuote = Field(..., description="Exact quote grounding this experience")


class ExtractedProject(BaseModel):
    """Structured project or portfolio claim."""

    project_name: str = Field(..., min_length=1, description="Name or title of project")
    description: str | None = Field(default=None, description="Brief summary of project scope")
    technologies: list[str] = Field(
        default_factory=list, description="Tools or languages used in the project"
    )
    source_quote: SourceQuote = Field(..., description="Exact quote grounding this project")


class ExtractedEducation(BaseModel):
    """Structured academic or credential qualification."""

    institution: str = Field(..., min_length=1, description="University, college, or school")
    degree: str | None = Field(default=None, description="Degree or certificate name")
    field_of_study: str | None = Field(default=None, description="Major or area of specialization")
    graduation_date: str | None = Field(default=None, description="Graduation year or date")
    source_quote: SourceQuote = Field(..., description="Exact quote grounding this education")


class ExtractedResumeProfile(BaseModel):
    """Complete structured profile parsed from resume text."""

    candidate_name: str | None = Field(
        default=None, description="Candidate name if explicitly listed"
    )
    skills: list[ExtractedSkill] = Field(default_factory=list)
    experiences: list[ExtractedExperience] = Field(default_factory=list)
    projects: list[ExtractedProject] = Field(default_factory=list)
    education: list[ExtractedEducation] = Field(default_factory=list)
    detected_conflicts: list[str] = Field(
        default_factory=list,
        description="Any internal contradictions or anomalies detected by model",
    )


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
    """Result of structured claim and profile extraction over a document."""

    claims: list[CandidateClaim] = Field(default_factory=list)
    profile: ExtractedResumeProfile | None = Field(default=None)
    document_hash: str
    provider: str
    model_name: str
    prompt_version: str = "v1"
