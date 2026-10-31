/**
 * ClearHire Review Workflow API Service
 * Communicates directly with backend FastAPI review endpoints:
 * - GET  /api/v1/review-flags
 * - POST /api/v1/review-flags
 * - GET  /api/v1/reviews/{id}
 * - POST /api/v1/reviews/{id}/decision
 * - POST /api/v1/applications/{id}/clarifications
 * - POST /api/v1/reviews/{id}/clarification
 */

import { apiClient } from './client';
import {
  ReviewFlagSummary,
  ReviewCaseDetail,
  ReviewDecisionItem,
  CandidateClarificationItem,
} from '../../contracts/models';
import { ReviewFlagStatus, ReviewDecisionType } from '../../contracts/enums';

export interface ReviewFlagListParams {
  status?: ReviewFlagStatus | string;
  application_id?: string;
}

export interface ReviewDecisionPayload {
  decision: ReviewDecisionType | string;
  mandatory_rationale: string;
}

export interface CandidateClarificationPayload {
  criterion_evidence_id: string;
  candidate_statement: string;
  additional_document_id?: string | null;
}

export interface CreateReviewFlagsPayload {
  application_id: string;
  criterion_evidence_id?: string;
  flag_preferred?: boolean;
  reason?: string;
  priority?: string;
  assigned_to_user_id?: string;
}

class ReviewService {
  /**
   * List assigned review cases (accessible to Reviewers, Employer Admins, System Auditors).
   */
  async listReviewFlags(params?: ReviewFlagListParams): Promise<ReviewFlagSummary[]> {
    const queryParams: Record<string, string | undefined> = {};
    if (params?.status) queryParams.status = params.status;
    if (params?.application_id) queryParams.application_id = params.application_id;

    return apiClient.get<ReviewFlagSummary[]>('/review-flags', { params: queryParams });
  }

  /**
   * Get complete review case detail package including criterion, source quotes,
   * candidate clarifications, and reviewer decisions.
   */
  async getReviewCase(id: string): Promise<ReviewCaseDetail> {
    return apiClient.get<ReviewCaseDetail>(`/reviews/${id}`);
  }

  /**
   * Record an authorized human reviewer decision with mandatory non-empty rationale.
   */
  async recordReviewDecision(
    id: string,
    decision: ReviewDecisionType | string,
    mandatoryRationale: string
  ): Promise<ReviewDecisionItem> {
    return apiClient.post<ReviewDecisionItem>(`/reviews/${id}/decision`, {
      decision,
      mandatory_rationale: mandatoryRationale,
    });
  }

  /**
   * Submit candidate clarification or supplementary evidence on an application.
   */
  async submitClarification(
    applicationId: string,
    payload: CandidateClarificationPayload
  ): Promise<CandidateClarificationItem> {
    return apiClient.post<CandidateClarificationItem>(
      `/applications/${applicationId}/clarifications`,
      payload
    );
  }

  /**
   * Convenience endpoint to submit candidate clarification referencing a review flag ID.
   */
  async submitClarificationForReview(
    reviewId: string,
    payload: CandidateClarificationPayload
  ): Promise<CandidateClarificationItem> {
    return apiClient.post<CandidateClarificationItem>(
      `/reviews/${reviewId}/clarification`,
      payload
    );
  }

  /**
   * Create or auto-flag review cases for candidate evaluation criteria.
   */
  async createReviewFlags(payload: CreateReviewFlagsPayload): Promise<unknown> {
    return apiClient.post('/review-flags', payload);
  }
}

export const reviewService = new ReviewService();
