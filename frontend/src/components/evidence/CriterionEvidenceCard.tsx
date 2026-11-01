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
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  HelpCircle as HelpIcon,
} from 'lucide-react';
import { EvidenceStatus, ReviewDecisionType, VerificationState } from '../../contracts/enums';
import { Button } from '../ui/Button';
import { CriterionClarificationSection } from './CriterionClarificationSection';
import { EmployerClarificationModal } from './EmployerClarificationModal';

interface CriterionEvidenceCardProps {
  item: CriterionEvaluationItem;
  onClarify?: (criterionId: string) => void;
  showClarifyButton?: boolean;
  isReviewerOrEmployer?: boolean;
  onCandidateSubmit?: (statement: string) => Promise<void>;
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
  onCandidateSubmit,
  onReviewDecision,
}) => {
  const [showDecisionModal, setShowDecisionModal] = useState(false);
  const [showEmployerClarifyModal, setShowEmployerClarifyModal] = useState(false);
  const [selectedDecision, setSelectedDecision] = useState<ReviewDecisionType>(
    ReviewDecisionType.ACCEPTED
  );
  const [rationale, setRationale] = useState('');
  const [rationaleError, setRationaleError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isExcerptExpanded, setIsExcerptExpanded] = useState(false);

  const isAmbiguousOrMissing =
    item.status === EvidenceStatus.AMBIGUOUS || item.status === EvidenceStatus.NOT_FOUND;

  const hasActiveClarificationRequest =
    (item.human_decision === 'requested_clarification' ||
      item.decisions?.some((d) => d.decision === ReviewDecisionType.REQUESTED_CLARIFICATION)) &&
    item.verification_state !== VerificationState.CANDIDATE_CLARIFIED &&
    item.verification_state !== VerificationState.HUMAN_VERIFIED &&
    item.verification_state !== VerificationState.HUMAN_REJECTED;

  const canClarify =
    (isAmbiguousOrMissing ||
      item.verification_state === VerificationState.HUMAN_REJECTED ||
      item.human_decision === 'rejected') &&
    item.verification_state !== VerificationState.CANDIDATE_CLARIFIED &&
    !hasActiveClarificationRequest;

  // Determine display status based on verification state and AI evidence status
  const getBadgeStatus = (): string => {
    const vState = item.verification_state ? String(item.verification_state).toLowerCase() : '';
    if (vState === 'human_verified' || item.human_decision === 'accepted') {
      return 'human_verified';
    }
    if (vState === 'human_rejected' || item.human_decision === 'rejected') {
      return 'human_rejected';
    }
    if (vState === 'candidate_clarified') {
      return 'candidate_clarified';
    }
    if (item.human_decision === 'requested_clarification' || hasActiveClarificationRequest) {
      return 'awaiting_candidate_response';
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

  const handleEmployerClarifySubmit = async (question: string) => {
    if (!onReviewDecision) return;
    await onReviewDecision(item, ReviewDecisionType.REQUESTED_CLARIFICATION, question);
    setShowEmployerClarifyModal(false);
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

  const isLongExcerpt = (item.source_excerpt || '').length > 220;

  return (
    <div className="bg-surface rounded-card p-6 sm:p-7 border border-subtle shadow-card hover:border-subtle-strong transition-all space-y-6">
      {/* Top Header: Criterion Name, Category, Status */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span
              className={`text-xs font-semibold px-2.5 py-0.5 rounded uppercase tracking-wider ${
                item.category === 'required'
                  ? 'bg-accent-dim text-accent border border-accent/25'
                  : 'bg-elevated text-muted border border-subtle'
              }`}
            >
              {item.category}
            </span>
            <h4 className="text-lg sm:text-[20px] font-semibold text-ink tracking-tight leading-[1.3]">
              {item.criterion_name}
            </h4>
          </div>
          <p className="text-[15px] text-ink-secondary leading-[1.6]">
            {item.plain_language_explanation}
          </p>
        </div>

        <div className="shrink-0 flex items-center gap-2 self-start">
          <StatusBadge status={badgeStatus} size="md" />
        </div>
      </div>

      {/* Source Excerpt / Grounding Box */}
      {item.source_excerpt ? (
        <div className="bg-elevated/80 border border-subtle rounded-card p-5 sm:p-6 text-[15px] relative group space-y-3">
          <div className="flex items-center justify-between text-xs sm:text-[13px] font-semibold text-muted">
            <span className="flex items-center gap-2 text-ink">
              <MessageSquareQuote className="w-4 h-4 text-accent shrink-0" />
              Primary Grounded Evidence
            </span>
            {item.source_page && (
              <span className="flex items-center gap-1.5 px-3 py-1 bg-surface border border-subtle rounded-pill text-xs text-muted font-medium">
                <FileText className="w-3.5 h-3.5 text-muted shrink-0" />
                Page {item.source_page}
              </span>
            )}
          </div>
          <p className="text-ink italic text-[15px] leading-[1.7] font-normal whitespace-pre-wrap">
            "{!isExcerptExpanded && isLongExcerpt
              ? `${item.source_excerpt.slice(0, 210).trim()}...`
              : item.source_excerpt}"
          </p>
          {isLongExcerpt && (
            <button
              type="button"
              onClick={() => setIsExcerptExpanded(!isExcerptExpanded)}
              className="inline-flex items-center gap-1.5 text-xs sm:text-[13px] font-semibold text-accent hover:underline cursor-pointer pt-1"
            >
              {isExcerptExpanded ? (
                <>
                  <ChevronUp className="w-3.5 h-3.5" />
                  <span>Show compact preview</span>
                </>
              ) : (
                <>
                  <ChevronDown className="w-3.5 h-3.5" />
                  <span>Show full evidence citation</span>
                </>
              )}
            </button>
          )}
        </div>
      ) : (
        <div className="bg-elevated/40 border border-dashed border-subtle rounded-card p-4 sm:p-5 text-[14px] text-muted italic flex items-center gap-2.5">
          <HelpCircle className="w-4 h-4 text-muted shrink-0" />
          <span>No explicit matching citation found in resume text.</span>
        </div>
      )}

      {/* Subcriteria Decomposed Breakdown */}
      {item.subcriteria && item.subcriteria.length > 0 && (
        <div className="pt-3 border-t border-subtle space-y-3.5">
          <div className="flex items-center justify-between text-xs sm:text-[13px] font-semibold text-muted">
            <span>Decomposed Sub-requirements ({item.subcriteria.length})</span>
            {item.missing_requirements && item.missing_requirements.length > 0 && (
              <span className="text-xs text-danger font-medium flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                {item.missing_requirements.length} missing from evidence
              </span>
            )}
          </div>

          <div className="space-y-3">
            {item.subcriteria.map((sub) => {
              const subStatus = String(sub.status).toLowerCase();
              const isDuplicateOfPrimary = Boolean(
                sub.source_excerpt &&
                  item.source_excerpt &&
                  sub.source_excerpt.trim().toLowerCase() === item.source_excerpt.trim().toLowerCase()
              );

              return (
                <div
                  key={sub.id}
                  className="bg-elevated/70 border border-subtle rounded-card p-4 sm:p-4.5 space-y-3"
                >
                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <span className="text-[15px] font-medium text-ink flex items-center gap-2">
                      {subStatus === 'supported' && (
                        <CheckCircle2 className="w-4 h-4 text-success shrink-0" />
                      )}
                      {subStatus === 'partially_supported' && (
                        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                      )}
                      {subStatus === 'ambiguous' && (
                        <HelpCircle className="w-4 h-4 text-warn shrink-0" />
                      )}
                      {subStatus === 'not_found' && (
                        <XCircle className="w-4 h-4 text-danger shrink-0" />
                      )}
                      {!['supported', 'partially_supported', 'ambiguous', 'not_found'].includes(
                        subStatus
                      )}
                      {sub.name}
                    </span>
                    <StatusBadge status={subStatus} size="sm" />
                  </div>

                  {sub.source_excerpt && isDuplicateOfPrimary && (
                    <div className="flex items-center gap-2 text-[13px] text-muted font-medium bg-surface/50 border border-subtle/60 rounded px-3.5 py-2">
                      <ShieldCheck className="w-4 h-4 text-accent shrink-0" />
                      <span>
                        Grounded by primary citation above
                        {sub.source_page ? ` (Page ${sub.source_page})` : ''}
                      </span>
                    </div>
                  )}

                  {sub.source_excerpt && !isDuplicateOfPrimary && (
                    <div className="text-[14px] text-ink/90 italic pl-3.5 border-l-2 border-accent/40 bg-surface/40 p-2.5 rounded-r leading-[1.65]">
                      "{sub.source_excerpt}"
                      {sub.source_page && (
                        <span className="ml-2.5 not-italic text-[12px] text-muted font-sans font-medium px-2 py-0.5 bg-elevated border border-subtle rounded inline-block">
                          Page {sub.source_page}
                        </span>
                      )}
                    </div>
                  )}

                  {sub.missing_reason && subStatus === 'not_found' && (
                    <p className="text-[13.5px] text-muted leading-[1.6] pl-3.5 border-l-2 border-danger/40">
                      {sub.missing_reason}
                    </p>
                  )}

                  {sub.explanation && subStatus !== 'not_found' && !sub.source_excerpt && (
                    <p className="text-[13.5px] text-muted leading-[1.6] pl-3.5 border-l-2 border-subtle">
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
      {item.decision_rationale &&
        item.human_decision &&
        item.human_decision !== 'requested_clarification' &&
        item.human_decision !== ReviewDecisionType.REQUESTED_CLARIFICATION && (
        <div
          className={`p-5 rounded-card border text-[15px] leading-[1.65] space-y-2.5 ${
            badgeStatus === 'human_verified'
              ? 'bg-success-dim/20 border-success/30 text-ink'
              : badgeStatus === 'human_rejected'
              ? 'bg-danger-dim/20 border-danger/30 text-ink'
              : 'bg-elevated/90 border-subtle text-ink'
          }`}
        >
          <div className="flex items-center justify-between text-xs sm:text-[13px] font-semibold">
            <span className="flex items-center gap-2 text-ink">
              <ShieldCheck className="w-4 h-4 text-accent shrink-0" />
              Audited Human Reviewer Verdict
            </span>
            {item.decided_at && (
              <span className="text-[12px] text-muted font-normal">
                {new Date(item.decided_at).toLocaleString()}
              </span>
            )}
          </div>
          <p className="italic font-normal text-ink pl-4 border-l-2 border-subtle-strong">
            "{item.decision_rationale}"
          </p>
        </div>
      )}

      {/* Employer / Reviewer Adjudication Actions */}
      {isReviewerOrEmployer && onReviewDecision && (
        <div className="pt-3 border-t border-subtle flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs sm:text-[13px] text-muted font-medium flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-accent shrink-0" />
            <span>Reviewer Adjudication:</span>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              type="button"
              onClick={() => handleOpenDecision(ReviewDecisionType.ACCEPTED)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs sm:text-[13px] font-semibold bg-success-dim hover:bg-success/20 text-success border border-success/30 transition-colors cursor-pointer"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{isHumanDecided && badgeStatus === 'human_verified' ? 'Verified' : 'Accept (Verify)'}</span>
            </button>

            <button
              type="button"
              onClick={() => handleOpenDecision(ReviewDecisionType.REJECTED)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs sm:text-[13px] font-semibold bg-danger-dim hover:bg-danger/20 text-danger border border-danger/30 transition-colors cursor-pointer"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>{isHumanDecided && badgeStatus === 'human_rejected' ? 'Rejected' : 'Reject'}</span>
            </button>

            <button
              type="button"
              disabled={hasActiveClarificationRequest}
              onClick={() => setShowEmployerClarifyModal(true)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs sm:text-[13px] font-semibold border transition-colors ${
                hasActiveClarificationRequest
                  ? 'bg-elevated text-muted border-subtle cursor-not-allowed opacity-60'
                  : 'bg-warn-dim hover:bg-warn/20 text-warn border border-warn/30 cursor-pointer'
              }`}
            >
              <HelpIcon className="w-3.5 h-3.5" />
              <span>{hasActiveClarificationRequest ? 'Awaiting Response' : 'Request Clarification'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Candidate Clarification Trigger Button */}
      {showClarifyButton && canClarify && onClarify && (
        <div className="pt-3 border-t border-subtle flex items-center justify-between flex-wrap gap-2">
          <span className="text-xs sm:text-[13px] text-warn flex items-center gap-1.5 font-medium">
            <HelpCircle className="w-4 h-4 text-warn shrink-0" />
            Think this assessment is incorrect?
          </span>
          <button
            onClick={() => onClarify(item.criterion_evidence_id || item.criterion_id)}
            className="inline-flex items-center gap-1.5 text-xs sm:text-[13px] font-semibold text-accent hover:underline cursor-pointer"
          >
            <span>Contest with clarification</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Inline Clarification Conversation Thread */}
      <CriterionClarificationSection
        item={item}
        isEmployerOrReviewer={isReviewerOrEmployer}
        onCandidateSubmit={onCandidateSubmit}
        onReviewDecision={onReviewDecision}
      />

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

      {/* Employer Clarification Request Modal */}
      {showEmployerClarifyModal && (
        <EmployerClarificationModal
          isOpen={showEmployerClarifyModal}
          onClose={() => setShowEmployerClarifyModal(false)}
          onSubmit={handleEmployerClarifySubmit}
          item={item}
        />
      )}
    </div>
  );
};
