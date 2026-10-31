import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
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
} from 'lucide-react';
import { VerificationState } from '../../contracts/enums';

export const CandidateApplicationDetailPage: React.FC = () => {
  const { applicationId } = useParams<{ applicationId: string }>();
  const navigate = useNavigate();

  const [application, setApplication] = useState<Application | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [activeCriterionClarify, setActiveCriterionClarify] = useState<string | null>(null);
  const [showSuccessToast, setShowSuccessToast] = useState(false);

  useEffect(() => {
    if (applicationId) {
      Promise.all([
        mockService.getApplication(applicationId),
        mockService.getEvaluation(applicationId),
      ]).then(([app, ev]) => {
        setApplication(app || mockService['applications'][0]);
        setEvaluation(ev);
      });
    }
  }, [applicationId]);

  const handleClarificationSubmit = async (statement: string) => {
    await mockService.submitClarification(statement);

    // Refresh evaluation state locally
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
  };

  if (!application || !evaluation) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-muted font-medium">
        Loading candidate application evidence...
      </div>
    );
  }

  // Active criterion being contested
  const selectedCriterion = evaluation.criteria_evaluations.find(
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
                {application.department}
              </span>
              <StatusBadge status={application.status} />
            </div>
            <h1 className="text-2xl md:text-3xl font-semibold text-ink tracking-tight">
              {application.job_title}
            </h1>
            <p className="text-xs text-muted mt-1.5 flex items-center gap-2 font-medium">
              <Clock className="w-3.5 h-3.5" />
              <span>Submitted on {new Date(application.submitted_at).toLocaleDateString()}</span>
              <span>•</span>
              <span className="font-mono">App #{application.id.slice(0, 8)}</span>
            </p>
          </div>

          <div className="bg-elevated border border-subtle px-4 py-2.5 rounded-card text-right">
            <span className="block text-[10px] font-semibold text-muted uppercase tracking-wider">
              Transparency Status
            </span>
            <span className="text-xs font-semibold text-ink flex items-center gap-1.5 justify-end mt-0.5">
              <ShieldCheck className="w-4 h-4 text-accent" />
              Verbatim Grounding Verified
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
              { label: '2. AI Extraction', active: true, done: true },
              { label: '3. Human Review', active: true, done: false },
              { label: '4. Decision Ready', active: false, done: false },
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

      {/* ── Evidence Coverage Summary Bar ─────────────────────── */}
      <CoverageSummaryBar coverage={evaluation.coverage} />

      {/* ── Criteria Breakdown Section ────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-ink tracking-tight">Criteria Evidence Audit</h2>
            <p className="text-xs text-muted font-medium mt-0.5">
              Each requirement is matched strictly against citations in your resume. Click "Contest with clarification" to submit proof.
            </p>
          </div>
          <span className="text-xs font-mono text-muted bg-elevated border border-subtle px-3 py-1 rounded-pill">
            {evaluation.criteria_evaluations.length} Criteria Evaluated
          </span>
        </div>

        <div className="space-y-4">
          {evaluation.criteria_evaluations.map((item) => (
            <CriterionEvidenceCard
              key={item.criterion_id}
              item={item}
              showClarifyButton={true}
              onClarify={(id) => setActiveCriterionClarify(id)}
            />
          ))}
        </div>
      </div>

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
