import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import CriterionCategory, EvidenceStatus, JobStatus, VerificationState
from app.schemas.review import CandidateClarificationItem, ReviewDecisionItem

# ============================================================================
# Job & Criteria Schemas
# ============================================================================


class JobCriterionCreate(BaseModel):
    """Payload to define an evaluation criterion on a job requisition."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Criterion name (e.g. Python, Microservices)"
    )
    description: str | None = Field(
        default=None, description="Detailed requirement definition or benchmark"
    )
    category: CriterionCategory = Field(
        default=CriterionCategory.REQUIRED, description="'required' or 'preferred'"
    )
    weight: float = Field(default=1.0, ge=0.0, description="Relative criterion importance weight")


class JobCriterionResponse(BaseModel):
    """Response representing an explicit versioned job criterion."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    version: int
    name: str
    description: str | None = None
    category: str
    weight: float
    is_active: bool
    created_at: datetime


class JobCreateRequest(BaseModel):
    """Payload to create an employer job posting with initial criteria."""

    title: str = Field(..., min_length=1, max_length=255, description="Job title")
    description: str | None = Field(default=None, description="Job summary description")
    department: str | None = Field(default=None, description="Organizational unit or team")
    criteria: list[JobCriterionCreate] = Field(
        default_factory=list, description="Initial list of screening criteria"
    )


class JobResponse(BaseModel):
    """Response representing a job requisition with its current criteria version."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employer_id: uuid.UUID
    title: str
    description: str | None = None
    department: str | None = None
    status: JobStatus
    criteria: list[JobCriterionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Application Schemas
# ============================================================================


class ApplicationCreateRequest(BaseModel):
    """Payload to apply for a job requisition with an uploaded resume document."""

    job_id: uuid.UUID = Field(..., description="Target job requisition ID")
    primary_document_id: uuid.UUID = Field(..., description="Uploaded resume document ID")
    auto_evaluate: bool = Field(
        default=False,
        description="Whether to automatically enqueue background extraction and evaluation pipeline.",
    )


class ApplicationResponse(BaseModel):
    """Response representing a candidate job application."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str | None = None
    candidate_email: str | None = None
    primary_document_id: uuid.UUID
    status: str
    submitted_at: datetime
    created_at: datetime


# ============================================================================
# Evaluation Schemas (Coverage Counts, Never Opaque Scores)
# ============================================================================


class EvaluationCreateRequest(BaseModel):
    """Payload to trigger candidate evidence evaluation against job criteria."""

    application_id: uuid.UUID = Field(..., description="Candidate application ID")


class SubcriterionEvaluationItem(BaseModel):
    """Evaluation result for an individual subrequirement of a compound criterion."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: EvidenceStatus
    confidence: float = 1.0
    source_excerpt: str | None = None
    source_page: int | None = None
    explanation: str | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    missing_reason: str | None = None


class CriterionEvaluationItem(BaseModel):
    """Evaluation result for an individual job criterion."""

    model_config = ConfigDict(from_attributes=True)

    criterion_id: uuid.UUID
    criterion_name: str
    category: str
    status: EvidenceStatus
    confidence: float
    plain_language_explanation: str
    source_excerpt: str | None = None
    source_page: int | None = None
    evidence_item_id: uuid.UUID | None = None
    criterion_evidence_id: uuid.UUID | None = None
    verification_state: VerificationState = VerificationState.UNVERIFIED
    human_decision: str | None = None
    decision_rationale: str | None = None
    decided_at: datetime | None = None
    subcriteria: list[SubcriterionEvaluationItem] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    clarifications: list[CandidateClarificationItem] = Field(default_factory=list)
    decisions: list[ReviewDecisionItem] = Field(default_factory=list)


class EvidenceCoverageSummary(BaseModel):
    """Factual evidence coverage counts (strictly non-probabilistic)."""

    total_criteria: int
    supported_count: int
    not_found_count: int
    ambiguous_count: int
    partially_supported_count: int = 0
    required_total: int
    required_supported_count: int
    preferred_total: int
    preferred_supported_count: int


class EvaluationResponse(BaseModel):
    """Complete evaluation report for a candidate application."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    version: int
    job_criteria_version: int
    extraction_run_id: uuid.UUID
    overall_status: EvidenceStatus
    coverage: EvidenceCoverageSummary
    criteria_evaluations: list[CriterionEvaluationItem] = Field(default_factory=list)
    summary_notes: str | None = None
    created_at: datetime


# ============================================================================
# Candidate Profile Skills Schemas
# ============================================================================


class ProfileSkillItem(BaseModel):
    """Skill in candidate's extracted profile inventory."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill_name: str
    category: str | None = None
    confidence: float
    source_page: int | None = None
    source_excerpt: str | None = None


class CandidateProfileSkillsResponse(BaseModel):
    """Response listing all verified candidate skills from uploaded documents."""

    candidate_id: uuid.UUID
    total_skills: int
    skills: list[ProfileSkillItem] = Field(default_factory=list)
