/**
 * ClearHire Candidate Profile API Service
 * Communicates directly with backend FastAPI profiles endpoint:
 * - GET /api/v1/profiles/{id}/skills (Candidate verified skill inventory)
 */

import { apiClient } from './client';
import { CandidateProfileSkillsResponse } from '../../contracts/models';

class ProfileService {
  /**
   * Retrieves verified skill inventory extracted from candidate resumes.
   * Accessible to authorized Candidates (own profile) and Employers/Reviewers (applicants to org jobs).
   */
  async getCandidateSkills(candidateId: string): Promise<CandidateProfileSkillsResponse> {
    return apiClient.get<CandidateProfileSkillsResponse>(`/profiles/${candidateId}/skills`);
  }
}

export const profileService = new ProfileService();
