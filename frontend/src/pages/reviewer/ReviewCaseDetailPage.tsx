import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeft, CheckCircle2, AlertTriangle, ShieldCheck, 
  FileText, ExternalLink, User,
  MessageSquare, Sparkles, Check, AlertOctagon
} from 'lucide-react';
import { mockService } from '../../services/mock/mockService';
import { ReviewCaseDetail } from '../../contracts/models';
import { StatusBadge } from '../../components/ui/Badge';
import { ReviewDecisionType } from '../../contracts/enums';
import { useAuthStore } from '../../stores/authStore';
import { Button, LoadingSpinner } from '../../components/ui';

export const ReviewCaseDetailPage: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [reviewCase, setReviewCase] = useState<ReviewCaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submittedSuccess, setSubmittedSuccess] = useState(false);

  // Form State
  const [decision, setDecision] = useState<ReviewDecisionType>(ReviewDecisionType.ACCEPTED);
  const [rationale, setRationale] = useState('');
  const [notes, setNotes] = useState('');
  const [rationaleError, setRationaleError] = useState('');

  useEffect(() => {
    const fetchCaseData = async () => {
      setLoading(true);
      try {
        const found = await mockService.getReviewCase(caseId || 'flag-001');
        setReviewCase(found);
      } catch (err) {
        console.error('Failed to load review case:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchCaseData();
  }, [caseId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <LoadingSpinner size="lg" label="Loading Decision Studio..." />
      </div>
    );
  }

  if (!reviewCase) {
    return (
      <div className="bg-surface rounded-card border border-subtle p-12 text-center max-w-lg mx-auto mt-12 space-y-4">
        <AlertTriangle className="w-12 h-12 text-warn mx-auto mb-2" />
        <h3 className="text-lg font-semibold text-ink">Review Case Not Located</h3>
        <p className="text-xs text-muted">The requested review case could not be located or has been archived.</p>
        <Button onClick={() => navigate('/reviewer/queue')} variant="secondary" size="sm">
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to Queue
        </Button>
      </div>
    );
  }

  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rationale.trim() || rationale.trim().length < 25) {
      setRationaleError('A detailed rationale of at least 25 characters is strictly required for cryptographic audit logging.');
      return;
    }
    setRationaleError('');
    setSubmitting(true);

    try {
      const fullRationale = notes.trim() 
        ? `${rationale.trim()} [Internal Notes: ${notes.trim()}]`
        : rationale.trim();

      await mockService.recordReviewDecision(reviewCase.flag_id, decision, fullRationale);
      setSubmittedSuccess(true);
      setTimeout(() => {
        navigate('/reviewer/queue');
      }, 1800);
    } catch (err) {
      console.error('Failed to submit decision:', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      {/* ── Top Header & Breadcrumb ───────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface p-6 rounded-card border border-subtle shadow-card">
        <div className="flex items-center gap-4">
          <Link
            to="/reviewer/queue"
            className="p-2.5 rounded-sm bg-elevated border border-subtle text-muted hover:text-ink transition-colors cursor-pointer"
            title="Return to triage queue"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-medium px-2 py-0.5 rounded-pill bg-elevated text-muted border border-subtle">
                FLAG #{reviewCase.flag_id}
              </span>
              <StatusBadge status={reviewCase.flag_status} size="sm" />
              <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-pill uppercase tracking-wider ${
                reviewCase.priority === 'HIGH' ? 'bg-danger-dim text-danger border border-danger/30' : 'bg-warn-dim text-warn border border-warn/30'
              }`}>
                {reviewCase.priority} PRIORITY
              </span>
            </div>
            <h1 className="text-xl font-semibold text-ink flex items-center gap-2">
              Decision Studio: <span className="text-accent font-medium">{reviewCase.criterion_name}</span>
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-xs text-muted font-medium">Assigned Candidate</p>
            <p className="text-sm font-semibold text-ink">{reviewCase.candidate_name}</p>
          </div>
          <div className="w-10 h-10 rounded-pill bg-elevated border border-subtle text-accent flex items-center justify-center font-semibold text-xs">
            {reviewCase.candidate_name.split(' ').map((n: string) => n[0]).join('')}
          </div>
        </div>
      </div>

      {submittedSuccess && (
        <div className="p-4 bg-surface border border-accent/40 rounded-card flex items-center gap-3 text-ink shadow-modal">
          <CheckCircle2 className="w-5 h-5 text-accent shrink-0" />
          <div>
            <h4 className="font-semibold text-sm text-ink">Audit Record Sealed & SHA-256 Hash Committed</h4>
            <p className="text-xs text-muted font-medium">Your determination has been written to the immutable hash ledger. Redirecting...</p>
          </div>
        </div>
      )}

      {/* ── 3-Panel Decision Studio Grid ──────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* PANEL 1 (LEFT): Candidate Context & Rubric (3 Cols) */}
        <div className="lg:col-span-3 space-y-5">
          {/* Candidate Dossier Mini-card */}
          <div className="bg-surface rounded-card border border-subtle p-5 shadow-card space-y-3.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-2">
              <User className="w-3.5 h-3.5 text-accent" /> Candidate Profile
            </h3>
            
            <div className="space-y-2">
              <div>
                <p className="text-[11px] text-muted font-medium">Full Name</p>
                <p className="text-sm font-semibold text-ink">{reviewCase.candidate_name}</p>
              </div>
              <div>
                <p className="text-[11px] text-muted font-medium">Target Requisition</p>
                <p className="text-sm font-medium text-ink">{reviewCase.job_title}</p>
              </div>
              <div>
                <p className="text-[11px] text-muted font-medium">Reference</p>
                <p className="text-xs font-medium text-muted">{reviewCase.application_id}</p>
              </div>
            </div>

            <div className="pt-2 border-t border-subtle">
              <Link 
                to={`/employer/applications/${reviewCase.application_id}`}
                target="_blank"
                className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-elevated hover:bg-elevated/80 text-ink rounded-pill text-xs font-semibold border border-subtle transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" /> Full Dossier
              </Link>
            </div>
          </div>

          {/* Benchmark Rubric */}
          <div className="bg-surface rounded-card border border-subtle p-5 shadow-card space-y-3.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-2">
              <ShieldCheck className="w-3.5 h-3.5 text-accent" /> Benchmark Rubric
            </h3>

            <div className="space-y-3">
              <div>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-pill bg-elevated text-accent border border-accent/20 uppercase">
                  {reviewCase.criterion_category}
                </span>
                <h4 className="text-sm font-semibold text-ink mt-2">{reviewCase.criterion_name}</h4>
                <p className="text-xs text-muted mt-1 leading-relaxed font-medium">{reviewCase.criterion_description}</p>
              </div>

              <div className="p-3 bg-elevated rounded-sm space-y-1.5 border border-subtle text-xs font-medium">
                <div className="flex justify-between">
                  <span className="text-muted">Weight Multiplier:</span>
                  <span className="font-semibold text-ink">{reviewCase.criterion_weight}x</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted">Current State:</span>
                  <StatusBadge status={reviewCase.verification_state} size="sm" />
                </div>
              </div>

              {/* Escalation Reason */}
              <div className="p-3.5 bg-warn-dim rounded-sm border border-warn/30">
                <div className="flex items-center gap-1.5 text-warn text-xs font-semibold mb-1">
                  <AlertOctagon className="w-3.5 h-3.5" /> Escalation Reason
                </div>
                <p className="text-xs text-ink leading-relaxed font-medium">{reviewCase.reason}</p>
              </div>
            </div>
          </div>
        </div>

        {/* PANEL 2 (CENTER): Verbatim Grounded Resume Excerpt (5 Cols) */}
        <div className="lg:col-span-5 space-y-5">
          <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-subtle">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-accent" />
                <h3 className="text-sm font-semibold text-ink">Grounded Evidence Verification</h3>
              </div>
              <span className="text-xs font-medium px-2.5 py-0.5 bg-elevated rounded-pill text-muted border border-subtle">
                Page {reviewCase.source_page || 1} • Verbatim
              </span>
            </div>

            {/* Verbatim Quote Display */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted mb-2">
                Verbatim Resume Citation
              </p>
              {reviewCase.source_excerpt ? (
                <div className="p-4 rounded-sm bg-elevated border border-subtle italic text-xs text-ink leading-relaxed font-normal">
                  "{reviewCase.source_excerpt}"
                </div>
              ) : (
                <div className="p-4 rounded-sm bg-elevated border border-dashed border-subtle text-center text-xs text-muted italic font-medium">
                  No verbatim quote extracted. Flagged as ambiguous or ungrounded claim.
                </div>
              )}
            </div>

            {/* Extracted Claim Text */}
            {reviewCase.claim_text && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted mb-2">
                  Extracted Candidate Claim
                </p>
                <div className="p-3 rounded-sm bg-elevated border border-subtle text-xs text-ink font-medium">
                  {reviewCase.claim_text}
                </div>
              </div>
            )}

            {/* AI Claim Extraction Explanation */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted mb-2 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-accent" /> AI Grounding Assessment
              </p>
              <div className="p-3.5 rounded-sm bg-elevated border border-subtle text-xs text-muted leading-relaxed font-medium">
                {reviewCase.ai_reasoning || 'Automated OCR extracted candidate resume text. Claim lacks explicit duration verification.'}
              </div>
            </div>

            {/* Clarification Thread */}
            {reviewCase.clarifications && reviewCase.clarifications.length > 0 && (
              <div className="p-4 rounded-sm bg-accent-dim border border-accent/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-accent flex items-center gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5" /> Candidate Clarification Statement
                  </span>
                  <span className="text-[10px] font-medium text-accent">Contested Proof</span>
                </div>
                <p className="text-xs text-ink italic bg-surface p-3 rounded-sm border border-subtle leading-relaxed font-medium">
                  "{reviewCase.clarifications[0].candidate_statement}"
                </p>
              </div>
            )}

            {/* Confidence Indicators */}
            <div className="pt-2 grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-sm bg-elevated border border-subtle font-medium">
                <span className="text-muted block mb-1">OCR Parser Confidence</span>
                <span className="font-semibold text-ink text-sm">
                  {Math.round((reviewCase.ai_confidence || 0.72) * 100)}%
                </span>
              </div>
              <div className="p-3 rounded-sm bg-elevated border border-subtle font-medium">
                <span className="text-muted block mb-1">Initial AI Status</span>
                <div className="mt-0.5">
                  <StatusBadge status={reviewCase.ai_status} size="sm" />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* PANEL 3 (RIGHT): Human Review Decision Form (4 Cols) */}
        <div className="lg:col-span-4 space-y-5">
          <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
            <div className="border-b border-subtle pb-3">
              <h3 className="text-base font-semibold text-ink flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-accent" /> Human Determination
              </h3>
              <p className="text-xs text-muted mt-1 font-medium">
                Mandatory human-in-the-loop audit sign-off
              </p>
            </div>

            <form onSubmit={handleDecisionSubmit} className="space-y-4">
              {/* Determination Action */}
              <div>
                <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-2">
                  Determination Verdict
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setDecision(ReviewDecisionType.ACCEPTED)}
                    className={`py-2 px-2.5 rounded-pill text-xs font-semibold border transition-all text-center cursor-pointer ${
                      decision === ReviewDecisionType.ACCEPTED
                        ? 'bg-success-dim text-success border-success/40'
                        : 'bg-elevated text-muted border-subtle hover:text-ink'
                    }`}
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    onClick={() => setDecision(ReviewDecisionType.REJECTED)}
                    className={`py-2 px-2.5 rounded-pill text-xs font-semibold border transition-all text-center cursor-pointer ${
                      decision === ReviewDecisionType.REJECTED
                        ? 'bg-danger-dim text-danger border-danger/40'
                        : 'bg-elevated text-muted border-subtle hover:text-ink'
                    }`}
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    onClick={() => setDecision(ReviewDecisionType.REQUESTED_CLARIFICATION)}
                    className={`py-2 px-2.5 rounded-pill text-xs font-semibold border transition-all text-center cursor-pointer ${
                      decision === ReviewDecisionType.REQUESTED_CLARIFICATION
                        ? 'bg-warn-dim text-warn border-warn/40'
                        : 'bg-elevated text-muted border-subtle hover:text-ink'
                    }`}
                  >
                    Contest
                  </button>
                </div>
              </div>

              {/* Mandatory Rationale */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-semibold text-ink">
                    Auditable Rationale <span className="text-danger">*</span>
                  </label>
                  <span className={`text-[11px] font-medium ${rationale.length >= 25 ? 'text-accent' : 'text-muted'}`}>
                    {rationale.length}/25 min chars
                  </span>
                </div>
                <textarea
                  value={rationale}
                  onChange={(e) => {
                    setRationale(e.target.value);
                    if (rationaleError) setRationaleError('');
                  }}
                  rows={4}
                  placeholder="Detail your exact factual observation, comparison against job requirements, and why the automated check was verified or overridden..."
                  className={`w-full text-xs p-3 rounded-sm border ${
                    rationaleError ? 'border-danger bg-danger-dim' : 'border-subtle bg-elevated'
                  } focus:outline-none focus:border-accent text-ink placeholder:text-muted font-medium`}
                />
                {rationaleError && (
                  <p className="text-xs text-danger mt-1 font-medium">{rationaleError}</p>
                )}
              </div>

              {/* Reviewer Internal Notes */}
              <div>
                <label className="block text-xs font-semibold text-muted mb-1">
                  Internal Review Notes (Optional)
                </label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Consulted hiring manager regarding Kafka scale"
                  className="w-full text-xs p-3 rounded-sm border border-subtle bg-elevated focus:outline-none focus:border-accent text-ink placeholder:text-muted font-medium"
                />
              </div>

              {/* Cryptographic Signature Notice */}
              <div className="p-3.5 bg-elevated rounded-sm border border-subtle text-muted space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-ink">
                  <ShieldCheck className="w-3.5 h-3.5 text-accent" /> Tamper-Proof Audit Event
                </div>
                <p className="text-[11px] leading-relaxed font-medium">
                  Signing as <strong className="text-ink">{user?.full_name} ({user?.role})</strong>. Submitting appends a cryptographic SHA-256 event to the immutable chain.
                </p>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                disabled={submitting || submittedSuccess}
                isLoading={submitting}
                variant="primary"
                size="md"
                className="w-full justify-center font-semibold"
              >
                Finalize Determination
              </Button>
            </form>
          </div>
        </div>

      </div>
    </div>
  );
};
