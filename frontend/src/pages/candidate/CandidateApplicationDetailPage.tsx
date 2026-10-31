import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { applicationService } from '../../services/api/applicationService';
import { evaluationService } from '../../services/api/evaluationService';
import { reviewService } from '../../services/api/reviewService';
import { Application, Evaluation } from '../../contracts/models';
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
} from 'lucide-react';
import { VerificationState } from '../../contracts/enums';
import { Button, LoadingSpinner } from '../../components/ui';

export const CandidateApplicationDetailPage: React.FC = () => {
  const { id, applicationId } = useParams<{ id?: string; applicationId?: string }>();
  const appId = id || applicationId;
  const navigate = useNavigate();

  const [application, setApplication] = useState<Application | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCriterionClarify, setActiveCriterionClarify] = useState<string | null>(null);
  const [showSuccessToast, setShowSuccessToast] = useState(false);

  useEffect(() => {
    if (!appId) {
      setError('No application identifier specified.');
      setLoading(false);
      return;
    }

    const loadApplicationData = async () => {
      setLoading(true);
      setError(null);
      try {
        const app = await applicationService.getApplication(appId);
        setApplication(app);

        // Attempt to fetch evaluation for this application
        try {
          const ev = await evaluationService.getEvaluation(appId);
          setEvaluation(ev);
        } catch {
          // Evaluation may not yet be initiated for newly submitted applications
          setEvaluation(null);
        }
      } catch (err: unknown) {
        const errObj = err as { message?: string };
        setError(errObj.message || 'Application not found or unauthorized.');
      } finally {
        setLoading(false);
      }
    };

    loadApplicationData();
  }, [appId]);

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
      ) : (
        /* Honest In-Progress Evaluation State */
        <div className="bg-surface rounded-card border border-subtle p-10 text-center shadow-card space-y-3">
          <FileText className="w-10 h-10 text-accent mx-auto opacity-70" />
          <h3 className="text-sm font-semibold text-ink">Evidence Extraction In Progress</h3>
          <p className="text-xs text-muted max-w-md mx-auto leading-relaxed">
            Your uploaded document is being parsed for factual claims and quotes. Factual criteria coverage and quotation citations will be displayed here as soon as evaluation completes.
          </p>
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
