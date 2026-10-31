/**
 * ClearHire Candidate Evaluation API Service
 * Communicates with backend FastAPI evaluation endpoints:
 * - GET  /api/v1/evaluations/{id}
 * - POST /api/v1/evaluations
 */

import { apiClient } from './client';
import { Evaluation } from '../../contracts/models';

class EvaluationService {
  /**
   * Fetch complete deterministic evaluation report with factual criteria coverage.
   */
  async getEvaluation(id: string): Promise<Evaluation> {
    return apiClient.get<Evaluation>(`/evaluations/${id}`);
  }

  /**
   * Execute deterministic evidence evaluation for an application against active job criteria.
   * Accessible to Employer Admin, Reviewer, and System Auditor.
   */
  async evaluateApplication(applicationId: string): Promise<Evaluation> {
    return apiClient.post<Evaluation>('/evaluations', {
      application_id: applicationId,
    });
  }
}

export const evaluationService = new EvaluationService();
