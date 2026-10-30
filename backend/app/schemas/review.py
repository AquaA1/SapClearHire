import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import (
    ApplicationStatus,
    CorrectionRequestStatus,
    EvidenceStatus,
    ReviewDecisionType,
    ReviewFlagStatus,
    VerificationState,
)


class ReviewFlagCreateRequest(BaseModel):
    """Payload to raise evaluation criteria for human review escalation."""

    application_id: uuid.UUID = Field(..., description="Target candidate application ID")
    criterion_evidence_id: uuid.UUID | None = Field(
        default=None,
        description="Optional specific criterion evidence ID to flag. If omitted, auto-flags according to rules.",
    )
    flag_preferred: bool = Field(
        default=False,
        description="Whether to flag ambiguous/not_found preferred criteria. Default false (flags only required).",
    )
    reason: str | None = Field(
        default=None,
        description="Optional custom explanatory reason for the review escalation.",
    )
    priority: str = Field(
        default="normal",
        description="Priority level: 'normal', 'high', or 'urgent'.",
    )
    assigned_to_user_id: uuid.UUID | None = Field(
        default=None,
        description="Optional reviewer user ID to assign this review case to.",
    )


class ReviewFlagResponse(BaseModel):
    """Response representing an individual review flag."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    criterion_evidence_id: uuid.UUID | None = None
    flag_type: str
    status: ReviewFlagStatus
    priority: str
    reason: str
    assigned_to_user_id: uuid.UUID | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class ReviewFlagBatchResponse(BaseModel):
    """Response returned when flagging criteria on an application."""

    application_id: uuid.UUID
    total_flagged: int
    flags: list[ReviewFlagResponse] = Field(default_factory=list)


class ReviewFlagSummaryResponse(BaseModel):
    """Summary representation of a review case in a reviewer's assignment queue."""

    id: uuid.UUID
    application_id: uuid.UUID
    criterion_name: str | None = None
    criterion_category: str | None = None
    candidate_id: uuid.UUID
    candidate_name: str | None = None
    job_title: str | None = None
    ai_status: EvidenceStatus | None = None
    verification_state: VerificationState | None = None
    flag_type: str
    status: ReviewFlagStatus
    priority: str
    reason: str
    created_at: datetime


class CandidateClarificationItem(BaseModel):
    """Item representing candidate-submitted clarification or supplementary evidence."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_statement: str
    additional_document_id: uuid.UUID | None = None
    status: CorrectionRequestStatus
    created_at: datetime


class ReviewDecisionItem(BaseModel):
    """Historical record of an authorized reviewer decision."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reviewer_id: uuid.UUID
    decision: ReviewDecisionType
    mandatory_rationale: str
    previous_verification_state: str
    new_verification_state: str
    created_at: datetime


class ReviewCaseDetailResponse(BaseModel):
    """Comprehensive review case details containing criterion, evidence, and clarifications."""

    flag_id: uuid.UUID
    flag_status: ReviewFlagStatus
    priority: str
    reason: str
    assigned_to_user_id: uuid.UUID | None = None

    application_id: uuid.UUID
    application_status: ApplicationStatus
    candidate_id: uuid.UUID
    candidate_name: str
    candidate_email: str
    job_id: uuid.UUID
    job_title: str

    criterion_id: uuid.UUID
    criterion_name: str
    criterion_category: str
    criterion_description: str | None = None
    criterion_version: int
    criterion_weight: float

    criterion_evidence_id: uuid.UUID
    ai_status: EvidenceStatus
    ai_confidence: float
    ai_reasoning: str | None = None
    verification_state: VerificationState
    source_excerpt: str | None = None
    source_page: int | None = None
    evidence_item_id: uuid.UUID | None = None
    claim_text: str | None = None

    clarifications: list[CandidateClarificationItem] = Field(default_factory=list)
    decisions: list[ReviewDecisionItem] = Field(default_factory=list)
    created_at: datetime
    resolved_at: datetime | None = None


class ReviewDecisionRequest(BaseModel):
    """Payload to record an authorized human reviewer verdict."""

    decision: ReviewDecisionType = Field(
        ...,
        description="Reviewer decision: 'accepted', 'rejected', or 'requested_clarification'.",
    )
    mandatory_rationale: str = Field(
        ...,
        min_length=1,
        description="Mandatory explanatory rationale. Cannot be empty or whitespace.",
    )


class ReviewDecisionResponse(BaseModel):
    """Response representing a recorded reviewer verdict."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    criterion_evidence_id: uuid.UUID | None = None
    reviewer_id: uuid.UUID
    decision: ReviewDecisionType
    mandatory_rationale: str
    previous_verification_state: str
    new_verification_state: str
    flag_status: ReviewFlagStatus
    created_at: datetime


class CandidateClarificationRequest(BaseModel):
    """Payload for candidate to contest or clarify evidence for a criterion."""

    criterion_evidence_id: uuid.UUID = Field(
        ..., description="Criterion evidence ID being clarified or contested"
    )
    candidate_statement: str = Field(
        ...,
        min_length=1,
        description="Candidate's statement, explanation, or context contesting the evaluation",
    )
    additional_document_id: uuid.UUID | None = Field(
        default=None,
        description="Optional ID of an additional uploaded document containing supporting evidence",
    )


class CandidateClarificationResponse(BaseModel):
    """Response returned upon successful submission of candidate clarification."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    candidate_id: uuid.UUID
    criterion_evidence_id: uuid.UUID | None = None
    candidate_statement: str
    additional_document_id: uuid.UUID | None = None
    status: CorrectionRequestStatus
    new_verification_state: VerificationState
    created_at: datetime
