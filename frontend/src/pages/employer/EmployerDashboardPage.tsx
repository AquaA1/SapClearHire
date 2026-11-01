import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { jobService } from '../../services/api/jobService';
import { applicationService } from '../../services/api/applicationService';
import { reviewService } from '../../services/api/reviewService';
import { auditService } from '../../services/api/auditService';
import { Job, Application, ReviewFlagSummary, AuditEvent } from '../../contracts/models';
import { StatusBadge } from '../../components/ui/Badge';
import {
  Button,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  LoadingSpinner,
} from '../../components/ui';
import {
  Briefcase,
  Users,
  CheckSquare,
  ArrowRight,
  Plus,
  AlertCircle,
  ShieldCheck,
  ChevronRight,
  FileText,
} from 'lucide-react';

export const EmployerDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [flags, setFlags] = useState<ReviewFlagSummary[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadEmployerData = async () => {
      try {
        const [j, a, e, f] = await Promise.all([
          jobService.listJobs(),
          applicationService.listApplications(),
          auditService.listAuditEvents().catch(() => []),
          reviewService.listReviewFlags({ status: 'all' }).catch(() => []),
        ]);
        setJobs(j);
        setApplications(a);
        setAuditEvents(e.slice(0, 6));
        setFlags(f);
      } catch (err) {
        console.error('Failed to load employer command center:', err);
      } finally {
        setLoading(false);
      }
    };

    loadEmployerData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[450px]">
        <LoadingSpinner size="lg" label="Loading employer command center..." />
      </div>
    );
  }

  // Factual, real database counts
  const activeJobsCount = jobs.filter((j) => j.status === 'active' || !j.status).length;
  const totalAppsCount = applications.length;
  const resolvedReviewsCount = flags.filter((f) => f.status === 'resolved').length;
  const pendingReviewsCount = flags.filter(
    (f) => f.status === 'pending' || f.status === 'under_review'
  ).length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-subtle">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">
            Employer Command Center
          </h1>
          <p className="text-xs text-muted mt-1 font-medium">
            Manage open requisitions, inspect candidate qualification evidence, and triage human reviews.
          </p>
        </div>

        <Button
          onClick={() => navigate('/employer/jobs')}
          variant="primary"
          size="sm"
          leftIcon={<Plus className="w-4 h-4" />}
          className="shrink-0 self-start sm:self-auto cursor-pointer font-semibold shadow-sm"
        >
          Manage Requisitions
        </Button>
      </div>

      {/* ── Bento Grid ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Stats & The One Mint Highlighted Card (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-5">
          {/* Bento Stat Card 1: Split Stat (Total Apps & Active Jobs) */}
          <div className="bg-surface border border-subtle rounded-card p-5 shadow-card">
            <div className="grid grid-cols-2 divide-x divide-subtle">
              <div className="pr-4">
                <span className="text-3xl sm:text-4xl font-semibold text-ink tracking-tight block">
                  {totalAppsCount}
                </span>
                <span className="text-xs text-muted mt-1.5 font-medium block">
                  Total Applicants
                </span>
              </div>
              <div className="pl-4">
                <span className="text-3xl sm:text-4xl font-semibold text-ink tracking-tight block">
                  {activeJobsCount}
                </span>
                <span className="text-xs text-muted mt-1.5 font-medium block">Active Jobs</span>
              </div>
            </div>
          </div>

          {/* Bento Stat Card 2: Resolved Reviews Stat */}
          <div className="bg-surface border border-subtle rounded-card p-5 shadow-card flex items-center justify-between">
            <div>
              <span className="text-3xl sm:text-4xl font-semibold text-ink tracking-tight block">
                {resolvedReviewsCount}
              </span>
              <span className="text-xs text-muted mt-1 font-medium block">
                Resolved Adjudications
              </span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-elevated border border-subtle flex items-center justify-center text-accent">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>

          {/* ── THE ONE MINT HIGHLIGHTED CARD FOR PRIORITY ACTION ── */}
          <div className="bg-accent-dim border border-accent/30 rounded-card p-5 shadow-card flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-accent uppercase tracking-wider flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" />
                Priority Review Triage
              </span>
              <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-pill bg-accent/20 text-accent border border-accent/40">
                {pendingReviewsCount > 0 ? `${pendingReviewsCount} Action Required` : 'Ledger Healthy'}
              </span>
            </div>

            <div>
              <h3 className="text-base font-semibold text-ink leading-snug">
                {pendingReviewsCount > 0
                  ? 'Ambiguous Evidence Requires Human Verdict'
                  : 'All Candidate Evidence Grounded'}
              </h3>
              <p className="text-xs text-ink/90 mt-1.5 leading-relaxed">
                {pendingReviewsCount > 0
                  ? 'Adjudicate missing qualifications with mandatory reviewer justification before final candidate determination.'
                  : 'Candidate claims match verbatim resume excerpts with cryptographic SHA-256 proof.'}
              </p>
            </div>

            <Button
              onClick={() => navigate('/employer/reviews')}
              variant="primary"
              size="sm"
              rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
              className="w-full justify-between font-semibold"
            >
              <span>{pendingReviewsCount > 0 ? 'Triage Review Cases' : 'Inspect Review Triage'}</span>
            </Button>
          </div>
        </div>

        {/* Right Column: Pending Screenings Table & Requisitions (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col gap-5">
          {/* Recent Screenings Table */}
          <div className="bg-surface border border-subtle rounded-card shadow-card overflow-hidden">
            <div className="p-5 border-b border-subtle flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-ink">Recent Candidate Screenings</h2>
                <p className="text-xs text-muted font-medium mt-0.5">
                  Applicants and deterministic evidence verification states
                </p>
              </div>
              {applications.length > 0 && (
                <Link
                  to={`/employer/applications/${applications[0].id}`}
                  className="text-xs font-semibold text-muted hover:text-ink flex items-center gap-1 transition-colors"
                >
                  <span>View Dossiers</span>
                  <ArrowRight className="w-3 h-3" />
                </Link>
              )}
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Candidate</TableHead>
                  <TableHead>Requisition</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {applications.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="py-12 text-center text-muted font-medium">
                      <div className="max-w-xs mx-auto space-y-2">
                        <Users className="w-8 h-8 text-muted mx-auto opacity-40" />
                        <p className="text-xs text-muted">No candidate applications submitted yet.</p>
                        <p className="text-[11px] text-muted">
                          Candidates will appear here as soon as they apply to your open job requisitions.
                        </p>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  applications.slice(0, 5).map((app) => (
                    <TableRow key={app.id}>
                      <TableCell>
                        <div className="font-semibold text-ink text-xs">
                          {app.candidate_name || `Candidate #${app.candidate_id.slice(0, 8)}`}
                        </div>
                        <div className="text-[11px] text-muted font-medium mt-0.5">
                          App #{app.id.slice(0, 8)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs font-medium text-ink/90 truncate block max-w-[220px]">
                          {app.job_title}
                        </span>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={app.status} size="sm" />
                      </TableCell>
                      <TableCell className="text-right">
                        <Link
                          to={`/employer/applications/${app.id}`}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline transition-colors"
                        >
                          <span>Inspect</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Lower Bento Grid: Open Requisitions (6 cols) & Quick Actions (6 cols) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Open Requisitions Roster */}
            <div className="bg-surface border border-subtle rounded-card p-5 shadow-card space-y-3.5">
              <div className="flex items-center justify-between pb-2 border-b border-subtle">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
                    Open Requisitions
                  </h3>
                  <p className="text-xs text-muted font-medium">Active job specifications</p>
                </div>
                <Link to="/employer/jobs" className="text-xs font-semibold text-muted hover:text-ink">
                  All ({jobs.length})
                </Link>
              </div>

              <div className="space-y-2.5">
                {jobs.length === 0 ? (
                  <div className="p-6 rounded-sm bg-elevated/40 border border-subtle text-center text-muted space-y-2">
                    <Briefcase className="w-6 h-6 text-muted mx-auto opacity-50" />
                    <p className="text-xs font-medium text-ink">No Requisitions Created</p>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => navigate('/employer/jobs')}
                      className="text-xs mt-1"
                    >
                      Create First Requisition
                    </Button>
                  </div>
                ) : (
                  jobs.slice(0, 3).map((job) => (
                    <div
                      key={job.id}
                      onClick={() => navigate('/employer/jobs')}
                      className="p-3.5 rounded-sm bg-elevated hover:bg-elevated/80 border border-subtle cursor-pointer transition-colors space-y-1.5"
                    >
                      <div className="flex items-start justify-between">
                        <h4 className="text-xs font-semibold text-ink leading-tight">{job.title}</h4>
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded-pill bg-success-dim text-success border border-success/30">
                          Active
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-muted font-medium">
                        <span>{job.department || 'General'}</span>
                        <span className="text-ink">{job.criteria?.length || 0} Criteria Defined</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* QuickActions Widget */}
            <div className="bg-surface border border-subtle rounded-card p-5 shadow-card space-y-3.5">
              <div className="pb-2 border-b border-subtle">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Quick Actions
                </h3>
                <p className="text-xs text-muted font-medium">Direct command shortcuts</p>
              </div>

              <div className="space-y-2">
                <button
                  onClick={() => navigate('/employer/jobs')}
                  className="w-full p-3 rounded-sm bg-elevated hover:bg-elevated/80 border border-subtle text-left transition-colors flex items-center justify-between cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <Plus className="w-4 h-4 text-accent shrink-0" />
                    <div>
                      <span className="text-xs font-semibold text-ink block">
                        Create New Requisition
                      </span>
                      <span className="text-[11px] text-muted font-medium">
                        Define criteria weights & benchmarks
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted group-hover:text-ink transition-colors" />
                </button>

                <button
                  onClick={() => navigate('/employer/reviews')}
                  className="w-full p-3 rounded-sm bg-elevated hover:bg-elevated/80 border border-subtle text-left transition-colors flex items-center justify-between cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <CheckSquare className="w-4 h-4 text-accent shrink-0" />
                    <div>
                      <span className="text-xs font-semibold text-ink block">Triage Review Cases</span>
                      <span className="text-[11px] text-muted font-medium">
                        Adjudicate ungrounded claims
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted group-hover:text-ink transition-colors" />
                </button>

                <button
                  onClick={() => {
                    if (applications.length > 0) {
                      navigate(`/employer/applications/${applications[0].id}`);
                    } else {
                      navigate('/employer/jobs');
                    }
                  }}
                  className="w-full p-3 rounded-sm bg-elevated hover:bg-elevated/80 border border-subtle text-left transition-colors flex items-center justify-between cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <Users className="w-4 h-4 text-accent shrink-0" />
                    <div>
                      <span className="text-xs font-semibold text-ink block">Candidate Dossiers</span>
                      <span className="text-[11px] text-muted font-medium">
                        {applications.length > 0
                          ? `Inspect ${applications.length} submitted dossiers`
                          : 'View active applicant cohort'}
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted group-hover:text-ink transition-colors" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
