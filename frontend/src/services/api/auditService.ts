/**
 * ClearHire Audit & Cryptographic Hash Chain API Service
 * Communicates with backend FastAPI audit endpoints:
 * - GET /api/v1/audit
 * - GET /api/v1/audit/{id}
 * - GET /api/v1/audit/verify
 */

import { apiClient } from './client';
import { AuditEvent, AuditVerificationReport } from '../../contracts/models';

export interface AuditQueryParams {
  resource_type?: string;
  resource_id?: string;
  actor_id?: string;
  limit?: number;
  offset?: number;
}

class AuditService {
  /**
   * Query cryptographically verifiable audit events.
   * Accessible to System Auditors and Employer Admins.
   */
  async listAuditEvents(params?: AuditQueryParams): Promise<AuditEvent[]> {
    const queryParams: Record<string, string | number | undefined> = {};
    if (params?.resource_type) queryParams.resource_type = params.resource_type;
    if (params?.resource_id) queryParams.resource_id = params.resource_id;
    if (params?.actor_id) queryParams.actor_id = params.actor_id;
    if (params?.limit !== undefined) queryParams.limit = params.limit;
    if (params?.offset !== undefined) queryParams.offset = params.offset;

    return apiClient.get<AuditEvent[]>('/audit', { params: queryParams });
  }

  /**
   * Get specific audit event with hash chain details.
   */
  async getAuditEvent(id: string): Promise<AuditEvent> {
    return apiClient.get<AuditEvent>(`/audit/${id}`);
  }

  /**
   * Run cryptographic verification across the full SHA-256 tamper-evident hash chain.
   */
  async verifyChain(): Promise<AuditVerificationReport> {
    return apiClient.get<AuditVerificationReport>('/audit/verify');
  }
}

export const auditService = new AuditService();
