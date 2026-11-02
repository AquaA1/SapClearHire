import React, { useState } from 'react';
import {
  MessageSquare,
  HelpCircle,
  Clock,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Send,
  CornerDownRight,
  AlertCircle,
} from 'lucide-react';
import { Button } from '../ui/Button';
import { ExpandableText } from '../ui/ExpandableText';
import { CriterionEvaluationItem } from '../../contracts/models';
import { ReviewDecisionType, VerificationState } from '../../contracts/enums';
import { EmployerClarificationModal } from './EmployerClarificationModal';

interface CriterionClarificationSectionProps {
  item: CriterionEvaluationItem;
  isEmployerOrReviewer?: boolean;
  onCandidateSubmit?: (statement: string) => Promise<void>;
  onReviewDecision?: (
    item: CriterionEvaluationItem,
    decision: ReviewDecisionType,
    rationale: string
  ) => Promise<void>;
}

export const CriterionClarificationSection: React.FC<CriterionClarificationSectionProps> = ({
  item,
  isEmployerOrReviewer = false,
  onCandidateSubmit,
  onReviewDecision,
}) => {
  const [candidateResponse, setCandidateResponse] = useState('');
  const [candidateError, setCandidateError] = useState('');
  const [isSubmittingResponse, setIsSubmittingResponse] = useState(false);

  // Decision Modal State
  const [decisionModalType, setDecisionModalType] = useState<ReviewDecisionType | null>(null);
  const [decisionRationale, setDecisionRationale] = useState('');
  const [decisionError, setDecisionError] = useState('');
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);

  // Further Clarification Modal
  const [showFurtherClarifyModal, setShowFurtherClarifyModal] = useState(false);

  // 1. Gather all clarification-related events chronologically
  const allQuestions = (item.decisions || []).filter(
    (d) => d.decision === ReviewDecisionType.REQUESTED_CLARIFICATION
  );
  const allClarifications = item.clarifications || [];
  const allDecisions = item.decisions || [];

  // Determine if there is any clarification activity
  const hasClarificationActivity =
    allQuestions.length > 0 ||
    allClarifications.length > 0 ||
    item.verification_state === VerificationState.CANDIDATE_CLARIFIED;

  if (!hasClarificationActivity) {
    return null;
  }

  // Combine questions and candidate answers chronologically
  type ThreadEntry =
    | { type: 'question'; id: string; text: string; time: string; reviewerId?: string }
    | { type: 'response'; id: string; text: string; time: string; status: string }
    | { type: 'verdict'; id: string; decision: ReviewDecisionType; text: string; time: string };

  const thread: ThreadEntry[] = [];

  for (const q of allQuestions) {
    thread.push({
      type: 'question',
      id: q.id,
      text: q.mandatory_rationale,
      time: q.created_at,
      reviewerId: q.reviewer_id,
    });
  }

  for (const c of allClarifications) {
    thread.push({
      type: 'response',
      id: c.id,
      text: c.candidate_statement,
      time: c.created_at,
      status: c.status,
    });
  }

  for (const d of allDecisions) {
    if (d.decision !== ReviewDecisionType.REQUESTED_CLARIFICATION) {
      thread.push({
        type: 'verdict',
        id: d.id,
        decision: d.decision,
        text: d.mandatory_rationale,
        time: d.created_at,
      });
    }
  }

  thread.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());

  // Determine the active lifecycle state
  const lastQuestion = [...allQuestions].pop();
  const lastClarification = [...allClarifications].pop();
  const lastFinalDecision = allDecisions
    .filter((d) => d.decision !== ReviewDecisionType.REQUESTED_CLARIFICATION)
    .pop();

  const qTime = lastQuestion ? new Date(lastQuestion.created_at).getTime() : 0;
  const cTime = lastClarification ? new Date(lastClarification.created_at).getTime() : 0;
  const dTime = lastFinalDecision ? new Date(lastFinalDecision.created_at).getTime() : 0;

  let activeState: 'AWAITING_CANDIDATE_RESPONSE' | 'AWAITING_EMPLOYER_REVIEW' | 'DECIDED' =
    'AWAITING_CANDIDATE_RESPONSE';

  if (dTime > qTime && dTime > cTime) {
    activeState = 'DECIDED';
  } else if (cTime > qTime) {
    activeState = 'AWAITING_EMPLOYER_REVIEW';
  } else if (qTime > 0) {
    activeState = 'AWAITING_CANDIDATE_RESPONSE';
  } else if (allClarifications.length > 0) {
    activeState = 'AWAITING_EMPLOYER_REVIEW';
  }

  // Candidate submission handler
  const handleCandidateResponseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = candidateResponse.trim();
    if (!clean) {
      setCandidateError('Please enter a response before submitting.');
      return;
    }
    setCandidateError('');
    setIsSubmittingResponse(true);
    try {
      if (onCandidateSubmit) {
        await onCandidateSubmit(clean);
      }
      setCandidateResponse('');
    } catch (err: any) {
      setCandidateError(err?.message || 'Failed to submit response.');
    } finally {
      setIsSubmittingResponse(false);
    }
  };

  // Employer decision handler
  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!decisionModalType || !onReviewDecision) return;
    const clean = decisionRationale.trim();
    if (clean.length < 25) {
      setDecisionError('A detailed explanatory rationale of at least 25 characters is required.');
      return;
    }
    setDecisionError('');
    setIsSubmittingDecision(true);
    try {
      await onReviewDecision(item, decisionModalType, clean);
      setDecisionModalType(null);
      setDecisionRationale('');
    } catch (err: any) {
      setDecisionError(err?.message || 'Failed to record decision.');
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const handleFurtherClarificationSubmit = async (question: string) => {
    if (!onReviewDecision) return;
    await onReviewDecision(item, ReviewDecisionType.REQUESTED_CLARIFICATION, question);
    setShowFurtherClarifyModal(false);
  };

  return (
    <div className="mt-5 pt-5 border-t border-subtle space-y-4">
      {/* Header and Active Status Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-elevated/70 p-4 rounded-card border border-subtle">
        <div className="flex items-center gap-2.5">
          <MessageSquare className="w-5 h-5 text-accent" />
          <span className="text-sm sm:text-base font-bold text-ink uppercase tracking-wider">
            Clarification Workflow
          </span>
        </div>

        <div>
          {activeState === 'AWAITING_CANDIDATE_RESPONSE' && (
            <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-pill text-xs sm:text-sm font-semibold bg-warn-dim text-warn border border-warn/30">
              <Clock className="w-4 h-4" />
              {isEmployerOrReviewer ? 'Awaiting Candidate Response' : 'Awaiting your response'}
            </span>
          )}

          {activeState === 'AWAITING_EMPLOYER_REVIEW' && (
            <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-pill text-xs sm:text-sm font-semibold bg-accent-dim text-accent border border-accent/30">
              <ShieldCheck className="w-4 h-4" />
              {isEmployerOrReviewer
                ? 'Candidate Responded — Awaiting Employer Review'
                : 'Submitted — Awaiting Employer Review'}
            </span>
          )}

          {activeState === 'DECIDED' && lastFinalDecision?.decision === ReviewDecisionType.ACCEPTED && (
            <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-pill text-xs sm:text-sm font-semibold bg-success-dim text-success border border-success/30">
              <CheckCircle2 className="w-4 h-4" />
              Clarification Accepted — Human Verified
            </span>
          )}

          {activeState === 'DECIDED' && lastFinalDecision?.decision === ReviewDecisionType.REJECTED && (
            <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-pill text-xs sm:text-sm font-semibold bg-danger-dim text-danger border border-danger/30">
              <XCircle className="w-4 h-4" />
              Clarification Rejected — Human Rejected
            </span>
          )}
        </div>
      </div>

      {/* Chronological Conversational Thread */}
      <div className="space-y-4">
        {thread.map((entry, idx) => {
          if (entry.type === 'question') {
            return (
              <div
                key={`q-${entry.id}-${idx}`}
                className="bg-elevated/80 border border-warn/30 rounded-card p-4 sm:p-5 space-y-3 shadow-xs"
              >
                <div className="flex items-center justify-between text-sm sm:text-base font-bold text-warn">
                  <span className="flex items-center gap-2">
                    <HelpCircle className="w-4 h-4 text-warn shrink-0" />
                    Employer Requested Clarification
                  </span>
                  <span className="text-xs sm:text-sm text-muted font-normal flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" />
                    {new Date(entry.time).toLocaleString()}
                  </span>
                </div>
                <div className="pl-4 border-l-2 border-warn/50">
                  <ExpandableText
                    text={entry.text}
                    maxChars={220}
                    quote
                    className="text-base sm:text-[18px] text-ink leading-relaxed font-normal"
                  />
                </div>
              </div>
            );
          }

          if (entry.type === 'response') {
            return (
              <div
                key={`r-${entry.id}-${idx}`}
                className="bg-elevated/90 border border-accent/30 rounded-card p-4 sm:p-5 space-y-3 shadow-xs"
              >
                <div className="flex items-center justify-between text-sm sm:text-base font-bold text-accent">
                  <span className="flex items-center gap-2">
                    <CornerDownRight className="w-4 h-4 text-accent shrink-0" />
                    {isEmployerOrReviewer ? 'Candidate Response' : 'Your Clarification Response'}
                  </span>
                  <span className="text-xs sm:text-sm text-muted font-normal flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" />
                    {new Date(entry.time).toLocaleString()}
                  </span>
                </div>
                <div className="pl-4 border-l-2 border-accent/50">
                  <ExpandableText
                    text={entry.text}
                    maxChars={220}
                    quote
                    className="text-base sm:text-[18px] text-ink leading-relaxed font-normal"
                  />
                </div>
              </div>
            );
          }

          if (entry.type === 'verdict') {
            const isAccepted = entry.decision === ReviewDecisionType.ACCEPTED;
            return (
              <div
                key={`v-${entry.id}-${idx}`}
                className={`border rounded-card p-4 sm:p-5 space-y-3 shadow-xs ${
                  isAccepted
                    ? 'bg-success-dim/20 border-success/30'
                    : 'bg-danger-dim/20 border-danger/30'
                }`}
              >
                <div className="flex items-center justify-between text-sm sm:text-base font-bold">
                  <span
                    className={`flex items-center gap-2 ${
                      isAccepted ? 'text-success' : 'text-danger'
                    }`}
                  >
                    {isAccepted ? (
                      <CheckCircle2 className="w-4 h-4 shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 shrink-0" />
                    )}
                    Reviewer Determination: {isAccepted ? 'Accepted (Verified)' : 'Rejected'}
                  </span>
                  <span className="text-xs sm:text-sm text-muted font-normal flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" />
                    {new Date(entry.time).toLocaleString()}
                  </span>
                </div>
                <div className="pl-4 border-l-2 border-subtle-strong">
                  <ExpandableText
                    text={entry.text}
                    maxChars={220}
                    quote
                    italic
                    className="text-base sm:text-[18px] text-ink leading-relaxed font-normal"
                  />
                </div>
              </div>
            );
          }

          return null;
        })}
      </div>

      {/* Candidate Response Input Form (Visible only to candidate when Awaiting Candidate Response) */}
      {!isEmployerOrReviewer && activeState === 'AWAITING_CANDIDATE_RESPONSE' && onCandidateSubmit && (
        <form
          onSubmit={handleCandidateResponseSubmit}
          className="bg-surface rounded-card p-5 sm:p-6 border border-accent/30 shadow-card space-y-4"
        >
          <div className="flex items-center justify-between flex-wrap gap-2">
            <label className="text-base sm:text-lg font-bold text-ink flex items-center gap-2">
              <CornerDownRight className="w-5 h-5 text-accent" />
              Submit Your Clarification Response
            </label>
            <span className="text-xs sm:text-sm text-muted font-medium">
              Directly address the employer's question
            </span>
          </div>

          <textarea
            rows={4}
            value={candidateResponse}
            onChange={(e) => {
              setCandidateResponse(e.target.value);
              if (candidateError) setCandidateError('');
            }}
            placeholder="e.g. In my Library Inventory API project, I utilized Flask with PostgreSQL. While I did not use FastAPI on that specific project, I have built subsequent internal microservices with FastAPI..."
            className="w-full text-base sm:text-[17px] p-4 rounded-md border border-subtle bg-elevated text-ink placeholder:text-muted focus:outline-none focus:border-accent font-normal leading-relaxed"
            disabled={isSubmittingResponse}
            required
          />

          {candidateError && (
            <p className="text-xs sm:text-sm text-danger font-medium flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {candidateError}
            </p>
          )}

          <div className="flex items-center justify-end">
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isSubmittingResponse}
              disabled={isSubmittingResponse || !candidateResponse.trim()}
              leftIcon={<Send className="w-4 h-4" />}
              className="font-semibold"
            >
              Submit Response
            </Button>
          </div>
        </form>
      )}

      {/* Employer Actions when Candidate has Responded (Awaiting Employer Review) */}
      {isEmployerOrReviewer && activeState === 'AWAITING_EMPLOYER_REVIEW' && onReviewDecision && (
        <div className="p-4 bg-surface rounded-card border border-accent/20 flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm sm:text-base font-semibold text-ink flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-accent" />
            Evaluate Candidate Clarification:
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              type="button"
              onClick={() => {
                setDecisionModalType(ReviewDecisionType.ACCEPTED);
                setDecisionRationale('');
                setDecisionError('');
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-pill text-xs sm:text-sm font-semibold bg-success-dim hover:bg-success/20 text-success border border-success/30 transition-colors cursor-pointer"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Accept Clarification</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setDecisionModalType(ReviewDecisionType.REJECTED);
                setDecisionRationale('');
                setDecisionError('');
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-pill text-xs sm:text-sm font-semibold bg-danger-dim hover:bg-danger/20 text-danger border border-danger/30 transition-colors cursor-pointer"
            >
              <XCircle className="w-4 h-4" />
              <span>Reject Clarification</span>
            </button>

            <button
              type="button"
              onClick={() => setShowFurtherClarifyModal(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-pill text-xs sm:text-sm font-semibold bg-warn-dim hover:bg-warn/20 text-warn border border-warn/30 transition-colors cursor-pointer"
            >
              <HelpCircle className="w-4 h-4" />
              <span>Request Further Clarification</span>
            </button>
          </div>
        </div>
      )}

      {/* Employer Decision Rationale Modal */}
      {decisionModalType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-surface border border-subtle rounded-card shadow-modal max-w-xl w-full p-6 sm:p-7 space-y-5">
            <div className="border-b border-subtle pb-3">
              <h3 className="text-base sm:text-lg font-bold text-ink flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-accent" />
                Sign Clarification Determination:{' '}
                <span className="capitalize">{decisionModalType}</span>
              </h3>
              <p className="text-sm text-muted mt-1 font-medium">
                Criterion: <span className="text-ink font-semibold">{item.criterion_name}</span>
              </p>
            </div>

            <form onSubmit={handleDecisionSubmit} className="space-y-4">
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-sm sm:text-base font-semibold text-ink">
                    Mandatory Auditable Rationale <span className="text-danger">*</span>
                  </label>
                  <span
                    className={`text-xs font-medium ${
                      decisionRationale.trim().length >= 25 ? 'text-accent' : 'text-muted'
                    }`}
                  >
                    {decisionRationale.trim().length}/25 min characters
                  </span>
                </div>
                <textarea
                  value={decisionRationale}
                  onChange={(e) => {
                    setDecisionRationale(e.target.value);
                    if (decisionError) setDecisionError('');
                  }}
                  rows={4}
                  placeholder={`State your factual observation on why the candidate's clarification is ${decisionModalType} and how it aligns with requirement standards...`}
                  className={`w-full text-sm sm:text-base p-3.5 rounded-md border ${
                    decisionError
                      ? 'border-danger bg-danger-dim/30'
                      : 'border-subtle bg-elevated'
                  } text-ink placeholder:text-muted focus:outline-none focus:border-accent font-medium leading-relaxed`}
                  required
                />
                {decisionError && (
                  <p className="text-xs sm:text-sm text-danger mt-1.5 font-medium">{decisionError}</p>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-subtle">
                <Button
                  type="button"
                  variant="secondary"
                  size="md"
                  onClick={() => setDecisionModalType(null)}
                  disabled={isSubmittingDecision}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  isLoading={isSubmittingDecision}
                  disabled={isSubmittingDecision || decisionRationale.trim().length < 25}
                  leftIcon={<ShieldCheck className="w-4 h-4" />}
                  className="font-semibold"
                >
                  Commit Determination
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Further Clarification Modal */}
      {showFurtherClarifyModal && (
        <EmployerClarificationModal
          isOpen={showFurtherClarifyModal}
          onClose={() => setShowFurtherClarifyModal(false)}
          onSubmit={handleFurtherClarificationSubmit}
          item={item}
          isFurtherClarification={true}
        />
      )}
    </div>
  );
};
