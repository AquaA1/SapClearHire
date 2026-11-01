import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../stores/authStore';
import { jobService } from '../../services/api/jobService';
import { documentService } from '../../services/api/documentService';
import { applicationService } from '../../services/api/applicationService';
import { pendingDocumentStore } from '../../services/storage/pendingDocumentStore';
import { Job, DocumentStatusResponse, Application } from '../../contracts/models';
import { DocumentProcessingStatus } from '../../contracts/enums';
import { StatusBadge } from '../../components/ui/Badge';
import {
  ArrowLeft,
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Trash2,
  ShieldCheck,
  Sparkles,
  FileCheck,
  Layers,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';
import { Button, LoadingSpinner } from '../../components/ui';

const MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024; // 15 MB backend limit
const POLL_INTERVAL_MS = 1500;
const MAX_POLL_ATTEMPTS = 30; // 45 seconds total

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export const CandidateJobDetailPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  // Requisition State
  const [job, setJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Existing Application Check (Duplicate Prevention)
  const [existingApplication, setExistingApplication] = useState<Application | null>(null);
  const [isCheckingExistingApp, setIsCheckingExistingApp] = useState(true);

  // Resume Upload & Extraction State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadState, setUploadState] = useState<
    'idle' | 'uploading' | 'processing' | 'completed' | 'failed'
  >('idle');
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [documentStatus, setDocumentStatus] = useState<DocumentStatusResponse | null>(null);
  const [documentError, setDocumentError] = useState<string | null>(null);
  const [selectedPageTab, setSelectedPageTab] = useState<string>('1');
  const [isRetrying, setIsRetrying] = useState(false);

  // Refresh Recovery State
  const [isRestoringDocument, setIsRestoringDocument] = useState(false);
  const [recoveryNotice, setRecoveryNotice] = useState<string | null>(null);

  // Application Submission State
  const [hasConfirmedDeclaration, setHasConfirmedDeclaration] = useState(false);
  const [isSubmittingApp, setIsSubmittingApp] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [submittedApplication, setSubmittedApplication] = useState<Application | null>(null);

  // Refs for polling and scrolling
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pollCountRef = useRef<number>(0);
  const uploadSectionRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Clear polling interval safely
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    pollCountRef.current = 0;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  // Status Polling Worker
  const startStatusPolling = useCallback(
    (docId: string) => {
      stopPolling();
      pollCountRef.current = 0;

      pollIntervalRef.current = setInterval(async () => {
        pollCountRef.current += 1;

        try {
          const statusRes = await documentService.getDocumentStatus(docId);
          setDocumentStatus(statusRes);

          if (statusRes.processing_status === DocumentProcessingStatus.COMPLETED) {
            stopPolling();
            setUploadState('completed');
            setIsRetrying(false);

            const pages = Object.keys(statusRes.extracted_text_by_page || {});
            if (pages.length > 0) {
              const sorted = pages.sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
              setSelectedPageTab(sorted[0]);
            }
          } else if (statusRes.processing_status === DocumentProcessingStatus.FAILED) {
            stopPolling();
            setUploadState('failed');
            setIsRetrying(false);
            const errMsg =
              statusRes.processing_error?.message ||
              'Document text extraction failed on server worker.';
            setDocumentError(errMsg);
          } else if (pollCountRef.current >= MAX_POLL_ATTEMPTS) {
            stopPolling();
            setUploadState('failed');
            setIsRetrying(false);
            setDocumentError(
              'Document extraction polling timed out after 45 seconds. The worker may still be processing. You can retry status checking.'
            );
          }
        } catch (err: unknown) {
          const errObj = err as { message?: string; status?: number };
          stopPolling();
          setUploadState('failed');
          setIsRetrying(false);
          setDocumentError(errObj.message || 'Failed to poll document extraction status.');
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling]
  );

  // Restore Pending Document Reference from Backend
  const restorePendingDocument = useCallback(
    async (docId: string, currentJobId: string, candidateId: string) => {
      setIsRestoringDocument(true);
      setRecoveryNotice(null);

      try {
        const statusRes = await documentService.getDocumentStatus(docId);
        setDocumentId(docId);
        setDocumentStatus(statusRes);

        if (statusRes.processing_status === DocumentProcessingStatus.COMPLETED) {
          setUploadState('completed');
          const pages = Object.keys(statusRes.extracted_text_by_page || {});
          if (pages.length > 0) {
            const sorted = pages.sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
            setSelectedPageTab(sorted[0]);
          }
        } else if (
          statusRes.processing_status === DocumentProcessingStatus.PROCESSING ||
          statusRes.processing_status === DocumentProcessingStatus.QUEUED
        ) {
          setUploadState('processing');
          startStatusPolling(docId);
        } else if (statusRes.processing_status === DocumentProcessingStatus.FAILED) {
          setUploadState('failed');
          const errMsg =
            statusRes.processing_error?.message ||
            'Document text extraction failed on server worker.';
          setDocumentError(errMsg);
        }
      } catch (err: unknown) {
        const errObj = err as { status?: number; message?: string };
        if (errObj.status === 404 || errObj.status === 403) {
          console.warn(
            `[CandidateJobDetailPage] Pending document ${docId} is invalid or unauthorized (HTTP ${errObj.status}). Discarding saved reference.`
          );
          pendingDocumentStore.removePendingDocument(candidateId, currentJobId);
          setDocumentId(null);
          setDocumentStatus(null);
          setUploadState('idle');
          setRecoveryNotice(
            'Your previously uploaded resume session is no longer available on the server. Please select a resume to upload.'
          );
        } else {
          setDocumentId(docId);
          setUploadState('failed');
          setDocumentError(
            'Unable to reach server to restore document status. You can retry or upload a new resume.'
          );
        }
      } finally {
        setIsRestoringDocument(false);
      }
    },
    [startStatusPolling]
  );

  // Fetch Job Requisition Details and Check for Existing Application or Saved Document
  useEffect(() => {
    if (!jobId) {
      setError('No requisition identifier specified.');
      setIsLoading(false);
      setIsCheckingExistingApp(false);
      return;
    }

    const loadJobAndApplicationStatus = async () => {
      setIsLoading(true);
      setError(null);
      setIsCheckingExistingApp(true);

      try {
        const [foundJob, candidateApps] = await Promise.all([
          jobService.getJob(jobId),
          applicationService.listApplications({ job_id: jobId }).catch(() => []),
        ]);

        setJob(foundJob);

        if (candidateApps.length > 0) {
          setExistingApplication(candidateApps[0]);
          // Clean up any unneeded pending reference if already applied
          if (user?.id) {
            pendingDocumentStore.removePendingDocument(user.id, jobId);
          }
        } else if (user?.id) {
          // Restore pending uploaded document if available for this candidate and job
          const pendingRef = pendingDocumentStore.getPendingDocument(user.id, jobId);
          if (pendingRef?.documentId) {
            await restorePendingDocument(pendingRef.documentId, jobId, user.id);
          }
        }
      } catch (err: unknown) {
        const errObj = err as { message?: string; status?: number };
        if (errObj.status === 404) {
          setError(`Job requisition "${jobId}" was not found or is no longer available.`);
        } else {
          setError(errObj.message || 'Failed to retrieve requisition details from server.');
        }
      } finally {
        setIsLoading(false);
        setIsCheckingExistingApp(false);
      }
    };

    loadJobAndApplicationStatus();
  }, [jobId, user?.id, restorePendingDocument]);

  // Validate incoming file
  const validateFile = (file: File): string | null => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      return 'Only PDF documents are supported (.pdf)';
    }
    if (file.type && file.type !== 'application/pdf') {
      return 'Invalid MIME type. Please upload an authentic PDF document.';
    }
    if (file.size === 0) {
      return 'Uploaded file is empty (0 bytes). Please select a valid resume.';
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File size (${formatBytes(file.size)}) exceeds the maximum allowed limit of 15 MB.`;
    }
    return null;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const valErr = validateFile(file);
    if (valErr) {
      setValidationError(valErr);
      setSelectedFile(null);
    } else {
      setValidationError(null);
      setSelectedFile(file);
      setUploadState('idle');
      setDocumentStatus(null);
      setDocumentError(null);
      setSubmissionError(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const file = e.dataTransfer.files?.[0];
    if (!file) return;

    const valErr = validateFile(file);
    if (valErr) {
      setValidationError(valErr);
      setSelectedFile(null);
    } else {
      setValidationError(null);
      setSelectedFile(file);
      setUploadState('idle');
      setDocumentStatus(null);
      setDocumentError(null);
      setSubmissionError(null);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setValidationError(null);
    setUploadState('idle');
    setDocumentId(null);
    setDocumentStatus(null);
    setDocumentError(null);
    setSubmissionError(null);
    setHasConfirmedDeclaration(false);
    setRecoveryNotice(null);
    stopPolling();

    // Discard saved pending document reference
    if (user?.id && jobId) {
      pendingDocumentStore.removePendingDocument(user.id, jobId);
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Upload Trigger
  const handleUpload = async () => {
    if (!selectedFile) return;
    if (uploadState === 'uploading' || uploadState === 'processing') return;

    setUploadState('uploading');
    setDocumentError(null);
    setValidationError(null);
    setSubmissionError(null);
    setRecoveryNotice(null);

    try {
      const uploadRes = await documentService.uploadDocument(selectedFile);
      setDocumentId(uploadRes.id);
      setUploadState('processing');

      // Save pending document reference in browser storage for recovery across refreshes
      if (user?.id && jobId) {
        pendingDocumentStore.savePendingDocument(user.id, jobId, {
          documentId: uploadRes.id,
          fileName: selectedFile.name,
        });
      }

      // Backend automatically enqueues extraction; start polling status
      startStatusPolling(uploadRes.id);
    } catch (err: unknown) {
      const errObj = err as { message?: string; status?: number };
      setUploadState('failed');
      setDocumentError(errObj.message || 'Failed to upload document to server.');
    }
  };

  // Retry Failed Processing
  const handleRetryProcessing = async () => {
    if (!documentId) return;
    setIsRetrying(true);
    setUploadState('processing');
    setDocumentError(null);

    try {
      const retryRes = await documentService.retryDocumentProcessing(documentId);
      setDocumentStatus(retryRes);
      startStatusPolling(documentId);
    } catch (err: unknown) {
      const errObj = err as { message?: string; status?: number };
      setIsRetrying(false);
      setUploadState('failed');
      setDocumentError(errObj.message || 'Failed to retry document extraction.');
    }
  };

  // Submit Application (Feature 3B)
  const handleSubmitApplication = async () => {
    if (!jobId || !documentId) {
      setSubmissionError('Cannot submit application: missing requisition or verified document.');
      return;
    }

    if (uploadState !== 'completed') {
      setSubmissionError('Document extraction must complete successfully before submitting application.');
      return;
    }

    if (!hasConfirmedDeclaration) {
      setSubmissionError('Please confirm the application declaration before submitting.');
      return;
    }

    setIsSubmittingApp(true);
    setSubmissionError(null);

    try {
      const newApp = await applicationService.submitApplication(jobId, documentId);

      // Clean up pending document from storage upon successful backend application creation
      if (user?.id && jobId) {
        pendingDocumentStore.removePendingDocument(user.id, jobId);
      }

      setSubmittedApplication(newApp);
      setExistingApplication(newApp);

      // Navigate to the newly created application detail dossier after brief feedback
      setTimeout(() => {
        navigate(`/candidate/applications/${newApp.id}`);
      }, 1200);
    } catch (err: unknown) {
      const errObj = err as { message?: string; status?: number };
      if (errObj.status === 409) {
        setSubmissionError(
          'An application for this requisition has already been submitted by your account.'
        );
      } else {
        setSubmissionError(errObj.message || 'Failed to submit application. Please check your connection and retry.');
      }
    } finally {
      setIsSubmittingApp(false);
    }
  };

  const scrollToUpload = () => {
    uploadSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  if (isLoading || isCheckingExistingApp || isRestoringDocument) {
    return (
      <div className="max-w-7xl mx-auto space-y-6 select-none animate-pulse">
        <div className="h-4 w-32 bg-surface rounded-pill" />
        <div className="bg-surface rounded-card p-8 border border-subtle shadow-card space-y-4">
          <div className="h-6 w-1/4 bg-elevated rounded-pill" />
          <div className="h-10 w-1/2 bg-elevated rounded-sm" />
          <div className="h-4 w-1/3 bg-elevated rounded-sm" />
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="max-w-xl mx-auto py-16 px-4 text-center select-none space-y-4">
        <div className="w-12 h-12 rounded-full bg-danger-dim border border-danger/30 text-danger flex items-center justify-center mx-auto">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-semibold text-ink tracking-tight">Requisition Unavailable</h2>
        <p className="text-xs text-muted max-w-sm mx-auto font-medium leading-relaxed">
          {error || 'The requested job posting could not be found.'}
        </p>
        <div className="pt-2">
          <Button
            onClick={() => navigate('/candidate/jobs')}
            variant="secondary"
            size="sm"
            leftIcon={<ArrowLeft className="w-4 h-4" />}
          >
            Back to Open Requisitions
          </Button>
        </div>
      </div>
    );
  }

  // Calculate extracted stats
  const pageEntries = Object.entries(documentStatus?.extracted_text_by_page || {}).sort(
    ([a], [b]) => parseInt(a, 10) - parseInt(b, 10)
  );
  const totalCharacters = pageEntries.reduce((sum, [, text]) => sum + text.length, 0);

  return (
    <div className="max-w-7xl mx-auto space-y-6 select-none">
      {/* ── Back Navigation ───────────────────────────────────── */}
      <div>
        <button
          onClick={() => navigate('/candidate/jobs')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to open requisitions
        </button>
      </div>

      {/* ── Hero Header Card ──────────────────────────────────── */}
      <div className="bg-surface rounded-card p-6 md:p-8 border border-subtle shadow-card flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium px-3 py-1 rounded-pill bg-elevated text-muted border border-subtle">
              {job.department || 'General'}
            </span>
            <span className="text-xs font-medium px-3 py-1 rounded-pill bg-success-dim text-success border border-success/30">
              Active Opening
            </span>
            {existingApplication && (
              <span className="text-xs font-semibold px-3 py-1 rounded-pill bg-accent-dim text-accent border border-accent/30">
                Applied
              </span>
            )}
          </div>
          <h1 className="text-2xl md:text-3xl font-semibold text-ink tracking-tight">
            {job.title}
          </h1>
          <p className="text-xs text-muted mt-1.5 flex items-center gap-2 font-medium">
            <span>Requisition ID: {job.id.slice(0, 8)}</span>
            <span>•</span>
            <span>Posted {new Date(job.created_at).toLocaleDateString()}</span>
          </p>
        </div>

        {existingApplication ? (
          <Button
            onClick={() => navigate(`/candidate/applications/${existingApplication.id}`)}
            variant="secondary"
            size="md"
            rightIcon={<ExternalLink className="w-4 h-4" />}
            className="font-semibold shadow-sm shrink-0"
          >
            View My Application
          </Button>
        ) : (
          <Button
            onClick={scrollToUpload}
            variant="primary"
            size="md"
            rightIcon={<UploadCloud className="w-4 h-4" />}
            className="font-semibold shadow-sm shrink-0"
          >
            Apply with Resume
          </Button>
        )}
      </div>

      {/* ── APPLICATION & DOCUMENT WORKSPACE SECTION ──────────── */}
      <div
        ref={uploadSectionRef}
        className="bg-surface rounded-card p-6 md:p-8 border border-subtle shadow-card space-y-6 scroll-mt-6"
      >
        {/* Existing Application Banner (Duplicate Prevention Guard) */}
        {existingApplication ? (
          <div className="p-6 rounded-card bg-accent-dim border border-accent/30 space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-accent/20 border border-accent/40 text-accent flex items-center justify-center shrink-0 mt-0.5">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-ink">
                      Application Already Submitted
                    </h3>
                    <StatusBadge status={existingApplication.status} size="sm" />
                  </div>
                  <p className="text-xs text-ink/90 leading-relaxed font-medium">
                    You have already submitted an application for <strong className="text-ink">{job.title}</strong> on{' '}
                    {new Date(existingApplication.submitted_at || existingApplication.created_at).toLocaleDateString()}.
                    Per ClearHire deterministic screening integrity, each candidate submits one official dossier per requisition.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-accent/20">
              <Button
                onClick={() => navigate(`/candidate/applications/${existingApplication.id}`)}
                variant="primary"
                size="sm"
                rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                className="text-xs font-semibold"
              >
                Inspect Application Dossier
              </Button>
              <Button
                onClick={() => navigate('/candidate/jobs')}
                variant="secondary"
                size="sm"
                className="text-xs font-medium"
              >
                Browse Other Requisitions
              </Button>
            </div>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-subtle">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="w-2 h-2 rounded-full bg-accent" />
                  <span className="text-[10px] text-accent font-semibold uppercase tracking-wider">
                    Application Pipeline
                  </span>
                </div>
                <h2 className="text-lg font-semibold text-ink tracking-tight">
                  Candidate Resume Ingestion & Application Submission
                </h2>
                <p className="text-xs text-muted mt-0.5 font-medium">
                  Upload your official resume in PDF format (maximum 15 MB). Verbatim text will be extracted with preserved page boundaries before formal application submission.
                </p>
              </div>

              {uploadState === 'completed' && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-success-dim text-success border border-success/30 text-xs font-semibold self-start sm:self-auto">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Extraction Completed
                </span>
              )}
            </div>

            {/* ── State 1: Dropzone / File Selection ── */}
            {uploadState === 'idle' && !selectedFile && (
              <div className="space-y-4">
                {recoveryNotice && (
                  <div className="p-3.5 rounded-card bg-accent-dim border border-accent/30 text-ink text-xs font-medium flex items-start gap-2.5">
                    <AlertCircle className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                    <span>{recoveryNotice}</span>
                  </div>
                )}
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".pdf,application/pdf"
                  className="hidden"
                  id="resume-file-input"
                />

                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-card p-8 sm:p-10 text-center cursor-pointer transition-all ${
                    isDragging
                      ? 'border-accent bg-accent/5'
                      : 'border-subtle hover:border-accent/50 bg-elevated/40 hover:bg-elevated/80'
                  }`}
                >
                  <div className="w-12 h-12 rounded-xl bg-accent-dim text-accent border border-accent/30 mx-auto flex items-center justify-center mb-3">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-semibold text-ink">
                    Click to browse or drag and drop your resume
                  </h3>
                  <p className="text-xs text-muted mt-1 font-medium">
                    Supports authentic PDF files up to <strong className="text-ink">15 MB</strong>.
                  </p>
                  <div className="mt-4 inline-flex items-center gap-2 text-[11px] font-semibold text-accent bg-accent/10 px-3 py-1 rounded-pill border border-accent/20">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Zero Silent Rejections — Verbatim Citation Engine</span>
                  </div>
                </div>

                {validationError && (
                  <div className="p-4 rounded-sm bg-danger-dim border border-danger/30 text-danger text-xs font-medium flex items-start gap-2.5">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <div>
                      <strong className="font-semibold block">Invalid File Selection</strong>
                      <span>{validationError}</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── State 2: File Selected (Ready to Upload) ── */}
            {selectedFile && uploadState === 'idle' && (
              <div className="space-y-4">
                <div className="p-4 rounded-card bg-elevated border border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3.5">
                    <div className="w-10 h-10 rounded-xl bg-accent-dim text-accent border border-accent/30 flex items-center justify-center shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-xs font-semibold text-ink truncate max-w-md">
                        {selectedFile.name}
                      </h4>
                      <div className="flex items-center gap-2 mt-0.5 text-[11px] text-muted font-medium">
                        <span>{formatBytes(selectedFile.size)}</span>
                        <span>•</span>
                        <span className="text-accent">Ready for server ingestion</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-auto">
                    <Button
                      onClick={handleRemoveFile}
                      variant="secondary"
                      size="sm"
                      leftIcon={<Trash2 className="w-3.5 h-3.5" />}
                      className="text-xs"
                    >
                      Remove
                    </Button>
                    <Button
                      onClick={handleUpload}
                      variant="primary"
                      size="sm"
                      rightIcon={<UploadCloud className="w-3.5 h-3.5" />}
                      className="text-xs font-semibold"
                    >
                      Upload & Extract
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* ── State 3: Uploading / Processing State ── */}
            {(uploadState === 'uploading' || uploadState === 'processing') && (
              <div className="p-8 rounded-card bg-elevated border border-subtle text-center space-y-4">
                <LoadingSpinner size="lg" />
                <div className="space-y-1 max-w-sm mx-auto">
                  <h4 className="text-sm font-semibold text-ink">
                    {uploadState === 'uploading'
                      ? 'Uploading Resume PDF...'
                      : 'Processing Document Text Extraction...'}
                  </h4>
                  <p className="text-xs text-muted leading-relaxed font-medium">
                    {uploadState === 'uploading'
                      ? 'Transmitting file to secure FastAPI storage...'
                      : 'FastAPI background worker is reading PDF pages and extracting verbatim text with page citations.'}
                  </p>
                </div>
                {documentId && (
                  <span className="inline-block text-[10px] font-mono text-muted bg-surface px-2.5 py-1 rounded border border-subtle">
                    DOC #{documentId.slice(0, 8)}
                  </span>
                )}
              </div>
            )}

            {/* ── State 4: Extraction Failed ── */}
            {uploadState === 'failed' && (
              <div className="p-6 rounded-card bg-danger-dim border border-danger/30 space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-danger/20 border border-danger/30 text-danger flex items-center justify-center shrink-0 mt-0.5">
                    <AlertCircle className="w-5 h-5" />
                  </div>
                  <div className="space-y-1 min-w-0">
                    <h4 className="text-sm font-semibold text-danger">Document Processing Failed</h4>
                    <p className="text-xs text-ink/90 leading-relaxed font-medium">
                      {documentError || 'The server encountered an error extracting text from this resume.'}
                    </p>
                    {documentStatus?.processing_error?.code && (
                      <span className="inline-block text-[10px] font-mono text-danger bg-surface/50 px-2 py-0.5 rounded border border-danger/20 mt-1">
                        CODE: {documentStatus.processing_error.code}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3 pt-2 border-t border-danger/20">
                  {documentId && (
                    <Button
                      onClick={handleRetryProcessing}
                      variant="secondary"
                      size="sm"
                      disabled={isRetrying}
                      leftIcon={
                        <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
                      }
                      className="text-xs font-semibold"
                    >
                      {isRetrying ? 'Retrying...' : 'Retry Extraction'}
                    </Button>
                  )}
                  <Button
                    onClick={handleRemoveFile}
                    variant="secondary"
                    size="sm"
                    className="text-xs font-medium"
                  >
                    Upload Different File
                  </Button>
                </div>
              </div>
            )}

            {/* ── State 5: Extraction Completed — Extracted Text Viewer & Application Submission ── */}
            {uploadState === 'completed' && documentStatus && (
              <div className="space-y-6">
                {/* Metadata Summary Banner */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3.5 rounded-card bg-elevated border border-subtle">
                    <span className="text-[10px] text-muted uppercase font-semibold block">Filename</span>
                    <span className="text-xs font-semibold text-ink truncate block mt-0.5" title={documentStatus.file_name}>
                      {documentStatus.file_name}
                    </span>
                  </div>
                  <div className="p-3.5 rounded-card bg-elevated border border-subtle">
                    <span className="text-[10px] text-muted uppercase font-semibold block">Total Pages</span>
                    <span className="text-xs font-semibold text-ink block mt-0.5">
                      {documentStatus.page_count ?? pageEntries.length} Page(s)
                    </span>
                  </div>
                  <div className="p-3.5 rounded-card bg-elevated border border-subtle">
                    <span className="text-[10px] text-muted uppercase font-semibold block">Extracted Characters</span>
                    <span className="text-xs font-semibold text-ink block mt-0.5">
                      {totalCharacters.toLocaleString()} chars
                    </span>
                  </div>
                  <div className="p-3.5 rounded-card bg-elevated border border-subtle">
                    <span className="text-[10px] text-muted uppercase font-semibold block">Lifecycle Status</span>
                    <span className="text-xs font-semibold text-success block mt-0.5">
                      COMPLETED
                    </span>
                  </div>
                </div>

                {/* Clear Transparency Notice */}
                <div className="p-4 rounded-card bg-accent-dim border border-accent/30 text-xs text-ink/90 flex items-start gap-3">
                  <Sparkles className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                  <div className="space-y-0.5">
                    <strong className="text-ink font-semibold block">
                      Verbatim Document Extraction Confirmed
                    </strong>
                    <p className="text-[11px] leading-relaxed text-muted">
                      Review your extracted resume text below. When ready, formally submit your application to attach this document to requisition <strong className="text-ink">{job.title}</strong>.
                    </p>
                  </div>
                </div>

                {/* Page Navigation Tabs & Text Box */}
                {pageEntries.length > 0 ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between gap-2 overflow-x-auto pb-1 border-b border-subtle">
                      <div className="flex items-center gap-1.5">
                        {pageEntries.map(([pageNum]) => (
                          <button
                            key={pageNum}
                            onClick={() => setSelectedPageTab(pageNum)}
                            className={`px-3 py-1.5 rounded-pill text-xs font-semibold transition-all cursor-pointer ${
                              selectedPageTab === pageNum
                                ? 'bg-elevated text-accent border border-accent/40 shadow-sm'
                                : 'text-muted hover:text-ink'
                            }`}
                          >
                            Page {pageNum}
                          </button>
                        ))}
                      </div>

                      <span className="text-[11px] text-muted font-medium shrink-0">
                        Showing Page {selectedPageTab} of {pageEntries.length}
                      </span>
                    </div>

                    <div className="relative">
                      <div className="bg-elevated border border-subtle rounded-card p-5 max-h-[320px] overflow-y-auto font-mono text-xs text-ink/90 whitespace-pre-wrap leading-relaxed select-text">
                        {documentStatus.extracted_text_by_page[selectedPageTab] || (
                          <span className="text-muted italic">No extractable digital text on Page {selectedPageTab}.</span>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-8 rounded-card bg-elevated border border-subtle text-center text-xs text-muted">
                    Document contains no extractable text pages.
                  </div>
                )}

                {/* ── APPLICATION SUBMISSION FORM (FEATURE 3B) ── */}
                <div className="p-6 rounded-card bg-elevated border border-accent/30 space-y-4">
                  <div className="flex items-start justify-between gap-4 pb-3 border-b border-subtle">
                    <div>
                      <span className="text-[10px] text-accent font-semibold uppercase tracking-wider block">
                        Formal Application Confirmation
                      </span>
                      <h3 className="text-sm font-semibold text-ink mt-0.5">
                        Submit Application for {job.title}
                      </h3>
                      <p className="text-xs text-muted mt-0.5">
                        This action links your verified document <strong className="text-ink">{documentStatus.file_name}</strong> to requisition <strong className="text-ink">{job.title}</strong>.
                      </p>
                    </div>

                    <span className="text-[11px] font-medium text-muted bg-surface px-2.5 py-1 rounded border border-subtle shrink-0">
                      Doc ID: {documentId?.slice(0, 8)}
                    </span>
                  </div>

                  {/* Submission Error Banner */}
                  {submissionError && (
                    <div className="p-3.5 rounded-sm bg-danger-dim border border-danger/30 text-danger text-xs font-medium flex items-start gap-2.5">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <div>
                        <strong className="font-semibold block">Submission Error</strong>
                        <span>{submissionError}</span>
                      </div>
                    </div>
                  )}

                  {/* Confirmation Declaration Checkbox */}
                  <label className="flex items-start gap-3 p-3.5 rounded-card bg-surface border border-subtle cursor-pointer hover:border-accent/40 transition-colors">
                    <input
                      type="checkbox"
                      checked={hasConfirmedDeclaration}
                      onChange={(e) => setHasConfirmedDeclaration(e.target.checked)}
                      className="mt-0.5 w-4 h-4 rounded text-accent focus:ring-accent bg-elevated border-subtle cursor-pointer"
                    />
                    <div className="space-y-0.5 text-xs">
                      <span className="font-semibold text-ink block">
                        Candidate Verification Declaration
                      </span>
                      <span className="text-muted leading-relaxed font-medium block">
                        I confirm that the uploaded document represents my accurate professional experience for the position of <strong className="text-ink">{job.title}</strong>. I understand that evaluations will be benchmarked deterministically against published requirements.
                      </span>
                    </div>
                  </label>

                  {/* Submit Actions */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
                    <Button
                      onClick={handleRemoveFile}
                      variant="secondary"
                      size="sm"
                      leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                      className="text-xs font-medium self-start sm:self-auto"
                    >
                      Upload Different Resume
                    </Button>

                    <Button
                      onClick={handleSubmitApplication}
                      disabled={!hasConfirmedDeclaration || isSubmittingApp}
                      variant="primary"
                      size="md"
                      rightIcon={
                        isSubmittingApp ? (
                          <LoadingSpinner size="sm" />
                        ) : (
                          <ArrowRight className="w-4 h-4" />
                        )
                      }
                      className="text-xs font-semibold shadow-sm self-stretch sm:self-auto justify-center"
                    >
                      {isSubmittingApp ? 'Submitting Application...' : 'Submit Application Now'}
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Two Column Layout: Description & Criteria ─────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Job Description & Guarantee */}
        <div className="lg:col-span-7 bg-surface rounded-card p-6 md:p-8 border border-subtle shadow-card space-y-6">
          <div>
            <h2 className="text-base font-semibold text-ink tracking-tight mb-2">Position Overview</h2>
            <p className="text-xs text-muted leading-relaxed whitespace-pre-line font-medium">
              {job.description || 'This position is evaluated objectively against verified resume excerpts.'}
            </p>
          </div>

          <div className="pt-4 border-t border-subtle">
            <h3 className="text-sm font-semibold text-ink mb-3">ClearHire Transparency Guarantee</h3>
            <div className="bg-accent-dim border border-accent/30 rounded-card p-5 text-xs text-ink space-y-3">
              <div className="flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                <span>
                  <strong className="text-ink font-semibold">No silent rejections:</strong> Every criterion listed on this page is evaluated strictly against verbatim citations in your resume.
                </span>
              </div>
              <div className="flex items-start gap-2.5">
                <Sparkles className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                <span>
                  <strong className="text-ink font-semibold">Right to clarification:</strong> If an AI evaluation marks your experience as ambiguous, you receive instant access to contest the evaluation with written proof.
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Explicit Versioned Criteria */}
        <div className="lg:col-span-5 bg-surface rounded-card p-6 md:p-8 border border-subtle shadow-card space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-subtle">
            <h3 className="text-base font-semibold text-ink tracking-tight">Screening Criteria</h3>
            <span className="text-[11px] font-medium text-muted bg-elevated px-2.5 py-1 rounded-pill border border-subtle">
              v1.0 Immutable
            </span>
          </div>
          <p className="text-xs text-muted font-medium">
            Your uploaded resume will be matched directly against these explicit benchmarks:
          </p>

          <div className="space-y-3">
            {job.criteria && job.criteria.length > 0 ? (
              job.criteria.map((c, i) => (
                <div key={c.id || i} className="p-3.5 rounded-sm border border-subtle bg-elevated space-y-1">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-[10px] font-medium text-muted">#0{i + 1}</span>
                    <span
                      className={`text-[9px] font-semibold px-2 py-0.5 rounded-pill uppercase tracking-wider ${
                        c.category === 'required'
                          ? 'bg-accent-dim text-accent border border-accent/30'
                          : 'bg-surface text-muted border border-subtle'
                      }`}
                    >
                      {c.category}
                    </span>
                  </div>
                  <h4 className="text-xs font-semibold text-ink">{c.name}</h4>
                  {c.description && (
                    <p className="text-[11px] text-muted leading-relaxed font-medium">{c.description}</p>
                  )}
                </div>
              ))
            ) : (
              <div className="text-xs text-muted py-6 text-center">
                No criteria defined on this requisition.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
