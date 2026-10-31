import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { reviewService } from '../../services/api/reviewService';
import { applicationService } from '../../services/api/applicationService';
import { ReviewFlagSummary } from '../../contracts/models';
import { ReviewFlagStatus } from '../../contracts/enums';
import { StatusBadge } from '../../components/ui/Badge';
import { ChevronRight, ShieldCheck, CheckSquare, Clock, Inbox, Briefcase } from 'lucide-react';
import { useAuth } from '../../stores/authStore';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  LoadingSpinner,
  Button,
} from '../../components/ui';

export const EmployerReviewQueuePage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [flags, setFlags] = useState<ReviewFlagSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<'ALL' | ReviewFlagStatus>('ALL');

  useEffect(() => {
    const fetchOrgFlags = async () => {
      setLoading(true);
      try {
        const apps = await applicationService.listApplications();

        // Strict organization tenant isolation: query review flags strictly scoped to employer applications
        if (apps.length > 0) {
          const flagPromises = apps.map((app) =>
            reviewService.listReviewFlags({ application_id: app.id }).catch(() => [])
          );
          const flagBatches = await Promise.all(flagPromises);
          setFlags(flagBatches.flat());
        } else {
          setFlags([]);
        }
      } catch (err) {
        console.error('Failed to load employer review cases:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchOrgFlags();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[450px]">
        <LoadingSpinner size="lg" label="Loading organization review cases..." />
      </div>
    );
  }

  const pendingCount = flags.filter((f) => f.status === ReviewFlagStatus.PENDING).length;
  const underReviewCount = flags.filter((f) => f.status === ReviewFlagStatus.UNDER_REVIEW).length;
  const resolvedCount = flags.filter((f) => f.status === ReviewFlagStatus.RESOLVED).length;

  const filteredFlags =
    statusFilter === 'ALL'
      ? flags
      : flags.filter((f) => f.status === statusFilter);

  return (
    <div className="max-w-7xl mx-auto space-y-6 select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-subtle">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">
            Organization Review Triage & Adjudications
          </h1>
          <p className="text-xs text-muted mt-1 font-medium">
            Inspect, contest, and adjudicate ambiguous candidate qualification criteria for your active requisitions.
          </p>
        </div>

        <Button
          onClick={() => navigate('/employer/jobs')}
          variant="secondary"
          size="sm"
          leftIcon={<Briefcase className="w-4 h-4" />}
          className="self-start sm:self-auto font-medium"
        >
          Manage Requisitions
        </Button>
      </div>

      {/* ── Tenant-Isolation Safeguard Banner ─────────────────── */}
      <div className="bg-surface border border-subtle rounded-card p-4 flex items-start gap-3.5 shadow-card">
        <div className="w-8 h-8 rounded-lg bg-accent/15 border border-accent/30 text-accent flex items-center justify-center shrink-0 mt-0.5">
          <ShieldCheck className="w-4 h-4" />
        </div>
        <div className="space-y-0.5 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-ink">Tenant-Isolated Review Triage Active</span>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-pill bg-accent/20 text-accent border border-accent/30 uppercase tracking-wider">
              Scoped
            </span>
          </div>
          <p className="text-[11px] text-muted leading-relaxed">
            Review cases are strictly scoped per authorized application ID (<code className="text-accent bg-elevated px-1 py-0.5 rounded font-mono text-[10px]">GET /api/v1/review-flags?application_id=...</code>) to prevent cross-organization candidate data exposure. Global unscoped querying is disabled.
          </p>
        </div>
      </div>

      {/* ── Integrated Workload & Admin Authority Stats ────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-surface border border-subtle rounded-card p-5 shadow-card flex items-center justify-between">
          <div>
            <span className="text-3xl font-semibold text-warn tracking-tight block">
              {pendingCount}
            </span>
            <span className="text-xs text-muted mt-1 font-medium block">
              Pending Adjudication
            </span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-warn-dim border border-warn/30 text-warn flex items-center justify-center">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-surface border border-subtle rounded-card p-5 shadow-card flex items-center justify-between">
          <div>
            <span className="text-3xl font-semibold text-success tracking-tight block">
              {resolvedCount}
            </span>
            <span className="text-xs text-muted mt-1 font-medium block">
              Resolved Determinations
            </span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-success-dim border border-success/30 text-success flex items-center justify-center">
            <CheckSquare className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-surface border border-subtle rounded-card p-5 shadow-card flex items-center justify-between">
          <div className="min-w-0 pr-2">
            <div className="flex items-center gap-1.5 mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
              <span className="text-[10px] text-accent uppercase font-semibold">
                Authorized Administrator
              </span>
            </div>
            <h4 className="text-xs font-semibold text-ink truncate">
              {user?.full_name || 'Employer Admin'}
            </h4>
            <span className="text-[11px] text-muted font-medium block mt-0.5">
              Employer Administrator Role
            </span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-elevated border border-subtle text-accent flex items-center justify-center shrink-0">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* ── Filter Tabs ───────────────────────────────────────── */}
      <div className="bg-surface p-3.5 rounded-card border border-subtle shadow-card flex items-center gap-2 overflow-x-auto">
        <button
          onClick={() => setStatusFilter('ALL')}
          className={`px-3.5 py-1.5 rounded-pill text-xs font-semibold transition-all cursor-pointer ${
            statusFilter === 'ALL'
              ? 'bg-elevated text-ink border border-subtle shadow-sm'
              : 'text-muted hover:text-ink'
          }`}
        >
          All Cases ({flags.length})
        </button>
        <button
          onClick={() => setStatusFilter(ReviewFlagStatus.PENDING)}
          className={`px-3.5 py-1.5 rounded-pill text-xs font-semibold transition-all cursor-pointer ${
            statusFilter === ReviewFlagStatus.PENDING
              ? 'bg-elevated text-ink border border-subtle shadow-sm'
              : 'text-muted hover:text-ink'
          }`}
        >
          Pending Action ({pendingCount})
        </button>
        <button
          onClick={() => setStatusFilter(ReviewFlagStatus.UNDER_REVIEW)}
          className={`px-3.5 py-1.5 rounded-pill text-xs font-semibold transition-all cursor-pointer ${
            statusFilter === ReviewFlagStatus.UNDER_REVIEW
              ? 'bg-elevated text-ink border border-subtle shadow-sm'
              : 'text-muted hover:text-ink'
          }`}
        >
          Under Review ({underReviewCount})
        </button>
        <button
          onClick={() => setStatusFilter(ReviewFlagStatus.RESOLVED)}
          className={`px-3.5 py-1.5 rounded-pill text-xs font-semibold transition-all cursor-pointer ${
            statusFilter === ReviewFlagStatus.RESOLVED
              ? 'bg-elevated text-ink border border-subtle shadow-sm'
              : 'text-muted hover:text-ink'
          }`}
        >
          Resolved ({resolvedCount})
        </button>
      </div>

      {/* ── Cases Queue Table Card ────────────────────────────── */}
      <div className="bg-surface rounded-card p-6 border border-subtle shadow-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Candidate</TableHead>
              <TableHead>Job Requisition</TableHead>
              <TableHead>Contested Criterion</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredFlags.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-16 text-center text-muted font-medium">
                  <div className="max-w-xs mx-auto space-y-2">
                    <Inbox className="w-10 h-10 text-muted mx-auto opacity-40" />
                    <p className="text-sm font-semibold text-ink">Review Queue Clear</p>
                    <p className="text-xs text-muted">
                      No criteria flags currently require adjudication for your organization's requisitions.
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              filteredFlags.map((flag) => (
                <TableRow
                  key={flag.id}
                  onClick={() => navigate(`/employer/reviews/${flag.id}`)}
                  className="cursor-pointer group"
                >
                  <TableCell>
                    <div className="font-semibold text-ink text-xs group-hover:text-accent transition-colors">
                      {flag.candidate_name || `Candidate #${flag.candidate_id.slice(0, 8)}`}
                    </div>
                    <div className="text-[11px] text-muted font-medium mt-0.5">
                      CASE #{flag.id.slice(0, 8)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-xs font-medium text-ink">
                      {flag.job_title}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="font-semibold text-ink text-xs block max-w-xs truncate">
                      {flag.criterion_name}
                    </span>
                    <span className="text-[11px] text-muted block truncate max-w-xs font-medium">
                      {flag.reason}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span
                      className={`text-[10px] font-semibold px-2.5 py-0.5 rounded-pill uppercase tracking-wider ${
                        flag.priority?.toLowerCase() === 'high'
                          ? 'bg-danger-dim text-danger border border-danger/30'
                          : 'bg-elevated text-muted border border-subtle'
                      }`}
                    >
                      {flag.priority}
                    </span>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={flag.status} size="sm" />
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="text-xs font-semibold text-accent group-hover:underline inline-flex items-center gap-1">
                      <span>Open Studio</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </span>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};
