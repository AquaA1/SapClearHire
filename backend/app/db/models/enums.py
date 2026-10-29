from enum import StrEnum


class EvidenceStatus(StrEnum):
    """AI-evaluated status of evidence mapped to explicit job criteria."""

    SUPPORTED = "supported"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"


class VerificationState(StrEnum):
    """Human and candidate verification state for a criterion evidence item."""

    UNVERIFIED = "unverified"
    CANDIDATE_CLARIFIED = "candidate_clarified"
    HUMAN_VERIFIED = "human_verified"
    HUMAN_REJECTED = "human_rejected"


class ReviewDecisionType(StrEnum):
    """Authorized human reviewer decision options."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REQUESTED_CLARIFICATION = "requested_clarification"


class DocumentProcessingStatus(StrEnum):
    """Lifecycle processing status of an uploaded document."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(StrEnum):
    """Lifecycle status of a job posting."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ApplicationStatus(StrEnum):
    """Screening lifecycle status of a candidate job application."""

    SUBMITTED = "submitted"
    SCREENING = "screening"
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"


class ReviewFlagStatus(StrEnum):
    """Status of a human review escalation flag."""

    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class CorrectionRequestStatus(StrEnum):
    """Status of candidate-provided clarification or dispute."""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
