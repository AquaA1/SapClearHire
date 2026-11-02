import { apiClient } from './client';
import { DocumentProcessingStatus, EvidenceStatus } from '../../contracts/enums';

export interface TranscriptQAItem {
  id: string;
  transcript_id: string;
  question_index: number;
  interviewer_question: string;
  candidate_answer_excerpt: string;
  start_line?: number | null;
  end_line?: number | null;
  mapped_criterion_id?: string | null;
  mapped_skill_name?: string | null;
  evidence_status: EvidenceStatus | string;
  expected_concept: string;
  alignment_summary: string;
  coaching_suggestion: string;
  clarification_requested: boolean;
  candidate_clarification_text?: string | null;
  created_at: string;
}

export interface InterviewTranscript {
  id: string;
  application_id: string;
  uploader_id?: string | null;
  round_name: string;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  processing_status: DocumentProcessingStatus | string;
  created_at: string;
  qa_items: TranscriptQAItem[];
}

class TranscriptService {
  /**
   * Upload an interview transcript for a candidate's application (Employer/Reviewer).
   */
  async uploadTranscript(
    applicationId: string,
    file: File,
    roundName: string = 'Technical Interview'
  ): Promise<InterviewTranscript> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('round_name', roundName);

    return apiClient.post<InterviewTranscript>(`/applications/${applicationId}/transcripts`, formData);
  }

  /**
   * List all interview transcripts and extracted Q&A coaching items for an application.
   */
  async listTranscripts(applicationId: string): Promise<InterviewTranscript[]> {
    return apiClient.get<InterviewTranscript[]>(`/applications/${applicationId}/transcripts`);
  }

  /**
   * Submit candidate clarification regarding an interview response.
   */
  async clarifyQAItem(qaId: string, clarificationText: string): Promise<TranscriptQAItem> {
    return apiClient.post<TranscriptQAItem>(`/transcripts/qa/${qaId}/clarify`, {
      clarification_text: clarificationText,
    });
  }

  /**
   * Retry failed transcript analysis.
   */
  async retryTranscript(transcriptId: string): Promise<void> {
    await apiClient.post(`/transcripts/${transcriptId}/retry`);
  }
}

export const transcriptService = new TranscriptService();
