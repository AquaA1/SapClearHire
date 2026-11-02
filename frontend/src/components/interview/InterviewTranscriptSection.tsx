import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  RefreshCw,
  Sparkles,
  FileText,
  ShieldCheck,
  CornerDownRight,
  Send,
  X,
  Clock,
  Layers,
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { StatusBadge } from '../ui/StatusBadge';
import {
  transcriptService,
  InterviewTranscript,
  TranscriptQAItem,
} from '../../services/api/transcriptService';

interface InterviewTranscriptSectionProps {
  applicationId: string;
  isCandidate?: boolean;
}

export const InterviewTranscriptSection: React.FC<InterviewTranscriptSectionProps> = ({
  applicationId,
  isCandidate = false,
}) => {
  const [transcripts, setTranscripts] = useState<InterviewTranscript[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Upload modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [roundName, setRoundName] = useState<string>('Technical Interview');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Clarification modal state
  const [selectedQAForClarify, setSelectedQAForClarify] = useState<TranscriptQAItem | null>(null);
  const [clarificationText, setClarificationText] = useState<string>('');
  const [isSubmittingClarify, setIsSubmittingClarify] = useState<boolean>(false);
  const [clarifyError, setClarifyError] = useState<string | null>(null);

  const loadTranscripts = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await transcriptService.listTranscripts(applicationId);
      setTranscripts(data);
    } catch (err: any) {
      console.error('Failed to load transcripts:', err);
      setError(err?.message || 'Failed to load interview transcripts');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (applicationId) {
      loadTranscripts();
    }
  }, [applicationId]);

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError('Please select a transcript file (.txt, .md, .json, .pdf, .docx)');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    try {
      await transcriptService.uploadTranscript(applicationId, selectedFile, roundName);
      setIsUploadModalOpen(false);
      setSelectedFile(null);
      setRoundName('Technical Interview');
      await loadTranscripts();
    } catch (err: any) {
      setUploadError(err?.message || 'Failed to upload interview transcript');
    } finally {
      setIsUploading(false);
    }
  };

  const handleClarifySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedQAForClarify || !clarificationText.trim()) return;

    setIsSubmittingClarify(true);
    setClarifyError(null);
    try {
      await transcriptService.clarifyQAItem(selectedQAForClarify.id, clarificationText.trim());
      setSelectedQAForClarify(null);
      setClarificationText('');
      await loadTranscripts();
    } catch (err: any) {
      setClarifyError(err?.message || 'Failed to submit clarification');
    } finally {
      setIsSubmittingClarify(false);
    }
  };

  const handleRetry = async (transcriptId: string) => {
    try {
      await transcriptService.retryTranscript(transcriptId);
      await loadTranscripts();
    } catch (err: any) {
      alert(`Retry failed: ${err?.message || 'Unknown error'}`);
    }
  };

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    if (s === 'supported') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill text-xs font-bold bg-success-dim text-success border border-success/30">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Supported</span>
        </span>
      );
    }
    if (s === 'partially_supported') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill text-xs font-bold bg-accent-dim text-accent border border-accent/30">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Partially Supported</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill text-xs font-bold bg-warn-dim text-warn border border-warn/30">
        <AlertTriangle className="w-3.5 h-3.5" />
        <span>Ambiguous</span>
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-surface rounded-card p-6 border border-subtle shadow-card flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-accent-dim text-accent border border-accent/30">
              <MessageSquare className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-ink">Interview Coach & Dialogue Audit</h3>
            <span className="px-2.5 py-0.5 rounded-pill text-xs font-bold bg-accent-dim text-accent border border-accent/20">
              Phase 3 Spec
            </span>
          </div>
          <p className="text-xs sm:text-sm text-muted max-w-2xl">
            Verbatim dialogue extraction and structural conceptual feedback. Aligned with strict
            responsible AI bounds: zero personality scoring, zero rejection guessing, and 100% verbatim excerpt grounding.
          </p>
        </div>

        {!isCandidate && (
          <Button
            variant="primary"
            onClick={() => setIsUploadModalOpen(true)}
            leftIcon={<UploadCloud className="w-4 h-4" />}
            className="font-bold shrink-0"
          >
            Upload Transcript
          </Button>
        )}
      </div>

      {/* Loading & Error States */}
      {isLoading && (
        <div className="bg-surface rounded-card border border-subtle p-12 text-center text-muted flex items-center justify-center gap-3">
          <RefreshCw className="w-5 h-5 animate-spin text-accent" />
          <span className="text-sm font-medium">Loading interview transcripts...</span>
        </div>
      )}

      {error && !isLoading && (
        <div className="p-4 rounded-card bg-danger-dim border border-danger/30 text-danger text-sm flex items-center justify-between">
          <span>{error}</span>
          <Button variant="secondary" size="sm" onClick={loadTranscripts}>
            Retry
          </Button>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && transcripts.length === 0 && (
        <div className="bg-surface rounded-card border border-subtle p-12 text-center space-y-3 shadow-card">
          <div className="w-12 h-12 rounded-full bg-elevated text-muted mx-auto flex items-center justify-center">
            <FileText className="w-6 h-6" />
          </div>
          <h4 className="text-base font-bold text-ink">No Interview Transcripts Uploaded</h4>
          <p className="text-xs sm:text-sm text-muted max-w-md mx-auto">
            {isCandidate
              ? 'When your interview notes or dialogue transcripts are uploaded by the employer, your transparent Q&A review and conceptual coaching feedback will appear here.'
              : 'Upload interview dialogue files (.txt, .md, .json, .pdf, .docx) to analyze Q&A exchanges, verify technical criteria, and generate coaching feedback.'}
          </p>
          {!isCandidate && (
            <Button
              variant="secondary"
              onClick={() => setIsUploadModalOpen(true)}
              leftIcon={<UploadCloud className="w-4 h-4" />}
              className="mt-2"
            >
              Upload First Transcript
            </Button>
          )}
        </div>
      )}

      {/* Transcript Cards */}
      {!isLoading &&
        transcripts.map((t) => (
          <div key={t.id} className="space-y-4">
            {/* Transcript Round Header */}
            <div className="bg-surface rounded-card p-4 sm:p-5 border border-subtle shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-elevated text-ink border border-subtle">
                  <FileText className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-sm sm:text-base font-bold text-ink">{t.round_name}</h4>
                  <div className="flex items-center gap-2 text-xs text-muted mt-0.5">
                    <span>{t.file_name}</span>
                    <span>•</span>
                    <span>{new Date(t.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2.5">
                <StatusBadge status={t.processing_status} size="sm" />
                {t.processing_status === 'failed' && !isCandidate && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleRetry(t.id)}
                    leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                  >
                    Retry
                  </Button>
                )}
              </div>
            </div>

            {/* In-Flight Processing Spinner */}
            {t.processing_status === 'processing' && (
              <div className="p-6 rounded-card bg-accent-dim/30 border border-accent/30 text-center space-y-2">
                <RefreshCw className="w-5 h-5 animate-spin text-accent mx-auto" />
                <p className="text-sm font-semibold text-ink">Analyzing Interview Dialogue...</p>
                <p className="text-xs text-muted">
                  Segmenting questions, verifying verbatim candidate quotes, and benchmarking conceptual depth.
                </p>
              </div>
            )}

            {/* Q&A Items */}
            {t.processing_status === 'completed' && t.qa_items && t.qa_items.length > 0 && (
              <div className="grid grid-cols-1 gap-4">
                {t.qa_items.map((qa) => (
                  <div
                    key={qa.id}
                    className="bg-surface rounded-card p-5 sm:p-6 border border-subtle shadow-card space-y-4 hover:border-subtle-strong transition-all"
                  >
                    {/* Q&A Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3 border-b border-subtle">
                      <div className="flex items-center gap-2.5">
                        <span className="w-7 h-7 rounded-full bg-elevated font-mono text-xs font-bold text-ink flex items-center justify-center border border-subtle">
                          Q{qa.question_index}
                        </span>
                        {qa.mapped_skill_name && (
                          <span className="px-2.5 py-0.5 rounded-pill bg-elevated font-medium text-xs text-ink border border-subtle">
                            Skill: {qa.mapped_skill_name}
                          </span>
                        )}
                        {qa.start_line && (
                          <span className="text-xs text-muted font-mono">
                            Line {qa.start_line}
                            {qa.end_line && qa.end_line !== qa.start_line ? `-${qa.end_line}` : ''}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {getStatusBadge(qa.evidence_status)}
                        {qa.clarification_requested && (
                          <span className="px-2 py-0.5 rounded-pill text-xs font-bold bg-accent-dim text-accent border border-accent/20">
                            Clarification Provided
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Question */}
                    <div>
                      <h5 className="text-xs font-bold uppercase tracking-wider text-muted mb-1">
                        Question Asked
                      </h5>
                      <p className="text-sm sm:text-base font-semibold text-ink">{qa.interviewer_question}</p>
                    </div>

                    {/* Candidate Verbatim Answer */}
                    <div className="bg-elevated/60 p-4 rounded-md border border-subtle space-y-1.5">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-muted uppercase tracking-wider">
                        <ShieldCheck className="w-3.5 h-3.5 text-success" />
                        <span>Candidate's Verbatim Response (Grounded)</span>
                      </div>
                      <blockquote className="text-sm text-ink italic font-serif leading-relaxed">
                        "{qa.candidate_answer_excerpt}"
                      </blockquote>
                    </div>

                    {/* Expected Technical Concept & Alignment */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs sm:text-sm">
                      <div className="p-3.5 rounded-md bg-elevated/40 border border-subtle space-y-1">
                        <span className="font-bold text-muted block text-xs uppercase tracking-wider">
                          Conceptual Benchmark Target
                        </span>
                        <p className="text-ink font-medium leading-normal">{qa.expected_concept}</p>
                      </div>

                      <div className="p-3.5 rounded-md bg-elevated/40 border border-subtle space-y-1">
                        <span className="font-bold text-muted block text-xs uppercase tracking-wider">
                          Evidence Assessment
                        </span>
                        <p className="text-ink font-medium leading-normal">{qa.alignment_summary}</p>
                      </div>
                    </div>

                    {/* Actionable Coaching Suggestion ("Build careers beyond it") */}
                    <div className="p-4 rounded-md bg-accent-dim/40 border border-accent/30 flex items-start gap-3">
                      <Sparkles className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                      <div className="space-y-1 text-xs sm:text-sm">
                        <strong className="font-bold text-ink block">
                          Career Coaching Suggestion (Phase 3)
                        </strong>
                        <p className="text-ink/90 font-medium leading-normal">{qa.coaching_suggestion}</p>
                      </div>
                    </div>

                    {/* Candidate Clarification Display */}
                    {qa.candidate_clarification_text && (
                      <div className="p-3.5 rounded-md bg-elevated border border-accent/30 space-y-1">
                        <span className="text-xs font-bold text-accent uppercase tracking-wider block">
                          Candidate Clarification Note
                        </span>
                        <p className="text-xs sm:text-sm text-ink font-medium">
                          {qa.candidate_clarification_text}
                        </p>
                      </div>
                    )}

                    {/* Clarification Button for Candidate */}
                    {isCandidate && !qa.candidate_clarification_text && (
                      <div className="pt-2 flex justify-end">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            setSelectedQAForClarify(qa);
                            setClarificationText('');
                          }}
                          leftIcon={<MessageSquare className="w-3.5 h-3.5" />}
                        >
                          Request Answer Clarification
                        </Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

      {/* Upload Transcript Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-xs">
          <div className="bg-surface rounded-card border border-subtle shadow-modal max-w-lg w-full p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-subtle">
              <div className="flex items-center gap-2">
                <UploadCloud className="w-5 h-5 text-accent" />
                <h4 className="text-base font-bold text-ink">Upload Interview Transcript</h4>
              </div>
              <button
                type="button"
                onClick={() => setIsUploadModalOpen(false)}
                className="text-muted hover:text-ink cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-muted uppercase tracking-wider mb-1.5">
                  Interview Round / Stage
                </label>
                <input
                  type="text"
                  value={roundName}
                  onChange={(e) => setRoundName(e.target.value)}
                  placeholder="e.g. Technical Screening Round 1"
                  className="w-full bg-elevated border border-subtle rounded-md px-3.5 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:border-accent font-medium"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-muted uppercase tracking-wider mb-1.5">
                  Transcript File
                </label>
                <input
                  type="file"
                  ref={fileInputRef}
                  accept=".txt,.md,.json,.pdf,.docx"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-muted file:mr-3 file:py-2 file:px-4 file:rounded-md file:border file:border-subtle file:text-xs file:font-bold file:bg-elevated file:text-ink hover:file:bg-surface cursor-pointer"
                  required
                />
                <p className="text-xs text-muted mt-1.5">
                  Supports plain text (.txt, .md), JSON (.json), PDF (.pdf), or Word (.docx).
                </p>
              </div>

              {uploadError && (
                <div className="p-3 rounded-md bg-danger-dim text-danger text-xs font-medium">
                  {uploadError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-subtle">
                <Button
                  variant="secondary"
                  size="sm"
                  type="button"
                  onClick={() => setIsUploadModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  type="submit"
                  isLoading={isUploading}
                  className="font-bold"
                >
                  Upload & Analyze
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Clarification Modal for Candidate */}
      {selectedQAForClarify && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-xs">
          <div className="bg-surface rounded-card border border-subtle shadow-modal max-w-lg w-full p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-subtle">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-accent" />
                <h4 className="text-base font-bold text-ink">Submit Answer Clarification</h4>
              </div>
              <button
                type="button"
                onClick={() => setSelectedQAForClarify(null)}
                className="text-muted hover:text-ink cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div className="p-3 rounded-md bg-elevated/60 text-xs space-y-1">
                <span className="font-bold text-muted uppercase">Question:</span>
                <p className="text-ink font-semibold">{selectedQAForClarify.interviewer_question}</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-muted uppercase tracking-wider mb-1.5">
                  Your Factual Clarification
                </label>
                <textarea
                  rows={4}
                  value={clarificationText}
                  onChange={(e) => setClarificationText(e.target.value)}
                  placeholder="Explain if your answer was abbreviated or if key context was missing in the transcript notes..."
                  className="w-full bg-elevated border border-subtle rounded-md p-3 text-xs sm:text-sm text-ink placeholder:text-muted focus:outline-none focus:border-accent font-medium resize-none"
                  required
                />
                <p className="text-xs text-muted mt-1">
                  This clarification will be permanently added to your dossier audit trail.
                </p>
              </div>

              {clarifyError && (
                <div className="p-3 rounded-md bg-danger-dim text-danger text-xs font-medium">
                  {clarifyError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-subtle">
                <Button
                  variant="secondary"
                  size="sm"
                  type="button"
                  onClick={() => setSelectedQAForClarify(null)}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleClarifySubmit}
                  isLoading={isSubmittingClarify}
                  className="font-bold"
                >
                  Submit Clarification
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
