import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
import { Job } from '../../contracts/models';
import {
  Briefcase,
  Layers,
  ArrowLeft,
  UploadCloud,
  CheckCircle2,
  FileText,
  X,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { Button } from '../../components/ui';

export const CandidateJobDetailPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<Job | null>(null);
  const [isApplyModalOpen, setIsApplyModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStep, setUploadStep] = useState<'idle' | 'uploading' | 'extracting' | 'complete'>('idle');
  const [progressText, setProgressText] = useState('');

  useEffect(() => {
    if (jobId) {
      mockService.getJob(jobId).then((j) => setJob(j || mockService['jobs'][0]));
    }
  }, [jobId]);

  if (!job) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-muted font-medium">
        Loading requisition details...
      </div>
    );
  }

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleApplySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadStep('uploading');
    setProgressText('Uploading PDF resume & verifying structure...');

    setTimeout(() => {
      setUploadStep('extracting');
      setProgressText('Extracting grounded claims & parsing criteria matches...');

      setTimeout(async () => {
        const app = await mockService.submitApplication(job.id, selectedFile?.name || 'resume.pdf');
        setUploadStep('complete');
        setProgressText('Application registered successfully!');

        setTimeout(() => {
          navigate(`/candidate/applications/${app.id}`);
        }, 800);
      }, 1100);
    }, 900);
  };

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
              {job.department}
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
          onClick={() => setIsApplyModalOpen(true)}
          variant="primary"
          size="md"
          rightIcon={<UploadCloud className="w-4 h-4" />}
          className="font-semibold shadow-sm"
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
              {job.description}
            </p>
          </div>

          <div className="pt-4 border-t border-subtle">
            <h3 className="text-sm font-semibold text-ink mb-3">ClearHire Transparency Guarantee</h3>
            <div className="bg-accent-dim border border-accent/30 rounded-card p-5 text-xs text-ink space-y-3">
              <div className="flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                <span>
                  <strong className="text-ink font-semibold">No silent rejections:</strong> Every criterion listed on this page is evaluated strictly against citations in your resume.
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
            <span className="text-[11px] font-mono text-muted bg-elevated px-2.5 py-1 rounded-pill border border-subtle">
              v1.0 Immutable
            </span>
          </div>
          <p className="text-xs text-muted font-medium">
            Your uploaded resume will be matched directly against these explicit benchmarks:
          </p>

          <div className="space-y-3">
            {job.criteria.map((c, i) => (
              <div key={c.id} className="p-3.5 rounded-sm border border-subtle bg-elevated space-y-1">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[10px] font-mono text-muted">#0{i + 1}</span>
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
            ))}
          </div>
        </div>
      </div>

      {/* ── Apply Modal (Token Styled) ────────────────────────── */}
      {isApplyModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-surface rounded-card max-w-lg w-full p-6 sm:p-8 shadow-modal border border-subtle relative">
            <button
              onClick={() => {
                if (uploadStep === 'idle') setIsApplyModalOpen(false);
              }}
              disabled={uploadStep !== 'idle'}
              className="absolute right-5 top-5 p-1.5 rounded-full text-muted hover:text-ink transition-colors disabled:opacity-30 cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="text-center mb-6">
              <div className="w-12 h-12 rounded-card bg-accent-dim text-accent mx-auto flex items-center justify-center border border-accent/30 mb-3">
                <UploadCloud className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-semibold text-ink">Submit Application</h3>
              <p className="text-xs text-muted mt-1 font-medium">Applying for: {job.title}</p>
            </div>

            {uploadStep !== 'idle' ? (
              <div className="py-8 text-center space-y-4">
                <div className="w-10 h-10 border-2 border-subtle border-t-accent rounded-full animate-spin mx-auto" />
                <div>
                  <h4 className="text-sm font-semibold text-ink">{progressText}</h4>
                  <span className="text-xs text-muted mt-1 block font-medium">
                    {uploadStep === 'uploading'
                      ? 'Step 1 of 3: PDF Processing'
                      : uploadStep === 'extracting'
                      ? 'Step 2 of 3: AI Evidence Grounding'
                      : 'Step 3 of 3: Complete'}
                  </span>
                </div>
              </div>
            ) : (
              <form onSubmit={handleApplySubmit} className="space-y-4">
                {/* Dropzone */}
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleFileDrop}
                  className="border-2 border-dashed border-subtle rounded-sm p-6 text-center hover:border-subtle-strong bg-elevated/40 transition-all cursor-pointer relative"
                >
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setSelectedFile(e.target.files[0]);
                      }
                    }}
                    className="absolute inset-0 opacity-0 cursor-pointer"
                  />
                  {selectedFile ? (
                    <div className="flex items-center justify-center gap-2 text-ink font-semibold text-xs">
                      <FileText className="w-5 h-5 text-accent" />
                      <span>{selectedFile.name}</span>
                    </div>
                  ) : (
                    <div>
                      <UploadCloud className="w-8 h-8 text-muted mx-auto mb-2" />
                      <span className="block text-xs font-semibold text-ink">
                        Click or drag & drop your resume PDF
                      </span>
                      <span className="block text-[11px] text-muted mt-1">
                        Only PDF format supported (Max. 10MB)
                      </span>
                    </div>
                  )}
                </div>

                <div className="text-[11px] text-muted leading-relaxed bg-elevated p-3 rounded-sm border border-subtle font-medium">
                  By applying, ClearHire will extract verifiable claims and map them directly to this requisition's {job.criteria.length} versioned criteria.
                </div>

                <Button
                  type="submit"
                  disabled={!selectedFile}
                  variant="primary"
                  size="md"
                  className="w-full justify-center font-semibold"
                >
                  Submit & Run Evidence Extraction
                </Button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
