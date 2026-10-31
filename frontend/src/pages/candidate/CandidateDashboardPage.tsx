import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../stores/authStore';
import { mockService } from '../../services/mock/mockService';
import { Application, Job, ReviewFlagSummary, AuditEvent } from '../../contracts/models';
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
  Clock,
  CheckCircle2,
  Briefcase,
  ArrowUpRight,
  FileCheck,
  ChevronRight,
  Sparkles,
} from 'lucide-react';

export const CandidateDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [applications, setApplications] = useState<Application[]>([]);
  const [reviewFlags, setReviewFlags] = useState<ReviewFlagSummary[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        const [apps, flags, events, allJobs] = await Promise.all([
          mockService.listApplications(),
          mockService.listReviewCases(),
          mockService.listAuditEvents(),
          mockService.listJobs(),
        ]);
        setApplications(apps);
        setReviewFlags(flags);
        setAuditEvents(events.slice(0, 4));
        setJobs(allJobs.slice(0, 3));
      } catch (err) {
        console.error('Failed to load candidate dashboard:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[450px]">
        <LoadingSpinner size="lg" label="Loading candidate dossier..." />
      </div>
    );
  }

  // Factual, supported counts only
  const totalAppsCount = applications.length;
  const inProgressCount = applications.filter(
    (a) => a.status === 'screening' || a.status === 'needs_review'
  ).length;

  const pendingActions = reviewFlags.filter((f) => f.status === 'pending' || f.status === 'under_review');
  const actionRequiredCount = pendingActions.length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-subtle">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">
            Welcome back, {user.full_name}
          </h1>
          <p className="text-xs text-muted mt-1 font-medium">
            Track your candidate qualification evidence, application progress, and reviewer requests.
          </p>
        </div>

        <Button
          onClick={() => navigate('/candidate/jobs')}
          variant="white"
          size="sm"
          leftIcon={<Briefcase className="w-4 h-4" />}
          className="shrink-0 self-start sm:self-auto cursor-pointer font-semibold shadow-sm"
        >
          Explore Openings
        </Button>
      </div>

      {/* ── Bento Grid ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* Left Column: Stats, Resume & The ONE Mint Highlighted Card (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-5">
          
          {/* Bento Stat Card 1: Split Stat (Total Apps & In Progress) */}
          <div className="bg-surface border border-subtle rounded-card p-5 shadow-card">
            <div className="grid grid-cols-2 divide-x divide-subtle">
              <div className="pr-4">
                <span className="text-3xl sm:text-4xl font-semibold text-ink tracking-tight block">
                  {totalAppsCount}
                </span>
                <span className="text-xs text-muted mt-1.5 font-medium block">
                  Submitted Apps
                </span>
              </div>
              <div className="pl-4">
                <span className="text-3xl sm:text-4xl font-semibold text-ink tracking-tight block">
                  {inProgressCount}
                </span>
                <span className="text-xs text-muted mt-1.5 font-medium block">
                  In Screening
                </span>
              </div>
            </div>
          </div>

          {/* Bento Card 2: Primary Resume Document Status */}
          <div className="bg-surface border border-subtle rounded-card p-5 shadow-card space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-subtle">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted">Primary Resume</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-pill bg-success-dim text-success border border-success/30 font-medium">
                OCR Parsed
              </span>
            </div>

            <div className="flex items-center gap-3 p-3 rounded-sm bg-elevated border border-subtle">
              <FileCheck className="w-5 h-5 text-accent shrink-0" />
              <div className="min-w-0 flex-1">
                <span className="text-xs font-semibold text-ink block truncate">
                  Elena_Rostova_Resume_2026.pdf
                </span>
                <span className="text-[11px] text-muted font-mono block mt-0.5">
                  Verbatim line coordinate index active
                </span>
              </div>
              <Link
                to="/candidate/applications"
                className="text-muted hover:text-ink p-1 transition-colors"
                title="View verified application evidence"
              >
                <ArrowUpRight className="w-4 h-4" />
              </Link>
            </div>
          </div>

          {/* ── THE ONE MINT HIGHLIGHTED CARD ── */}
          <div className="bg-accent-dim border border-accent/30 rounded-card p-5 shadow-card flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-accent uppercase tracking-wider flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" />
                Evidence Status
              </span>
              <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-pill bg-accent/20 text-accent border border-accent/40">
                {actionRequiredCount > 0 ? `${actionRequiredCount} Action Required` : 'Fully Grounded'}
              </span>
            </div>

            <div>
              <h3 className="text-base font-semibold text-ink leading-snug">
                {actionRequiredCount > 0
                  ? `Clarification: ${pendingActions[0]?.criterion_name || 'Evaluation Item'}`
                  : 'Zero Ungrounded Discrepancies'}
              </h3>
              <p className="text-xs text-ink/90 mt-1.5 leading-relaxed">
                {actionRequiredCount > 0
                  ? 'A human reviewer requested context for an ambiguous qualification. Providing written proof updates your dossier.'
                  : 'Your qualifications match OCR resume evidence with cryptographic SHA-256 verification.'}
              </p>
            </div>

            {actionRequiredCount > 0 ? (
              <Button
                onClick={() => navigate(`/candidate/applications/${pendingActions[0].application_id}`)}
                variant="primary"
                size="sm"
                rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                className="w-full justify-between font-semibold"
              >
                <span>Provide Clarification</span>
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
                <p className="text-xs text-muted font-medium mt-0.5">Current screening status and grounded dossiers</p>
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
                    <TableCell colSpan={5} className="py-10 text-center text-muted font-medium">
                      No submitted applications yet.
                    </TableCell>
                  </TableRow>
                ) : (
                  applications.map((app) => (
                    <TableRow key={app.id}>
                      <TableCell>
                        <div className="font-semibold text-ink text-xs">{app.job_title}</div>
                        <div className="text-[11px] text-muted font-mono mt-0.5">App #{app.id.slice(0, 8)}</div>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs font-medium text-ink/90">
                          {app.department || 'Engineering'}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs font-medium text-muted whitespace-nowrap">
                          {new Date(app.submitted_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric'
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
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Evidence Ledger</h3>
                  <p className="text-xs text-muted font-medium">Auditable events for your profile</p>
                </div>
                <Link to="/candidate/applications" className="text-xs font-semibold text-muted hover:text-ink">
                  All Records
                </Link>
              </div>

              <div className="space-y-2.5">
                {auditEvents.map((event) => (
                  <div key={event.id} className="flex items-start gap-3 p-3 rounded-sm bg-elevated border border-subtle">
                    <div className="w-7 h-7 rounded-sm bg-surface border border-subtle flex items-center justify-center text-accent shrink-0 mt-0.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-accent" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-ink truncate capitalize">{event.action.replace(/_/g, ' ')}</span>
                        <span className="text-[10px] text-muted font-mono whitespace-nowrap">
                          {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted font-mono mt-0.5 truncate">
                        Hash: {event.event_hash.slice(0, 16)}...
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Featured Openings */}
            <div className="bg-surface border border-subtle rounded-card p-5 shadow-card space-y-3.5">
              <div className="flex items-center justify-between pb-2 border-b border-subtle">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Featured Openings</h3>
                  <p className="text-xs text-muted font-medium">Matching verified competencies</p>
                </div>
                <Link to="/candidate/jobs" className="text-xs font-semibold text-muted hover:text-ink">
                  All ({jobs.length})
                </Link>
              </div>

              <div className="space-y-2.5">
                {jobs.map((job) => (
                  <Link
                    key={job.id}
                    to={`/candidate/jobs/${job.id}`}
                    className="block p-3 rounded-sm bg-elevated hover:bg-elevated/80 border border-subtle transition-colors space-y-1 group"
                  >
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold text-ink truncate group-hover:text-accent transition-colors">{job.title}</h4>
                      <ChevronRight className="w-3.5 h-3.5 text-muted group-hover:text-ink shrink-0 transition-colors" />
                    </div>
                    <span className="text-[11px] text-muted font-medium block">
                      {job.department || 'Engineering'} • {job.criteria.length} Verification Criteria
                    </span>
                  </Link>
                ))}
              </div>
            </div>

          </div>

        </div>

      </div>

    </div>
  );
};
