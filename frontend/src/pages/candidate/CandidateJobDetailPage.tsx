import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { jobService } from '../../services/api/jobService';
import { Job } from '../../contracts/models';
import {
  Layers,
  ArrowLeft,
  UploadCloud,
  X,
  ShieldCheck,
  Sparkles,
  AlertCircle,
  Clock,
} from 'lucide-react';
import { Button } from '../../components/ui';

export const CandidateJobDetailPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isApplyNoticeOpen, setIsApplyNoticeOpen] = useState(false);

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
          onClick={() => setIsApplyNoticeOpen(true)}
          variant="primary"
          size="md"
          rightIcon={<UploadCloud className="w-4 h-4" />}
          className="font-semibold shadow-sm shrink-0"
        >
          Apply with Resume
        </Button>
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

      {/* ── Application Pipeline Integration Modal ─────────────────── */}
      {isApplyNoticeOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-surface rounded-card max-w-md w-full p-6 sm:p-8 shadow-modal border border-subtle relative space-y-5">
            <button
              onClick={() => setIsApplyNoticeOpen(false)}
              className="absolute right-5 top-5 p-1.5 rounded-full text-muted hover:text-ink transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="text-center">
              <div className="w-12 h-12 rounded-card bg-accent-dim text-accent mx-auto flex items-center justify-center border border-accent/30 mb-3">
                <Clock className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-semibold text-ink">Application Pipeline</h3>
              <p className="text-xs text-muted mt-1 font-medium">Feature 3 Integration Milestone</p>
            </div>

            <div className="p-4 rounded-sm bg-elevated border border-subtle text-xs text-ink/90 leading-relaxed font-medium space-y-2">
              <p>
                Resume PDF upload, background document extraction, and grounded AI evidence evaluations are scheduled for integration in the upcoming <strong className="text-accent">Feature 3: Candidate Application & Resume Upload</strong>.
              </p>
              <p className="text-muted text-[11px]">
                Requisition <strong>{job.title}</strong> has <strong>{job.criteria.length} active criteria</strong> configured and ready for evidence mapping.
              </p>
            </div>

            <Button
              variant="primary"
              size="md"
              onClick={() => setIsApplyNoticeOpen(false)}
              className="w-full justify-center font-semibold"
            >
              Close
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
