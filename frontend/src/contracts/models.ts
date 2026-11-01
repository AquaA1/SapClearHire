import {
  UserRole,
  EvidenceStatus,
  VerificationState,
  ReviewDecisionType,
  DocumentProcessingStatus,
  JobStatus,
  CriterionCategory,
  ApplicationStatus,
  ReviewFlagStatus,
  CorrectionRequestStatus,
} from './enums';

export interface User {
  id: string;
  email: string;
  role: UserRole;
  full_name: string;
  employer_id: string | null;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface CandidateRegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface JobCriterion {
  id: string;
  job_id: string;
  version: number;
  name: string;
  description: string | null;
  category: CriterionCategory | string;
  weight: number;
  is_active: boolean;
  created_at: string;
}

export interface Job {
  id: string;
  employer_id: string;
  title: string;
  description: string | null;
  department: string | null;
  status: JobStatus;
  criteria: JobCriterion[];
  created_at: string;
  updated_at: string;
  applicants_count?: number;
}

export interface JobCriterionCreate {
  name: string;
  description?: string | null;
  category: CriterionCategory | string;
  weight: number;
}

export interface JobCreateRequest {
  title: string;
  description?: string | null;
  department?: string | null;
  criteria: JobCriterionCreate[];
}

export interface JobListParams {
  status?: JobStatus;
  department?: string;
  limit?: number;
  offset?: number;
}

export interface Application {
  id: string;
  job_id: string;
  candidate_id: string;
  primary_document_id: string;
  status: ApplicationStatus | string;
  submitted_at: string;
  created_at: string;
  // Augmented UI fields
  job_title?: string;
  candidate_name?: string;
  candidate_email?: string;
  department?: string;
}

export interface CandidateSkill {
  id: string;
  skill_name: string;
  category: string | null;
  confidence: number;
  source_page: number | null;
  source_excerpt: string | null;
}

export interface EvidenceItem {
  id: string;
  claim_text: string;
  source_page: number;
  source_excerpt: string;
  confidence: number;
  grounding_verified: boolean;
  raw_metadata?: Record<string, any>;
}

export interface SubcriterionEvaluationItem {
  id: string;
  name: string;
  status: EvidenceStatus | string;
  confidence: number;
  source_excerpt?: string | null;
  source_page?: number | null;
  explanation?: string | null;
  citations?: Array<{
    document_id?: string | null;
    page_number?: number | null;
    exact_excerpt?: string;
    evidence_type?: string;
    grounding_verified?: boolean;
  }>;
  missing_reason?: string | null;
}

export interface CriterionEvaluationItem {
  criterion_id: string;
  criterion_name: string;
  category: string;
  status: EvidenceStatus;
  confidence: number;
  plain_language_explanation: string;
  source_excerpt: string | null;
  source_page: number | null;
  evidence_item_id: string | null;
  criterion_evidence_id?: string | null;
  verification_state?: VerificationState;
  human_decision?: string | null;
  decision_rationale?: string | null;
  decided_at?: string | null;
  subcriteria?: SubcriterionEvaluationItem[];
  missing_requirements?: string[];
}

export interface EvidenceCoverageSummary {
  total_criteria: number;
  supported_count: number;
  not_found_count: number;
  ambiguous_count: number;
  partially_supported_count?: number;
  required_total: number;
  required_supported_count: number;
  preferred_total: number;
  preferred_supported_count: number;
}

export interface Evaluation {
  id: string;
  application_id: string;
  version: number;
  job_criteria_version: number;
  extraction_run_id: string;
  overall_status: EvidenceStatus;
  coverage: EvidenceCoverageSummary;
  criteria_evaluations: CriterionEvaluationItem[];
  summary_notes: string | null;
  created_at: string;
}

export interface CandidateClarificationItem {
  id: string;
  candidate_statement: string;
  additional_document_id: string | null;
  status: CorrectionRequestStatus;
  created_at: string;
}

export interface ReviewDecisionItem {
  id: string;
  reviewer_id: string;
  reviewer_name?: string;
  decision: ReviewDecisionType;
  mandatory_rationale: string;
  previous_verification_state: string;
  new_verification_state: string;
  created_at: string;
}

export interface ReviewFlagSummary {
  id: string;
  application_id: string;
  criterion_evidence_id?: string | null;
  criterion_name: string | null;
  criterion_category: string | null;
  candidate_id: string;
  candidate_name: string | null;
  job_title: string | null;
  ai_status: EvidenceStatus | null;
  verification_state: VerificationState | null;
  flag_type: string;
  status: ReviewFlagStatus;
  priority: string;
  reason: string;
  created_at: string;
}

export interface ReviewCaseDetail {
  flag_id: string;
  flag_status: ReviewFlagStatus;
  priority: string;
  reason: string;
  assigned_to_user_id: string | null;
  application_id: string;
  application_status: ApplicationStatus;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  job_id: string;
  job_title: string;
  criterion_id: string;
  criterion_name: string;
  criterion_category: string;
  criterion_description: string | null;
  criterion_version: number;
  criterion_weight: number;
  criterion_evidence_id: string;
  ai_status: EvidenceStatus;
  ai_confidence: number;
  ai_reasoning: string | null;
  verification_state: VerificationState;
  source_excerpt: string | null;
  source_page: number | null;
  evidence_item_id: string | null;
  claim_text: string | null;
  clarifications: CandidateClarificationItem[];
  decisions: ReviewDecisionItem[];
  created_at: string;
  resolved_at: string | null;
}

export interface AuditEvent {
  id: string;
  sequence_number: number;
  timestamp: string;
  actor_id: string | null;
  actor_role: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  entity_version: number | null;
  prior_state: Record<string, any> | null;
  new_state: Record<string, any> | null;
  details: Record<string, any>;
  ip_address: string | null;
  previous_hash: string | null;
  event_hash: string;
  is_verified: boolean;
}

export interface AuditVerificationReport {
  is_valid: boolean;
  total_events: number;
  verified_events: number;
  chain_head_hash: string | null;
  discrepancy_type: string | null;
  error: string | null;
  broken_event_id: string | null;
  broken_sequence_number: number | null;
  tamper_evidence_disclaimer: string;
}

export interface ScreeningMetrics {
  total_evaluations: number;
  correct_evaluations: number;
  true_positives: number;
  true_negatives: number;
  ambiguous_identified: number;
  false_positives: number;
  false_negatives: number;
  accuracy: number;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
}

export interface CriterionComparison {
  criterion_name: string;
  ground_truth: string;
  baseline_status: string;
  clearhire_status: string;
  baseline_correct: boolean;
  clearhire_correct: boolean;
  notes: string;
}

export interface CandidateBenchmarkResult {
  case_id: string;
  candidate_name: string;
  scenario: string;
  ground_truth_overall: string;
  baseline_overall: string;
  clearhire_overall: string;
  baseline_correct: boolean;
  clearhire_correct: boolean;
  criterion_comparisons: CriterionComparison[];
  summary_findings: string;
}

export interface BenchmarkReport {
  is_synthetic: boolean;
  benchmark_disclaimer: string;
  sample_size: number;
  total_criteria_evaluations: number;
  baseline_metrics: ScreeningMetrics;
  clearhire_metrics: ScreeningMetrics;
  candidate_results: CandidateBenchmarkResult[];
  keyword_baseline_misses_breakdown: Record<string, number>;
  clearhire_findings: string[];
  extraction_limitations: string[];
}

export interface DocumentUploadResponse {
  id: string;
  file_name: string;
  file_hash: string;
  file_size_bytes: number;
  processing_status: DocumentProcessingStatus;
  created_at: string;
}

export interface DocumentProcessingError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface DocumentStatusResponse {
  id: string;
  file_name: string;
  processing_status: DocumentProcessingStatus;
  page_count: number | null;
  extracted_text_by_page: Record<string, string>;
  processing_error: DocumentProcessingError | null;
  created_at: string;
  updated_at: string;
  file_hash?: string;
  file_size_bytes?: number;
  mime_type?: string;
}

export interface ExtractionRunResponse {
  id: string;
  document_id: string;
  run_number: number;
  provider: string;
  model_name: string;
  status: DocumentProcessingStatus;
  error_message: string | null;
  skills: CandidateSkill[];
  evidence_items: EvidenceItem[];
  started_at: string;
  completed_at: string | null;
  raw_output?: Record<string, any>;
}

export interface ProfileSkillItem {
  id: string;
  skill_name: string;
  category: string | null;
  confidence: number;
  source_page: number | null;
  source_excerpt: string | null;
}

export interface CandidateProfileSkillsResponse {
  candidate_id: string;
  total_skills: number;
  skills: ProfileSkillItem[];
}

