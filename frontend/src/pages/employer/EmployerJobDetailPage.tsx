import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
import { Job, Application } from '../../contracts/models';
import { StatusBadge } from '../../components/ui/Badge';
import { ArrowLeft, ChevronRight, Layers } from 'lucide-react';
import { Button } from '../../components/ui';

export const EmployerJobDetailPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<Job | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);

  useEffect(() => {
    if (jobId) {
      Promise.all([
        mockService.getJob(jobId),
        mockService.listApplications(jobId),
      ]).then(([j, apps]) => {
        setJob(j || mockService['jobs'][0]);
        setApplications(apps);
      });
    }
  }, [jobId]);

  if (!job) {
    return (
      <div className="max-w-6xl mx-auto py-12 text-center text-muted font-medium">
        Loading requisition details...
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 select-none">
      {/* ── Back Navigation ───────────────────────────────────── */}
      <div>
        <button
          onClick={() => navigate('/employer/jobs')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to job list
        </button>
      </div>

      {/* ── Requisition Header ────────────────────────────────── */}
      <div className="bg-surface rounded-card p-6 md:p-8 border border-subtle shadow-card flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium px-3 py-0.5 rounded-pill bg-elevated text-muted border border-subtle">
              {job.department}
            </span>
            <StatusBadge status={job.status} />
          </div>
          <h1 className="text-2xl md:text-3xl font-semibold text-ink tracking-tight">{job.title}</h1>
          <p className="text-xs text-muted mt-1.5 font-medium">
            Requisition ID: {job.id} • Created {new Date(job.created_at).toLocaleDateString()}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={() => navigate('/employer/applications')}
            variant="secondary"
            size="sm"
          >
            View Applicants ({applications.length})
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Criteria List (5 cols) */}
        <div className="lg:col-span-5 bg-surface rounded-card p-6 border border-subtle shadow-card space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-subtle">
            <h2 className="text-base font-semibold text-ink tracking-tight">Versioned Criteria</h2>
            <span className="text-xs font-mono text-muted bg-elevated px-2.5 py-0.5 rounded-pill border border-subtle">
              Version 1.0
            </span>
          </div>
          <p className="text-xs text-muted font-medium">
            Applicants are deterministically evaluated against these {job.criteria.length} explicit benchmarks.
          </p>

          <div className="space-y-3 pt-1">
            {job.criteria.map((c, i) => (
              <div key={c.id} className="p-3.5 rounded-sm border border-subtle bg-elevated space-y-1">
                <div className="flex items-center justify-between mb-1">
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

        {/* Right: Applicants for this Requisition (7 cols) */}
        <div className="lg:col-span-7 bg-surface rounded-card p-6 border border-subtle shadow-card space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-subtle">
            <h2 className="text-base font-semibold text-ink tracking-tight">Active Applicants</h2>
            <span className="text-xs font-semibold text-muted">{applications.length} Candidates</span>
          </div>

          <div className="space-y-3 pt-1">
            {applications.map((app) => (
              <div
                key={app.id}
                onClick={() => navigate(`/employer/applications/${app.id}`)}
                className="p-4 rounded-sm border border-subtle bg-elevated hover:bg-elevated/80 transition-all cursor-pointer flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-pill bg-surface border border-subtle text-accent flex items-center justify-center font-semibold text-xs">
                    {app.candidate_name
                      ?.split(' ')
                      .map((n) => n[0])
                      .join('') || 'C'}
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-ink group-hover:text-accent transition-colors">
                      {app.candidate_name}
                    </h4>
                    <span className="text-[11px] text-muted font-mono">{app.candidate_email}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <StatusBadge status={app.status} size="sm" />
                  <ChevronRight className="w-4 h-4 text-muted group-hover:text-accent transition-colors" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
