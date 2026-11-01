import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { applicationService } from '../../services/api/applicationService';
import { evaluationService } from '../../services/api/evaluationService';
import { reviewService } from '../../services/api/reviewService';
import { documentService } from '../../services/api/documentService';
import { Application, Evaluation, DocumentStatusResponse } from '../../contracts/models';
import { StatusBadge } from '../../components/ui/Badge';
import { CoverageSummaryBar } from '../../components/evidence/CoverageSummaryBar';
import { CriterionEvidenceCard } from '../../components/evidence/CriterionEvidenceCard';
import { ClarificationModal } from '../../components/evidence/ClarificationModal';
import {
  ArrowLeft,
  Clock,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  FileText,
  AlertTriangle,
  RotateCw,
  Loader2,
} from 'lucide-react';
import { VerificationState } from '../../contracts/enums';
import { Button, LoadingSpinner } from '../../components/ui';

export const CandidateApplicationDetailPage: React.FC = () => {
  const { id, applicationId } = useParams<{ id?: string; applicationId?: string }>();
  const appId = id || applicationId;
  const navigate = useNavigate();

  const [application, setApplication] = useState<Application | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [documentStatus, setDocumentStatus] = useState<DocumentStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [pollCount, setPollCount] = useState(0);
  const [activeCriterionClarify, setActiveCriterionClarify] = useState<string | null>(null);
  const [showSuccessToast, setShowSuccessToast] = useState(false);

  useEffect(() => {
    if (!appId) {
      setError('No application identifier specified.');
      setLoading(false);
      return;
    }

    let isMounted = true;
    let pollInterval: ReturnType<typeof setInterval> | null = null;
    let attempts = 0;
    const maxAttempts = 30;

    const checkEvaluationAndStatus = async (app: Application) => {
      // 1. Check if evaluation is already available
      try {
        const ev = await evaluationService.getEvaluationByApplication(app.id);
        if (ev && isMounted) {
          setEvaluation(ev);
          setPipelineError(null);
          if (pollInterval) clearInterval(pollInterval);
          return true;
        }
      } catch {
        // Evaluation not yet created
      }

      // 2. Check document and extraction status
      if (app.primary_document_id) {
        try {
          const docStatus = await documentService.getDocumentStatus(app.primary_document_id);
          if (isMounted) setDocumentStatus(docStatus);

          if (docStatus.processing_status === 'failed') {
            if (isMounted) {
              setPipelineError(
                docStatus.processing_error?.message ||
                  'Document text extraction failed. Please retry.'
              );
              if (pollInterval) clearInterval(pollInterval);
            }
            return true;
          }
        } catch {
          // Graceful fallback
        }

        try {
          const extRun = await documentService.getExtractionResults(app.primary_document_id);
          if (extRun && extRun.status === 'failed') {
            if (isMounted) {
              setPipelineError(
                extRun.error_message ||
                  'AI claim extraction failed to process document claims.'
              );
              if (pollInterval) clearInterval(pollInterval);
            }
            return true;
          }
        } catch {
          // Graceful fallback
        }
      }

      return false;
    };

    const loadApplicationData = async () => {
      setLoading(true);
      setError(null);
      setPipelineError(null);
      try {
        const app = await applicationService.getApplication(appId);
        if (!isMounted) return;
        setApplication(app);

        const done = await checkEvaluationAndStatus(app);
        if (!done && isMounted) {
          pollInterval = setInterval(async () => {
            attempts += 1;
            if (isMounted) setPollCount(attempts);
            const finished = await checkEvaluationAndStatus(app);
            if (finished || attempts >= maxAttempts) {
              if (pollInterval) clearInterval(pollInterval);
            }
          }, 2000);
        }
      } catch (err: unknown) {
        if (!isMounted) return;
        const errObj = err as { message?: string };
        setError(errObj.message || 'Application not found or unauthorized.');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadApplicationData();

    return () => {
      isMounted = false;
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [appId]);

  const handleRetryPipeline = async () => {
    if (!application?.primary_document_id) return;
    setIsRetrying(true);
    setPipelineError(null);
    setPollCount(0);
    try {
      if (documentStatus?.processing_status === 'failed') {
        await documentService.retryDocumentProcessing(application.primary_document_id);
      } else {
        await documentService.triggerAIExtraction(application.primary_document_id);
      }
      // Re-poll for evaluation
      let attempts = 0;
      const pollInterval = setInterval(async () => {
        attempts += 1;
        setPollCount(attempts);
        try {
          const ev = await evaluationService.getEvaluationByApplication(application.id);
          if (ev) {
            setEvaluation(ev);
            setPipelineError(null);
            clearInterval(pollInterval);
            return;
          }
        } catch {
          // In progress
        }
        if (attempts >= 30) {
          clearInterval(pollInterval);
        }
      }, 2000);
    } catch (err: unknown) {
      const errObj = err as { message?: string };
      setPipelineError(errObj.message || 'Failed to trigger retry.');
    } finally {
      setIsRetrying(false);
    }
  };

  const handleClarificationSubmit = async (statement: string) => {
    if (!application || !activeCriterionClarify) return;

    try {
      await reviewService.submitClarification(application.id, {
        criterion_evidence_id: activeCriterionClarify,
        candidate_statement: statement,
      });

      // Update evaluation state locally to show clarified verification status
      if (evaluation) {
        const updatedCriteria = evaluation.criteria_evaluations.map((c) => {
          if (c.criterion_id === activeCriterionClarify) {
            return { ...c, verification_state: VerificationState.CANDIDATE_CLARIFIED };
          }
          return c;
        });
        setEvaluation({
          ...evaluation,
          criteria_evaluations: updatedCriteria,
        });
      }

      setShowSuccessToast(true);
      setTimeout(() => setShowSuccessToast(false), 4500);
    } catch (err) {
      console.error('Failed to submit clarification:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[450px]">
        <LoadingSpinner size="lg" label="Loading application evidence dossier..." />
      </div>
    );
  }

  if (error || !application) {
    return (
      <div className="bg-surface rounded-card border border-subtle p-12 text-center max-w-lg mx-auto mt-12 space-y-4 shadow-card">
        <AlertTriangle className="w-12 h-12 text-warn mx-auto" />
        <h3 className="text-base font-semibold text-ink">Application Not Found</h3>
        <p className="text-xs text-muted max-w-sm mx-auto leading-relaxed">
          {error || 'The requested application does not exist or you are not authorized to view it.'}
        </p>
        <Button onClick={() => navigate('/candidate/applications')} variant="secondary" size="sm">
          <ArrowLeft className="w-4 h-4 mr-1.5" /> Return to Applications
        </Button>
      </div>
    );
  }

  const selectedCriterion = evaluation?.criteria_evaluations.find(
    (c) => c.criterion_id === activeCriterionClarify
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6 select-none">
      {/* ── Toast Notification ────────────────────────────────── */}
      {showSuccessToast && (
        <div className="fixed top-6 right-6 z-50 bg-surface text-ink px-5 py-3.5 rounded-card shadow-modal border border-accent/40 flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-accent shrink-0" />
          <div className="text-xs">
            <span className="font-semibold block text-ink">Clarification Dispatched</span>
            <span className="text-muted font-medium">
              Your statement has been routed to the human reviewer queue.
            </span>
          </div>
        </div>
      )}

      {/* ── Back Navigation ───────────────────────────────────── */}
      <div>
        <button
          onClick={() => navigate('/candidate/applications')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to applications
        </button>
      </div>

      {/* ── Header Card ───────────────────────────────────────── */}
      <div className="bg-surface rounded-card p-6 md:p-8 border border-subtle shadow-card space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-subtle">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-medium px-3 py-0.5 rounded-pill bg-elevated text-muted border border-subtle">
                {application.department || 'General'}
              </span>
              <StatusBadge status={application.status} />
            </div>
            <h1 className="text-2xl md:text-3xl font-semibold text-ink tracking-tight">
              {application.job_title}
            </h1>
            <p className="text-xs text-muted mt-1.5 flex items-center gap-2 font-medium">
              <Clock className="w-3.5 h-3.5" />
              <span>
                Submitted on{' '}
                {new Date(application.submitted_at || application.created_at).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </span>
              <span>•</span>
              <span className="font-medium">App #{application.id.slice(0, 8)}</span>
            </p>
          </div>

          <div className="bg-elevated border border-subtle px-4 py-2.5 rounded-card text-right">
            <span className="block text-[10px] font-semibold text-muted uppercase tracking-wider">
              Transparency Status
            </span>
            <span className="text-xs font-semibold text-ink flex items-center gap-1.5 justify-end mt-0.5">
              <ShieldCheck className="w-4 h-4 text-accent" />
              Verbatim Grounding Enforced
            </span>
          </div>
        </div>

        {/* Horizontal Pipeline Progression */}
        <div>
          <span className="block text-[11px] font-semibold text-muted uppercase tracking-wider mb-3">
            Hiring Transparency Progression
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {[
              { label: '1. Submitted', active: true, done: true },
              {
                label: '2. AI Extraction',
                active: application.status !== 'submitted',
                done: !!evaluation,
              },
              {
                label: '3. Human Review',
                active: application.status === 'needs_review',
                done: application.status === 'reviewed',
              },
              {
                label: '4. Decision Ready',
                active: application.status === 'reviewed',
                done: application.status === 'reviewed',
              },
            ].map((step, idx) => (
              <div
                key={idx}
                className={`py-2 px-3 rounded-sm text-center text-xs font-medium border transition-all ${
                  step.done
                    ? 'bg-accent-dim text-accent border-accent/40 font-semibold'
                    : step.active
                    ? 'bg-elevated text-ink border-subtle-strong'
                    : 'bg-elevated/40 text-muted border-subtle'
                }`}
              >
                {step.label}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Linked Verified Document Card ─────────────────────── */}
      <div className="bg-surface rounded-card p-5 border border-subtle shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-accent-dim text-accent border border-accent/30 flex items-center justify-center shrink-0">
            <FileText className="w-5 h-5" />
          </div>
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-semibold text-ink">
                {documentStatus?.file_name || `Document #${application.primary_document_id.slice(0, 8)}.pdf`}
              </h3>
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-pill bg-success-dim text-success border border-success/30">
                Verified Evidence Source
              </span>
            </div>
            <p className="text-[11px] text-muted font-medium flex items-center gap-2">
              <span>Doc ID: {application.primary_document_id.slice(0, 8)}</span>
              {documentStatus?.page_count && (
                <>
                  <span>•</span>
                  <span>{documentStatus.page_count} {documentStatus.page_count === 1 ? 'page' : 'pages'}</span>
                </>
              )}
              <span>•</span>
              <span className="capitalize">Status: {documentStatus?.processing_status || 'completed'}</span>
            </p>
          </div>
        </div>

        <div className="text-xs text-muted font-medium bg-elevated px-3 py-1.5 rounded-pill border border-subtle self-start sm:self-auto">
          Bound to Requisition #{application.job_id.slice(0, 8)}
        </div>
      </div>

      {/* ── Evidence Coverage Summary & Criteria Breakdown ──── */}
      {evaluation ? (
        <>
          {/* Coverage Summary Bar */}
          <CoverageSummaryBar coverage={evaluation.coverage} />

          {/* Criteria Breakdown Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-ink tracking-tight">
                  Criteria Evidence Audit
                </h2>
                <p className="text-xs text-muted font-medium mt-0.5">
                  Each requirement is matched strictly against citations in your resume. Click "Contest with clarification" to submit proof.
                </p>
              </div>
              <span className="text-xs font-medium text-muted bg-elevated border border-subtle px-3 py-1 rounded-pill">
                {evaluation.criteria_evaluations.length} Criteria Evaluated
              </span>
            </div>

            <div className="space-y-4">
              {evaluation.criteria_evaluations.map((item) => (
                <CriterionEvidenceCard
                  key={item.criterion_id}
                  item={item}
                  showClarifyButton={true}
                  onClarify={(critId) => setActiveCriterionClarify(critId)}
                />
              ))}
            </div>
          </div>
        </>
      ) : pipelineError ? (
        /* Explicit Failure State */
        <div className="bg-surface rounded-card border border-danger/30 p-8 text-center shadow-card space-y-4">
          <AlertCircle className="w-10 h-10 text-danger mx-auto" />
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-ink">Evidence Extraction Encountered an Issue</h3>
            <p className="text-xs text-danger font-medium max-w-md mx-auto leading-relaxed">
              {pipelineError}
            </p>
            <p className="text-xs text-muted max-w-md mx-auto">
              You can retry the automated extraction pipeline below without having to re-upload your resume.
            </p>
          </div>
          <Button
            onClick={handleRetryPipeline}
            variant="primary"
            size="sm"
            isLoading={isRetrying}
            leftIcon={<RotateCw className="w-3.5 h-3.5" />}
          >
            Retry Extraction Pipeline
          </Button>
        </div>
      ) : (
        /* Honest In-Progress Evaluation State with Active Polling Indicator */
        <div className="bg-surface rounded-card border border-subtle p-10 text-center shadow-card space-y-4">
          <div className="relative w-12 h-12 mx-auto flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-accent animate-spin" />
          </div>
          <div className="space-y-1.5">
            <h3 className="text-sm font-semibold text-ink">Evidence Extraction In Progress</h3>
            <p className="text-xs text-muted max-w-md mx-auto leading-relaxed">
              Your uploaded document is being analyzed by our AI extraction pipeline and matched against job criteria.
              This typically takes a few seconds. Criteria coverage and citations will appear automatically.
            </p>
          </div>
          {pollCount >= 30 && (
            <div className="pt-2">
              <Button
                onClick={handleRetryPipeline}
                variant="secondary"
                size="sm"
                isLoading={isRetrying}
                leftIcon={<RotateCw className="w-3.5 h-3.5" />}
              >
                Retry or Check Status
              </Button>
            </div>
          )}
        </div>
      )}

      {/* ── Clarification Contest Modal ───────────────────────── */}
      <ClarificationModal
        isOpen={!!activeCriterionClarify}
        onClose={() => setActiveCriterionClarify(null)}
        onSubmit={handleClarificationSubmit}
        criterionName={selectedCriterion?.criterion_name}
      />
    </div>
  );
};
