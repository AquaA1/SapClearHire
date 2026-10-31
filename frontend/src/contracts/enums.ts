export enum UserRole {
  CANDIDATE = 'candidate',
  EMPLOYER_ADMIN = 'employer_admin',
  REVIEWER = 'reviewer',
  SYSTEM_AUDITOR = 'system_auditor',
}

export enum EvidenceStatus {
  SUPPORTED = 'supported',
  NOT_FOUND = 'not_found',
  AMBIGUOUS = 'ambiguous',
}

export enum VerificationState {
  UNVERIFIED = 'unverified',
  CANDIDATE_CLARIFIED = 'candidate_clarified',
  HUMAN_VERIFIED = 'human_verified',
  HUMAN_REJECTED = 'human_rejected',
}

export enum ReviewDecisionType {
  ACCEPTED = 'accepted',
  REJECTED = 'rejected',
  REQUESTED_CLARIFICATION = 'requested_clarification',
}

export enum DocumentProcessingStatus {
  QUEUED = 'queued',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export enum JobStatus {
  DRAFT = 'draft',
  ACTIVE = 'active',
  ARCHIVED = 'archived',
}

export enum CriterionCategory {
  REQUIRED = 'required',
  PREFERRED = 'preferred',
}

export enum ApplicationStatus {
  SUBMITTED = 'submitted',
  SCREENING = 'screening',
  NEEDS_REVIEW = 'needs_review',
  REVIEWED = 'reviewed',
}

export enum ReviewFlagStatus {
  PENDING = 'pending',
  UNDER_REVIEW = 'under_review',
  RESOLVED = 'resolved',
  DISMISSED = 'dismissed',
}

export enum CorrectionRequestStatus {
  SUBMITTED = 'submitted',
  UNDER_REVIEW = 'under_review',
  ACCEPTED = 'accepted',
  REJECTED = 'rejected',
}
