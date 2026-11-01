import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../stores/authStore';
import { applicationService } from '../../services/api/applicationService';
import { jobService } from '../../services/api/jobService';
import { documentService } from '../../services/api/documentService';
import { Application, Job, DocumentStatusResponse } from '../../contracts/models';
import { JobStatus } from '../../contracts/enums';
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
  FileText,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Briefcase,
  ArrowUpRight,
  FileCheck,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';

export const CandidateDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [applications, setApplications] = useState<Application[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [primaryDocStatus, setPrimaryDocStatus] = useState<DocumentStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const loadDashboardData = async () => {
      try {
        const [apps, allJobs] = await Promise.all([
          applicationService.listApplications(),
          jobService.listJobs({ status: JobStatus.ACTIVE }),
        ]);
        if (!isMounted) return;
        setApplications(apps);
        setJobs(allJobs.slice(0, 4));
        setIsLoading(false);

        if (apps.length > 0 && apps[0].primary_document_id) {
          try {
            const docStatus = await documentService.getDocumentStatus(apps[0].primary_document_id);
            if (isMounted) {
              setPrimaryDocStatus(docStatus);
            }
          } catch {
            // Graceful fallback
          }
        }
      } catch (err) {
        console.error('Failed to load candidate dashboard data:', err);
        if (isMounted) setIsLoading(false);
      }
    };

    loadDashboardData();

    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[450px]">
        <LoadingSpinner size="lg" label="Loading candidate dossier..." />
      </div>
    );
  }

  // Derived factual metrics from real backend database records
  const totalAppsCount = applications.length;
  const inProgressCount = applications.filter(
    (a) => a.status === 'screening' || a.status === 'needs_review' || a.status === 'submitted'
  ).length;

  const actionRequiredApps = applications.filter((a) => a.status === 'needs_review');
  const actionRequiredCount = actionRequiredApps.length;
  const primaryApp = applications.length > 0 ? applications[0] : null;

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-subtle">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">
            Welcome back, {user?.full_name || 'Candidate'}
          </h1>
          <p className="text-xs text-muted mt-1 font-medium">
            Track your candidate qualification evidence, application progress, and reviewer requests.
          </p>
        </div>

        <Button
          onClick={() => navigate('/candidate/jobs')}
          variant="primary"
          size="sm"
          leftIcon={<Briefcase className="w-4 h-4" />}
          className="shrink-0 self-start sm:self-auto cursor-pointer font-semibold shadow-sm"
        >
          Explore Openings
        </Button>
      </div>

      {/* ── Bento Grid ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Stats, Resume & Mint Highlighted Card (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-5">
          {/* Bento Stat Card 1: Split Stat (Total Apps & In Progress) */}
          <div className="bg-surface border border-subtle rounded-card p-5 shadow-card">
            <div className="grid grid-cols-2 divide-x divide-subtle">
              <div className="pr-4">
                <span className="text-3xl sm:text-4xl font-semibold text-ink tracking-tight block">
                  {totalAppsCount}
                </span>
                <span className="text-xs text-muted mt-1.5 font-medium block">Submitted Apps</span>
              </div>
              <div className="pl-4">
                <span className="text-3xl sm:text-4xl font-semibold text-ink tracking-tight block">
                  {inProgressCount}
                </span>
                <span className="text-xs text-muted mt-1.5 font-medium block">In Screening</span>
              </div>
            </div>
          </div>

          {/* Bento Card 2: Primary Resume Document Status */}
          <div className="bg-surface border border-subtle rounded-card p-5 shadow-card space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-subtle">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted">
                Primary Resume
              </span>
              {primaryApp ? (
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-pill bg-success-dim text-success border border-success/30">
                  Registered
                </span>
              ) : (
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-pill bg-elevated text-muted border border-subtle">
                  Not Uploaded
                </span>
              )}
            </div>

            {primaryApp ? (
              <div className="flex items-center gap-3 p-3 rounded-sm bg-elevated border border-subtle">
                <FileCheck className="w-5 h-5 text-accent shrink-0" />
                <div className="min-w-0 flex-1">
                  <span className="text-xs font-semibold text-ink block truncate">
                    {primaryDocStatus?.file_name || `Document #${primaryApp.primary_document_id.slice(0, 8)}.pdf`}
                  </span>
                  <span className="text-[11px] text-muted font-medium block mt-0.5 truncate">
                    Attached to {primaryApp.job_title}
                  </span>
                </div>
                <Link
                  to={`/candidate/applications/${primaryApp.id}`}
                  className="text-muted hover:text-ink p-1 transition-colors"
                  title="View verified application evidence"
                >
                  <ArrowUpRight className="w-4 h-4" />
                </Link>
              </div>
            ) : (
              <div className="p-4 rounded-sm bg-elevated/40 border border-subtle text-center space-y-2">
                <FileText className="w-6 h-6 text-muted mx-auto opacity-50" />
                <div>
                  <span className="text-xs font-semibold text-ink block">No Resume on File</span>
                  <span className="text-[11px] text-muted font-medium block mt-0.5">
                    Upload your resume when applying to active job requisitions.
                  </span>
                </div>
                <Button
                  onClick={() => navigate('/candidate/jobs')}
                  variant="secondary"
                  size="sm"
                  className="w-full text-xs mt-1"
                >
                  Browse Openings
                </Button>
              </div>
            )}
          </div>

          {/* ── THE ONE MINT HIGHLIGHTED CARD ── */}
          <div className="bg-accent-dim border border-accent/30 rounded-card p-5 shadow-card flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-accent uppercase tracking-wider flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" />
                Evidence Status
              </span>
              <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-pill bg-accent/20 text-accent border border-accent/40">
                {actionRequiredCount > 0
                  ? `${actionRequiredCount} Action Required`
                  : totalAppsCount > 0
                  ? 'Evaluation Active'
                  : 'Ready to Apply'}
              </span>
            </div>

            <div>
              <h3 className="text-base font-semibold text-ink leading-snug">
                {actionRequiredCount > 0
                  ? `Clarification: ${actionRequiredApps[0].job_title}`
                  : totalAppsCount > 0
                  ? 'All Evidence Grounded'
                  : 'Start Your Transparent Application'}
              </h3>
              <p className="text-xs text-ink/90 mt-1.5 leading-relaxed">
                {actionRequiredCount > 0
                  ? 'A human reviewer requested clarification on an ambiguous qualification. Providing written proof updates your dossier.'
                  : totalAppsCount > 0
                  ? 'Your qualifications are deterministically benchmarked against published criteria with verifiable proof.'
                  : 'Apply to active positions to generate deterministic OCR extractions and cryptographic audit logs.'}
              </p>
            </div>

            {actionRequiredCount > 0 ? (
              <Button
                onClick={() => navigate(`/candidate/applications/${actionRequiredApps[0].id}`)}
                variant="primary"
                size="sm"
                rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                className="w-full justify-between font-semibold"
              >
                <span>Provide Clarification</span>
              </Button>
            ) : totalAppsCount > 0 ? (
              <Button
                onClick={() => navigate('/candidate/applications')}
                variant="primary"
                size="sm"
                rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                className="w-full justify-between font-semibold"
              >
                <span>Inspect My Applications</span>
              </Button>
            ) : (
              <Button
                onClick={() => navigate('/candidate/jobs')}
                variant="primary"
                size="sm"
                rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                className="w-full justify-between font-semibold"
              >
                <span>Browse New Openings</span>
              </Button>
            )}
          </div>
        </div>

        {/* Right Column: Applications Table & Secondary Panels (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col gap-5">
          {/* Applications Table */}
          <div className="bg-surface border border-subtle rounded-card shadow-card overflow-hidden">
            <div className="p-5 border-b border-subtle flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-ink">My Applications</h2>
                <p className="text-xs text-muted font-medium mt-0.5">
                  Current screening status and grounded dossiers
                </p>
              </div>
              <Link
                to="/candidate/applications"
                className="text-xs font-semibold text-muted hover:text-ink flex items-center gap-1 transition-colors"
              >
                <span>All Applications</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Requisition Title</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Submitted</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {applications.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="py-12 text-center text-muted font-medium">
                      <div className="max-w-xs mx-auto space-y-2">
                        <FileText className="w-8 h-8 text-muted mx-auto opacity-40" />
                        <p className="text-xs text-muted">You have not submitted any applications yet.</p>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => navigate('/candidate/jobs')}
                          className="text-xs mt-1"
                        >
                          Explore Active Positions
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  applications.slice(0, 5).map((app) => (
                    <TableRow key={app.id}>
                      <TableCell>
                        <div className="font-semibold text-ink text-xs">{app.job_title}</div>
                        <div className="text-[11px] text-muted font-medium mt-0.5">
                          App #{app.id.slice(0, 8)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs font-medium text-ink/90">
                          {app.department || 'General'}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs font-medium text-muted whitespace-nowrap">
                          {new Date(app.submitted_at || app.created_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                        </span>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={app.status} size="sm" />
                      </TableCell>
                      <TableCell className="text-right">
                        <Link
                          to={`/candidate/applications/${app.id}`}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline transition-colors"
                        >
                          <span>Evidence</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Lower Bento Grid: Recent Activity & Featured Openings (6 cols each) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Recent Evidence Activity Timeline */}
            <div className="bg-surface border border-subtle rounded-card p-5 shadow-card space-y-3.5">
              <div className="flex items-center justify-between pb-2 border-b border-subtle">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
                    Evidence Ledger
                  </h3>
                  <p className="text-xs text-muted font-medium">Auditable events for your profile</p>
                </div>
                <Link to="/candidate/applications" className="text-xs font-semibold text-muted hover:text-ink">
                  All Records
                </Link>
              </div>

              <div className="space-y-2.5">
                {applications.length === 0 ? (
                  <div className="p-6 rounded-sm bg-elevated/40 border border-subtle text-center text-muted space-y-1">
                    <ShieldCheck className="w-6 h-6 text-muted mx-auto opacity-50" />
                    <p className="text-xs font-medium text-ink">No Ledger Events Yet</p>
                    <p className="text-[11px] text-muted">
                      Cryptographic audit records begin automatically upon submitting your first application.
                    </p>
                  </div>
                ) : (
                  applications.slice(0, 3).map((app) => (
                    <div
                      key={app.id}
                      className="flex items-start gap-3 p-3 rounded-sm bg-elevated border border-subtle"
                    >
                      <div className="w-7 h-7 rounded-sm bg-surface border border-subtle flex items-center justify-center text-accent shrink-0 mt-0.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-accent" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-ink truncate capitalize">
                            Application Submitted
                          </span>
                          <span className="text-[10px] text-muted font-medium whitespace-nowrap">
                            {new Date(app.submitted_at || app.created_at).toLocaleDateString([], {
                              month: 'short',
                              day: 'numeric',
                            })}
                          </span>
                        </div>
                        <p className="text-[11px] text-muted font-medium mt-0.5 truncate">
                          Requisition: {app.job_title}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Featured Openings */}
            <div className="bg-surface border border-subtle rounded-card p-5 shadow-card space-y-3.5">
              <div className="flex items-center justify-between pb-2 border-b border-subtle">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
                    Featured Openings
                  </h3>
                  <p className="text-xs text-muted font-medium">Matching verified competencies</p>
                </div>
                <Link to="/candidate/jobs" className="text-xs font-semibold text-muted hover:text-ink">
                  All ({jobs.length})
                </Link>
              </div>

              <div className="space-y-2.5">
                {jobs.length === 0 ? (
                  <div className="p-6 rounded-sm bg-elevated/40 border border-subtle text-center text-muted space-y-1">
                    <Briefcase className="w-6 h-6 text-muted mx-auto opacity-50" />
                    <p className="text-xs font-medium text-ink">No Open Positions</p>
                    <p className="text-[11px] text-muted">Check back later for newly published requisitions.</p>
                  </div>
                ) : (
                  jobs.map((job) => (
                    <Link
                      key={job.id}
                      to={`/candidate/jobs/${job.id}`}
                      className="block p-3 rounded-sm bg-elevated hover:bg-elevated/80 border border-subtle transition-colors space-y-1 group"
                    >
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-semibold text-ink truncate group-hover:text-accent transition-colors">
                          {job.title}
                        </h4>
                        <ChevronRight className="w-3.5 h-3.5 text-muted group-hover:text-ink shrink-0 transition-colors" />
                      </div>
                      <span className="text-[11px] text-muted font-medium block">
                        {job.department || 'General'} • {job.criteria?.length || 0} Screening Criteria
                      </span>
                    </Link>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
