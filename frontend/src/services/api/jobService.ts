/**
 * ClearHire Job Requisitions API Service
 * Communicates directly with backend FastAPI job endpoints:
 * - GET  /api/v1/jobs
 * - POST /api/v1/jobs
 * - GET  /api/v1/jobs/{id}
 * Includes in-memory query caching and cache invalidation.
 */

import { apiClient } from './client';
import { Job, JobCreateRequest, JobListParams } from '../../contracts/models';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

class JobService {
  private cache = new Map<string, CacheEntry<Job[]>>();
  private jobDetailCache = new Map<string, CacheEntry<Job>>();
  private readonly CACHE_TTL_MS = 15000; // 15 seconds fresh cache

  private getCacheKey(params?: JobListParams): string {
    if (!params) return 'all';
    return JSON.stringify({
      status: params.status || null,
      department: params.department || null,
      limit: params.limit || 50,
      offset: params.offset || 0,
    });
  }

  /**
   * Invalidate all cached job queries (e.g. after creating a new requisition)
   */
  invalidateCache(): void {
    this.cache.clear();
    this.jobDetailCache.clear();
  }

  /**
   * Fetch a list of job requisitions with criteria.
   */
  async listJobs(params?: JobListParams, skipCache = false): Promise<Job[]> {
    const key = this.getCacheKey(params);
    const now = Date.now();

    if (!skipCache) {
      const cached = this.cache.get(key);
      if (cached && now - cached.timestamp < this.CACHE_TTL_MS) {
        return cached.data;
      }
    }

    const queryParams: Record<string, string | number | undefined> = {};
    if (params?.status) queryParams.status = params.status;
    if (params?.department && params.department !== 'all') queryParams.department = params.department;
    if (params?.limit !== undefined) queryParams.limit = params.limit;
    if (params?.offset !== undefined) queryParams.offset = params.offset;

    const data = await apiClient.get<Job[]>('/jobs', { params: queryParams });
    this.cache.set(key, { data, timestamp: now });
    return data;
  }

  /**
   * Fetch single job requisition with full versioned criteria.
   */
  async getJob(id: string, skipCache = false): Promise<Job> {
    const now = Date.now();
    if (!skipCache) {
      const cached = this.jobDetailCache.get(id);
      if (cached && now - cached.timestamp < this.CACHE_TTL_MS) {
        return cached.data;
      }
    }

    const job = await apiClient.get<Job>(`/jobs/${id}`);
    this.jobDetailCache.set(id, { data: job, timestamp: now });
    return job;
  }

  /**
   * Create a new employer job requisition with versioned screening criteria.
   * Automatically invalidates cached job lists upon 201 Created.
   */
  async createJob(payload: JobCreateRequest): Promise<Job> {
    const createdJob = await apiClient.post<Job>('/jobs', payload);
    this.invalidateCache();
    return createdJob;
  }
}

export const jobService = new JobService();
