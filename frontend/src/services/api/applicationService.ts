/**
 * ClearHire Candidate Applications API Service
 * Communicates with backend FastAPI application endpoints:
 * - GET  /api/v1/applications
 * - GET  /api/v1/applications/{id}
 * - POST /api/v1/applications
 * Automatically enriches job titles and departments using jobService cache.
 */

import { apiClient } from './client';
import { jobService } from './jobService';
import { Application } from '../../contracts/models';
import { ApplicationStatus } from '../../contracts/enums';

export interface ApplicationListParams {
  job_id?: string;
  status?: ApplicationStatus | string;
  limit?: number;
  offset?: number;
}

class ApplicationService {
  /**
   * List candidate applications (tenant-isolated per role).
   */
  async listApplications(params?: ApplicationListParams): Promise<Application[]> {
    const queryParams: Record<string, string | number | undefined> = {};
    if (params?.job_id) queryParams.job_id = params.job_id;
    if (params?.status) queryParams.status = params.status;
    if (params?.limit !== undefined) queryParams.limit = params.limit;
    if (params?.offset !== undefined) queryParams.offset = params.offset;

    const applications = await apiClient.get<Application[]>('/applications', { params: queryParams });

    // Enrich with job title and department
    try {
      const jobs = await jobService.listJobs({}, false);
      const jobMap = new Map(jobs.map((j) => [j.id, j]));

      return applications.map((app) => {
        const matchingJob = jobMap.get(app.job_id);
        return {
          ...app,
          job_title: matchingJob?.title || app.job_title || `Requisition #${app.job_id.slice(0, 8)}`,
          department: matchingJob?.department || app.department || 'General',
        };
      });
    } catch {
      // Fallback if jobs listing fails
      return applications.map((app) => ({
        ...app,
        job_title: app.job_title || `Requisition #${app.job_id.slice(0, 8)}`,
        department: app.department || 'General',
      }));
    }
  }

  /**
   * Get single candidate application details.
   */
  async getApplication(id: string): Promise<Application> {
    const application = await apiClient.get<Application>(`/applications/${id}`);

    try {
      const job = await jobService.getJob(application.job_id);
      return {
        ...application,
        job_title: job.title || `Requisition #${application.job_id.slice(0, 8)}`,
        department: job.department || 'General',
      };
    } catch {
      return {
        ...application,
        job_title: application.job_title || `Requisition #${application.job_id.slice(0, 8)}`,
        department: application.department || 'General',
      };
    }
  }

  /**
   * Submit a new candidate application.
   */
  async submitApplication(job_id: string, primary_document_id: string): Promise<Application> {
    return apiClient.post<Application>('/applications', {
      job_id,
      primary_document_id,
    });
  }
}

export const applicationService = new ApplicationService();
