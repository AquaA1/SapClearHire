/**
 * ClearHire Document & Resume Extraction API Service
 * Communicates directly with backend FastAPI document endpoints:
 * - POST /api/v1/documents (Upload PDF resume)
 * - GET  /api/v1/documents/{id}/status (Poll processing status & page text)
 * - POST /api/v1/documents/{id}/retry (Retry failed processing)
 * - POST /api/v1/documents/{id}/extract (Trigger structured AI evidence extraction)
 * - GET  /api/v1/documents/{id}/extraction-results (Get AI evidence extraction results)
 */

import { apiClient } from './client';
import {
  DocumentUploadResponse,
  DocumentStatusResponse,
  ExtractionRunResponse,
} from '../../contracts/models';

class DocumentService {
  /**
   * Upload candidate PDF resume.
   * Uses multipart/form-data with field name 'file'.
   * The browser automatically generates the multipart boundary.
   */
  async uploadDocument(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file, file.name);

    return apiClient.post<DocumentUploadResponse>('/documents', formData);
  }

  /**
   * Poll document processing status and page-by-page extracted text.
   */
  async getDocumentStatus(documentId: string): Promise<DocumentStatusResponse> {
    return apiClient.get<DocumentStatusResponse>(`/documents/${documentId}/status`);
  }

  /**
   * Retry document text extraction without requiring re-upload.
   */
  async retryDocumentProcessing(documentId: string): Promise<DocumentStatusResponse> {
    return apiClient.post<DocumentStatusResponse>(`/documents/${documentId}/retry`);
  }

  /**
   * Trigger structured AI evidence extraction pipeline on a completed document.
   */
  async triggerAIExtraction(documentId: string): Promise<ExtractionRunResponse> {
    return apiClient.post<ExtractionRunResponse>(`/documents/${documentId}/extract`);
  }

  /**
   * Retrieve the latest structured AI evidence extraction run results.
   */
  async getExtractionResults(documentId: string): Promise<ExtractionRunResponse> {
    return apiClient.get<ExtractionRunResponse>(`/documents/${documentId}/extraction-results`);
  }

  /**
   * Fetch original uploaded PDF document as a binary Blob.
   * Enforces token authentication and returns Blob + original filename.
   */
  async getDocumentFile(
    documentId: string,
    disposition: 'inline' | 'attachment' = 'inline'
  ): Promise<{ blob: Blob; filename: string; contentType: string }> {
    return apiClient.getBlob(`/documents/${documentId}/file`, {
      params: { disposition },
    });
  }
}


export const documentService = new DocumentService();
