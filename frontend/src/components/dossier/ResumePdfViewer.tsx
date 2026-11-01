import React, { useEffect, useState, useRef } from 'react';
import { documentService } from '../../services/api/documentService';
import { DocumentStatusResponse } from '../../contracts/models';
import {
  FileText,
  Download,
  ExternalLink,
  Search,
  Copy,
  Check,
  AlertCircle,
  RefreshCw,
  Eye,
  FileCode,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react';
import { Button, LoadingSpinner, StatusBadge } from '../ui';

interface ResumePdfViewerProps {
  documentId: string;
  applicationId?: string;
  onRetrySuccess?: () => void;
}

export const ResumePdfViewer: React.FC<ResumePdfViewerProps> = ({
  documentId,
  applicationId,
  onRetrySuccess,
}) => {
  const [docStatus, setDocStatus] = useState<DocumentStatusResponse | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [filename, setFilename] = useState<string>('resume.pdf');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'pdf' | 'text'>('pdf');
  const [selectedPage, setSelectedPage] = useState<string>('1');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);
  const [isRetrying, setIsRetrying] = useState<boolean>(false);

  // Keep ref of active blob URL for cleanup
  const activeBlobUrlRef = useRef<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    const loadDocumentAndPdf = async () => {
      setLoading(true);
      setError(null);
      setErrorStatus(null);

      // Clean up previous blob URL
      if (activeBlobUrlRef.current) {
        URL.revokeObjectURL(activeBlobUrlRef.current);
        activeBlobUrlRef.current = null;
        setBlobUrl(null);
      }

      try {
        // 1. Fetch document metadata and status
        const status = await documentService.getDocumentStatus(documentId);
        if (isCancelled) return;
        setDocStatus(status);

        const pages = Object.keys(status.extracted_text_by_page || {});
        if (pages.length > 0 && !pages.includes(selectedPage)) {
          setSelectedPage(pages[0]);
        }

        // 2. Fetch original PDF binary as authenticated Blob
        try {
          const fileResult = await documentService.getDocumentFile(documentId, 'inline');
          if (isCancelled) return;

          const url = URL.createObjectURL(fileResult.blob);
          activeBlobUrlRef.current = url;
          setBlobUrl(url);
          setFilename(fileResult.filename || status.file_name || 'resume.pdf');
        } catch (pdfErr: any) {
          console.warn('PDF stream retrieval error:', pdfErr);
          // If PDF binary failed, we still have metadata and extracted text
          if (pdfErr?.status === 403) {
            setErrorStatus(403);
            setError('Access Denied: You do not have permission to view this resume document.');
          } else if (pdfErr?.status === 404) {
            setErrorStatus(404);
            setError('Original PDF file was not found in storage. Extracted text may still be available.');
          } else {
            setErrorStatus(pdfErr?.status || 500);
            setError(pdfErr?.message || 'Failed to stream original PDF file.');
          }
          // Default to text mode if PDF fails
          setViewMode('text');
        }
      } catch (statusErr: any) {
        console.error('Document status error:', statusErr);
        if (statusErr?.status === 403) {
          setErrorStatus(403);
          setError('Access Denied: You are not authorized to view this candidate dossier document.');
        } else if (statusErr?.status === 404) {
          setErrorStatus(404);
          setError('Document record not found in system.');
        } else {
          setErrorStatus(statusErr?.status || 500);
          setError(statusErr?.message || 'Failed to load document record.');
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    };

    if (documentId) {
      loadDocumentAndPdf();
    }

    return () => {
      isCancelled = true;
      if (activeBlobUrlRef.current) {
        URL.revokeObjectURL(activeBlobUrlRef.current);
        activeBlobUrlRef.current = null;
      }
    };
  }, [documentId]);

  const handleDownload = () => {
    if (!blobUrl) return;
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleOpenInNewTab = () => {
    if (!blobUrl) return;
    window.open(blobUrl, '_blank', 'noopener,noreferrer');
  };

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRetry = async () => {
    if (!documentId) return;
    setIsRetrying(true);
    try {
      const updated = await documentService.retryDocumentProcessing(documentId);
      setDocStatus(updated);
      setError(null);
      if (onRetrySuccess) onRetrySuccess();
    } catch (err: any) {
      setError(err?.message || 'Retry failed');
    } finally {
      setIsRetrying(false);
    }
  };

  // Format file size
  const formatFileSize = (bytes?: number) => {
    if (!bytes) return null;
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  if (loading) {
    return (
      <div className="bg-surface rounded-card border border-subtle p-12 text-center shadow-card space-y-4">
        <LoadingSpinner size="lg" label="Retrieving authentic resume PDF from secure storage..." />
        <p className="text-xs text-muted max-w-sm mx-auto">
          Verifying tenant authorization and decrypting document stream...
        </p>
      </div>
    );
  }

  // Permission Denied State
  if (errorStatus === 403) {
    return (
      <div className="bg-surface rounded-card border border-danger/40 p-10 text-center shadow-card space-y-3">
        <ShieldCheck className="w-12 h-12 text-danger mx-auto opacity-75" />
        <h3 className="text-sm font-semibold text-ink">Document Access Restricted</h3>
        <p className="text-xs text-muted max-w-md mx-auto leading-relaxed">
          {error || 'You do not have organizational authorization to inspect this document.'}
        </p>
      </div>
    );
  }

  // Not Found State
  if (errorStatus === 404 && !docStatus) {
    return (
      <div className="bg-surface rounded-card border border-subtle p-10 text-center shadow-card space-y-3">
        <AlertTriangle className="w-12 h-12 text-warn mx-auto opacity-75" />
        <h3 className="text-sm font-semibold text-ink">Resume Document Not Found</h3>
        <p className="text-xs text-muted max-w-md mx-auto leading-relaxed">
          The requested document record does not exist or may have been deleted.
        </p>
      </div>
    );
  }

  const pageEntries = Object.entries(docStatus?.extracted_text_by_page || {}).sort(
    ([a], [b]) => parseInt(a, 10) - parseInt(b, 10)
  );

  const activePageText = docStatus?.extracted_text_by_page?.[selectedPage] || '';

  // Filter text by search query
  const matchesSearch = (text: string) => {
    if (!searchQuery.trim()) return true;
    return text.toLowerCase().includes(searchQuery.toLowerCase().trim());
  };

  const countOccurrences = (text: string, query: string) => {
    if (!query.trim()) return 0;
    const re = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    return (text.match(re) || []).length;
  };

  const matchCount = searchQuery.trim() ? countOccurrences(activePageText, searchQuery) : 0;

  return (
    <div className="space-y-4">
      {/* ── Document Control Header Bar ────────────────────────────── */}
      <div className="bg-surface rounded-card border border-subtle p-4 shadow-card">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* File Metadata */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-elevated border border-subtle flex items-center justify-center text-accent shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-xs font-semibold text-ink truncate max-w-xs sm:max-w-md">
                  {docStatus?.file_name || filename}
                </h4>
                {docStatus?.processing_status && (
                  <StatusBadge status={docStatus.processing_status} size="sm" />
                )}
              </div>
              <div className="flex items-center gap-2 mt-0.5 text-[11px] text-muted font-medium">
                <span>{docStatus?.page_count ? `${docStatus.page_count} Pages` : '1 Page'}</span>
                {docStatus?.file_size_bytes && (
                  <>
                    <span>•</span>
                    <span>{formatFileSize(docStatus.file_size_bytes)}</span>
                  </>
                )}
                <span>•</span>
                <span>Uploaded {docStatus?.created_at ? new Date(docStatus.created_at).toLocaleDateString() : 'Recently'}</span>
                <span>•</span>
                <span className="font-mono text-[10px]">Doc #{documentId.slice(0, 8)}</span>
              </div>
            </div>
          </div>

          {/* Actions & View Mode Toggle */}
          <div className="flex items-center flex-wrap gap-2">
            {/* View Mode Toggle */}
            <div className="bg-elevated p-0.5 rounded border border-subtle flex items-center">
              <button
                type="button"
                onClick={() => setViewMode('pdf')}
                disabled={!blobUrl}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-all ${
                  viewMode === 'pdf'
                    ? 'bg-surface text-ink shadow-sm'
                    : 'text-muted hover:text-ink disabled:opacity-40 disabled:cursor-not-allowed'
                }`}
                title={blobUrl ? 'View original rendered PDF document' : 'PDF preview unavailable'}
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Original PDF</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('text')}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-all ${
                  viewMode === 'text'
                    ? 'bg-surface text-ink shadow-sm'
                    : 'text-muted hover:text-ink'
                }`}
                title="View page-by-page extracted OCR text"
              >
                <FileCode className="w-3.5 h-3.5" />
                <span>Extracted Text</span>
              </button>
            </div>

            {/* Open In New Tab */}
            {blobUrl && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleOpenInNewTab}
                leftIcon={<ExternalLink className="w-3.5 h-3.5" />}
                className="text-xs"
              >
                Open in Tab
              </Button>
            )}

            {/* Download PDF Button */}
            {blobUrl && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleDownload}
                leftIcon={<Download className="w-3.5 h-3.5" />}
                className="text-xs"
              >
                Download PDF
              </Button>
            )}

            {/* Retry Button if Failed */}
            {docStatus?.processing_status === 'failed' && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleRetry}
                isLoading={isRetrying}
                leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                className="text-xs text-danger"
              >
                Retry Processing
              </Button>
            )}
          </div>
        </div>

        {/* Processing Warning if Failed or Processing */}
        {docStatus?.processing_status === 'failed' && (
          <div className="mt-3 p-3 rounded bg-danger-dim border border-danger/30 text-xs text-danger flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold block">Text Extraction Failed</strong>
              <span>
                {docStatus?.processing_error?.message ||
                  'The automated text extractor encountered an error with this file. Click Retry to re-run extraction.'}
              </span>
            </div>
          </div>
        )}

        {error && viewMode === 'text' && (
          <div className="mt-3 p-3 rounded bg-warn-dim border border-warn/30 text-xs text-warn flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* ── Main Viewer Body: PDF vs Extracted Text ────────────────── */}
      {viewMode === 'pdf' && blobUrl ? (
        <div className="bg-surface rounded-card border border-subtle p-2 shadow-card">
          <div className="w-full h-[700px] rounded overflow-hidden bg-elevated/40 relative">
            <iframe
              src={`${blobUrl}#toolbar=1&navpanes=1`}
              title={filename}
              className="w-full h-full border-none rounded"
            />
          </div>
        </div>
      ) : (
        /* ── Page-by-Page Extracted Text Viewer ──────────────────── */
        <div className="bg-surface rounded-card border border-subtle p-5 shadow-card space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-subtle">
            {/* Page Tabs */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
              {pageEntries.length > 0 ? (
                pageEntries.map(([pageNum]) => (
                  <button
                    key={pageNum}
                    type="button"
                    onClick={() => setSelectedPage(pageNum)}
                    className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
                      selectedPage === pageNum
                        ? 'bg-accent text-surface shadow-sm'
                        : 'bg-elevated/60 text-muted hover:text-ink border border-subtle'
                    }`}
                  >
                    Page {pageNum}
                  </button>
                ))
              ) : (
                <span className="text-xs text-muted">Page 1 (No pages detected)</span>
              )}
            </div>

            {/* Search Input & Copy Button */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-muted absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search page text..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-elevated border border-subtle rounded pl-8 pr-3 py-1 text-xs text-ink placeholder:text-muted focus:outline-none focus:border-accent w-48 font-medium"
                />
              </div>

              {searchQuery.trim() && (
                <span className="text-[11px] text-muted font-medium shrink-0">
                  {matchCount} match{matchCount === 1 ? '' : 'es'}
                </span>
              )}

              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleCopyText(activePageText)}
                leftIcon={copied ? <Check className="w-3.5 h-3.5 text-accent" /> : <Copy className="w-3.5 h-3.5" />}
                className="text-xs"
              >
                {copied ? 'Copied' : 'Copy Page'}
              </Button>
            </div>
          </div>

          {/* Text Container with Monospace Styling */}
          <div className="relative">
            <div className="bg-elevated/60 border border-subtle rounded p-5 max-h-[550px] overflow-y-auto font-mono text-xs text-ink/90 whitespace-pre-wrap leading-relaxed select-text">
              {activePageText ? (
                matchesSearch(activePageText) ? (
                  activePageText
                ) : (
                  <div className="text-center py-8 text-muted italic">
                    No matches found on Page {selectedPage} for "{searchQuery}".
                  </div>
                )
              ) : (
                <div className="text-center py-8 text-muted italic">
                  No extractable digital text found on Page {selectedPage}.
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] text-muted pt-2 border-t border-subtle">
            <span>
              Verbatim extraction provided by backend PyMuPDF engine with page anchors.
            </span>
            <span className="font-mono">
              Page {selectedPage} of {pageEntries.length || 1}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
