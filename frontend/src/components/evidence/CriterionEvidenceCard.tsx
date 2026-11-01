import React, { useState } from 'react';
import { CriterionEvaluationItem } from '../../contracts/models';
import { StatusBadge } from '../ui/Badge';
import {
  FileText,
  MessageSquareQuote,
  HelpCircle,
  ArrowUpRight,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  HelpCircle as HelpIcon,
} from 'lucide-react';
import { EvidenceStatus, ReviewDecisionType, VerificationState } from '../../contracts/enums';
import { Button } from '../ui/Button';

interface CriterionEvidenceCardProps {
  item: CriterionEvaluationItem;
  onClarify?: (criterionId: string) => void;
  showClarifyButton?: boolean;
  isReviewerOrEmployer?: boolean;
  onReviewDecision?: (
    item: CriterionEvaluationItem,
    decision: ReviewDecisionType,
    rationale: string
  ) => Promise<void>;
}

export const CriterionEvidenceCard: React.FC<CriterionEvidenceCardProps> = ({
  item,
  onClarify,
  showClarifyButton = false,
  isReviewerOrEmployer = false,
  onReviewDecision,
}) => {
  const [showDecisionModal, setShowDecisionModal] = useState(false);
  const [selectedDecision, setSelectedDecision] = useState<ReviewDecisionType>(
    ReviewDecisionType.ACCEPTED
  );
  const [rationale, setRationale] = useState('');
  const [rationaleError, setRationaleError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isAmbiguousOrMissing =
    item.status === EvidenceStatus.AMBIGUOUS || item.status === EvidenceStatus.NOT_FOUND;

  const canClarify =
    (isAmbiguousOrMissing ||
      item.verification_state === VerificationState.HUMAN_REJECTED ||
      item.human_decision === 'rejected') &&
    item.verification_state !== VerificationState.CANDIDATE_CLARIFIED;

  // Determine display status based on verification state and AI evidence status
  const getBadgeStatus = (): string => {
    const vState = item.verification_state ? String(item.verification_state).toLowerCase() : '';
    if (vState === 'human_verified' || item.human_decision === 'accepted') {
      return 'human_verified';
    }
    if (vState === 'human_rejected' || item.human_decision === 'rejected') {
      return 'human_rejected';
    }
    if (vState === 'candidate_clarified' || item.human_decision === 'requested_clarification') {
      return 'candidate_clarified';
    }
    if (item.status === EvidenceStatus.SUPPORTED) {
      return 'evidence_supported';
    }
    if (
      item.status === EvidenceStatus.PARTIALLY_SUPPORTED ||
      item.status === ('partially_supported' as any)
    ) {
      return 'partially_supported';
    }
    if (item.status === EvidenceStatus.AMBIGUOUS) {
      return 'ambiguous';
    }
    if (item.status === EvidenceStatus.NOT_FOUND) {
      return 'not_found';
    }
    return item.status || 'unverified';
  };

  const handleOpenDecision = (dec: ReviewDecisionType) => {
    setSelectedDecision(dec);
    setRationale('');
    setRationaleError('');
    setShowDecisionModal(true);
  };

  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = rationale.trim();
    if (clean.length < 25) {
      setRationaleError(
        'A detailed explanatory rationale of at least 25 characters is required for auditable records.'
      );
      return;
    }
    setRationaleError('');
    if (!onReviewDecision) return;

    setIsSubmitting(true);
    try {
      await onReviewDecision(item, selectedDecision, clean);
      setShowDecisionModal(false);
      setRationale('');
    } catch (err: any) {
      setRationaleError(err?.message || 'Failed to record review determination.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const badgeStatus = getBadgeStatus();
  const isHumanDecided =
    item.verification_state === VerificationState.HUMAN_VERIFIED ||
    item.verification_state === VerificationState.HUMAN_REJECTED ||
    !!item.human_decision;

  return (
    <div className="bg-surface rounded-card p-5 border border-subtle shadow-card hover:border-subtle-strong transition-all space-y-3">
      {/* Top Header: Criterion Name, Category, Status */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span
              className={`text-[10px] font-medium px-2 py-0.5 rounded-sm uppercase tracking-wider ${
                item.category === 'required'
                  ? 'bg-accent-dim text-accent border border-accent/20'
                  : 'bg-elevated text-muted border border-subtle'
              }`}
            >
              {item.category}
            </span>
            <h4 className="text-sm font-semibold text-ink tracking-tight">{item.criterion_name}</h4>
          </div>
          <p className="text-xs text-muted leading-relaxed">{item.plain_language_explanation}</p>
        </div>

        <div className="shrink-0 flex items-center gap-2">
          <StatusBadge status={badgeStatus} />
        </div>
      </div>

      {/* Source Excerpt / Grounding Box */}
      {item.source_excerpt ? (
        <div className="bg-elevated border border-subtle rounded-sm p-3.5 text-xs relative group">
          <div className="flex items-center justify-between mb-1.5 text-[11px] font-medium text-muted">
            <span className="flex items-center gap-1.5 text-ink font-medium">
              <MessageSquareQuote className="w-3.5 h-3.5 text-accent" />
              Primary Grounded Evidence
            </span>
            {item.source_page && (
              <span className="flex items-center gap-1 px-2 py-0.5 bg-surface border border-subtle rounded text-[10px] text-muted font-medium">
                <FileText className="w-3 h-3 text-muted" />
                Page {item.source_page}
              </span>
            )}
          </div>
          <p className="text-ink italic text-xs leading-relaxed font-mono">
            "{item.source_excerpt}"
          </p>
        </div>
      ) : (
        <div className="bg-elevated/50 border border-dashed border-subtle rounded-sm p-3 text-xs text-muted italic">
          No explicit matching citation found in resume text.
        </div>
      )}

      {/* Subcriteria Decomposed Breakdown */}
      {item.subcriteria && item.subcriteria.length > 0 && (
        <div className="pt-2 border-t border-subtle space-y-2">
          <div className="flex items-center justify-between text-[11px] font-semibold text-muted">
            <span>Decomposed Sub-requirements ({item.subcriteria.length})</span>
            {item.missing_requirements && item.missing_requirements.length > 0 && (
              <span className="text-[10px] text-danger font-medium">
                {item.missing_requirements.length} missing from evidence
              </span>
            )}
          </div>

          <div className="space-y-2">
            {item.subcriteria.map((sub) => {
              const subStatus = String(sub.status).toLowerCase();
              return (
                <div
                  key={sub.id}
                  className="bg-elevated/70 border border-subtle rounded p-2.5 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-ink flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
                      {sub.name}
                    </span>
                    <StatusBadge status={subStatus} size="sm" />
                  </div>

                  {sub.source_excerpt && (
                    <div className="text-[11px] font-mono text-ink/80 italic pl-3 border-l-2 border-accent/40 bg-surface/40 p-1.5 rounded-r">
                      "{sub.source_excerpt}"
                      {sub.source_page && (
                        <span className="ml-2 not-italic text-[10px] text-muted font-sans font-medium px-1.5 py-0.5 bg-elevated border border-subtle rounded">
                          Page {sub.source_page}
                        </span>
                      )}
                    </div>
                  )}

                  {sub.missing_reason && subStatus === 'not_found' && (
                    <p className="text-[11px] text-muted leading-tight pl-3 border-l-2 border-danger/40">
                      {sub.missing_reason}
                    </p>
                  )}

                  {sub.explanation && subStatus !== 'not_found' && !sub.source_excerpt && (
                    <p className="text-[11px] text-muted leading-tight pl-3 border-l-2 border-subtle">
                      {sub.explanation}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Audited Reviewer Determination & Public Rationale */}
      {item.decision_rationale && (
        <div
          className={`p-3.5 rounded-sm border text-xs leading-relaxed space-y-1 ${
            badgeStatus === 'human_verified'
              ? 'bg-success-dim/30 border-success/30 text-ink'
              : badgeStatus === 'human_rejected'
              ? 'bg-danger-dim/30 border-danger/30 text-ink'
              : 'bg-elevated border-subtle text-ink'
          }`}
        >
          <div className="flex items-center justify-between text-[11px] font-semibold">
            <span className="flex items-center gap-1.5 text-ink">
              <ShieldCheck className="w-3.5 h-3.5 text-accent" />
              Audited Human Reviewer Verdict
            </span>
            {item.decided_at && (
              <span className="text-[10px] text-muted font-normal">
                {new Date(item.decided_at).toLocaleString()}
              </span>
            )}
          </div>
          <p className="italic font-medium text-ink/90">"{item.decision_rationale}"</p>
        </div>
      )}

      {/* Employer / Reviewer Adjudication Actions */}
      {isReviewerOrEmployer && onReviewDecision && (
        <div className="pt-2 border-t border-subtle flex flex-wrap items-center justify-between gap-2">
          <div className="text-[11px] text-muted font-medium flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-accent" />
            <span>Reviewer Adjudication:</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleOpenDecision(ReviewDecisionType.ACCEPTED)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-success-dim hover:bg-success/20 text-success border border-success/30 transition-colors cursor-pointer"
            >
              <CheckCircle2 className="w-3 h-3" />
              <span>{isHumanDecided && badgeStatus === 'human_verified' ? 'Verified' : 'Accept (Verify)'}</span>
            </button>

            <button
              type="button"
              onClick={() => handleOpenDecision(ReviewDecisionType.REJECTED)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-danger-dim hover:bg-danger/20 text-danger border border-danger/30 transition-colors cursor-pointer"
            >
              <XCircle className="w-3 h-3" />
              <span>{isHumanDecided && badgeStatus === 'human_rejected' ? 'Rejected' : 'Reject'}</span>
            </button>

            <button
              type="button"
              onClick={() => handleOpenDecision(ReviewDecisionType.REQUESTED_CLARIFICATION)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-warn-dim hover:bg-warn/20 text-warn border border-warn/30 transition-colors cursor-pointer"
            >
              <HelpIcon className="w-3 h-3" />
              <span>Request Clarification</span>
            </button>
          </div>
        </div>
      )}

      {/* Candidate Clarification Trigger Button */}
      {showClarifyButton && canClarify && onClarify && (
        <div className="pt-2 border-t border-subtle flex items-center justify-between">
          <span className="text-[11px] text-warn flex items-center gap-1">
            <HelpCircle className="w-3.5 h-3.5" />
            Think this is incorrect?
          </span>
          <button
            onClick={() => onClarify(item.criterion_evidence_id || item.criterion_id)}
            className="inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline cursor-pointer"
          >
            <span>Contest with clarification</span>
            <ArrowUpRight className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Decision Rationale Modal */}
      {showDecisionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-surface border border-subtle rounded-card shadow-modal max-w-lg w-full p-6 space-y-4">
            <div className="border-b border-subtle pb-3">
              <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-accent" />
                Sign Review Determination: {item.criterion_name}
              </h3>
              <p className="text-xs text-muted mt-0.5 font-medium">
                Cryptographic audit trail entry with mandatory rationale.
              </p>
            </div>

            <form onSubmit={handleDecisionSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">
                  Action
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedDecision(ReviewDecisionType.ACCEPTED)}
                    className={`py-1.5 px-2 rounded text-xs font-semibold border transition-all text-center cursor-pointer ${
                      selectedDecision === ReviewDecisionType.ACCEPTED
                        ? 'bg-success-dim text-success border-success/40'
                        : 'bg-elevated text-muted border-subtle hover:text-ink'
                    }`}
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedDecision(ReviewDecisionType.REJECTED)}
                    className={`py-1.5 px-2 rounded text-xs font-semibold border transition-all text-center cursor-pointer ${
                      selectedDecision === ReviewDecisionType.REJECTED
                        ? 'bg-danger-dim text-danger border-danger/40'
                        : 'bg-elevated text-muted border-subtle hover:text-ink'
                    }`}
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedDecision(ReviewDecisionType.REQUESTED_CLARIFICATION)}
                    className={`py-1.5 px-2 rounded text-xs font-semibold border transition-all text-center cursor-pointer ${
                      selectedDecision === ReviewDecisionType.REQUESTED_CLARIFICATION
                        ? 'bg-warn-dim text-warn border-warn/40'
                        : 'bg-elevated text-muted border-subtle hover:text-ink'
                    }`}
                  >
                    Clarify
                  </button>
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-semibold text-ink">
                    Mandatory Auditable Rationale <span className="text-danger">*</span>
                  </label>
                  <span
                    className={`text-[10px] font-medium ${
                      rationale.trim().length >= 25 ? 'text-accent' : 'text-muted'
                    }`}
                  >
                    {rationale.trim().length}/25 min characters
                  </span>
                </div>
                <textarea
                  value={rationale}
                  onChange={(e) => {
                    setRationale(e.target.value);
                    if (rationaleError) setRationaleError('');
                  }}
                  rows={4}
                  placeholder="State your factual observation, why this claim is accepted or rejected, and how it aligns with the requisition requirements..."
                  className={`w-full text-xs p-3 rounded-sm border ${
                    rationaleError ? 'border-danger bg-danger-dim/30' : 'border-subtle bg-elevated'
                  } text-ink placeholder:text-muted focus:outline-none focus:border-accent font-medium leading-relaxed`}
                />
                {rationaleError && (
                  <p className="text-xs text-danger mt-1 font-medium">{rationaleError}</p>
                )}
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-subtle">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowDecisionModal(false)}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  isLoading={isSubmitting}
                  disabled={isSubmitting || rationale.trim().length < 25}
                  leftIcon={<ShieldCheck className="w-3.5 h-3.5" />}
                  className="font-semibold"
                >
                  Commit Determination
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
