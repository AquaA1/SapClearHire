import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { jobService } from '../../services/api/jobService';
import { documentService } from '../../services/api/documentService';
import { Job, DocumentStatusResponse } from '../../contracts/models';
import { DocumentProcessingStatus } from '../../contracts/enums';
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
  ChevronRight,
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

  // Requisition State
  const [job, setJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  // Fetch Job Requisition Details
  useEffect(() => {
    if (!jobId) {
      setError('No requisition identifier specified.');
      setIsLoading(false);
      return;
    }

    const fetchJobDetail = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const found = await jobService.getJob(jobId);
        setJob(found);
      } catch (err: unknown) {
        const errObj = err as { message?: string; status?: number };
        if (errObj.status === 404) {
          setError(`Job requisition "${jobId}" was not found or is no longer available.`);
        } else {
          setError(errObj.message || 'Failed to retrieve requisition details from server.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobDetail();
  }, [jobId]);

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
    }
    // Reset file input value so re-selecting same file triggers change
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
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setValidationError(null);
    setUploadState('idle');
    setDocumentId(null);
    setDocumentStatus(null);
    setDocumentError(null);
    stopPolling();
  };

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

            // Select first page by default
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

  // Upload Trigger
  const handleUpload = async () => {
    if (!selectedFile) return;
    if (uploadState === 'uploading' || uploadState === 'processing') return;

    setUploadState('uploading');
    setDocumentError(null);
    setValidationError(null);

    try {
      const uploadRes = await documentService.uploadDocument(selectedFile);
      setDocumentId(uploadRes.id);
      setUploadState('processing');

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

  const scrollToUpload = () => {
    uploadSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  if (isLoading) {
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

        <Button
          onClick={scrollToUpload}
          variant="primary"
          size="md"
          rightIcon={<UploadCloud className="w-4 h-4" />}
          className="font-semibold shadow-sm shrink-0"
        >
          Upload Resume
        </Button>
      </div>

      {/* ── RESUME UPLOAD & AI DOCUMENT EXTRACTION STUDIO ─────── */}
      <div
        ref={uploadSectionRef}
        className="bg-surface rounded-card p-6 md:p-8 border border-subtle shadow-card space-y-6 scroll-mt-6"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-subtle">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2 h-2 rounded-full bg-accent" />
              <span className="text-[10px] text-accent font-semibold uppercase tracking-wider">
                Document Ingestion Pipeline
              </span>
            </div>
            <h2 className="text-lg font-semibold text-ink tracking-tight">
              Resume Upload & Verbatim Text Extraction
            </h2>
            <p className="text-xs text-muted mt-0.5 font-medium">
              Upload your official resume PDF. The server extracts raw text with original page boundaries for objective qualification matching.
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
        {(uploadState === 'idle' || !selectedFile) && uploadState !== 'completed' && (
          <div className="space-y-4">
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

        {/* ── State 5: Extraction Completed — Extracted Text Viewer ── */}
        {uploadState === 'completed' && documentStatus && (
          <div className="space-y-5">
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
                  This viewer displays raw textual excerpts extracted directly from your PDF document by page.
                  Candidate qualification evaluation, evidence grounding, and criteria matching will occur upon application submission.
                </p>
              </div>
            </div>

            {/* Page Navigation Tabs */}
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

                {/* Extracted Page Text Box */}
                <div className="relative">
                  <div className="bg-elevated border border-subtle rounded-card p-5 max-h-[360px] overflow-y-auto font-mono text-xs text-ink/90 whitespace-pre-wrap leading-relaxed select-text">
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

            {/* Action Bar */}
            <div className="flex items-center justify-between pt-2 border-t border-subtle">
              <Button
                onClick={handleRemoveFile}
                variant="secondary"
                size="sm"
                leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                className="text-xs"
              >
                Upload Different Resume
              </Button>

              <span className="text-[11px] text-muted font-medium">
                Document ID: <code className="text-accent font-mono">{documentId}</code>
              </span>
            </div>
          </div>
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
