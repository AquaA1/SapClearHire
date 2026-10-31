import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
import { ReviewFlagSummary } from '../../contracts/models';
import { ReviewFlagStatus } from '../../contracts/enums';
import { StatusBadge } from '../../components/ui/Badge';
import { ChevronRight, ShieldCheck, CheckSquare, Clock } from 'lucide-react';
import { useAuth } from '../../stores/authStore';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '../../components/ui';

export const ReviewerQueuePage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [flags, setFlags] = useState<ReviewFlagSummary[]>([]);
  const [statusFilter, setStatusFilter] = useState<'ALL' | ReviewFlagStatus>('ALL');

  useEffect(() => {
    mockService.listReviewCases().then(setFlags);
  }, []);

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
      <div className="pb-3 border-b border-subtle">
        <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">Review Cases Queue & Triage</h1>
        <p className="text-xs text-muted mt-1 font-medium">
          Triage ambiguous and disputed candidate criteria. Select any case to open the side-by-side Decision Studio.
        </p>
      </div>

      {/* ── Integrated Workload & Specialist Authority Stats ──── */}
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
              Signed Off Determinations
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
              <span className="text-[10px] text-accent uppercase font-semibold">Authorized Signer</span>
            </div>
            <h4 className="text-xs font-semibold text-ink truncate">{user.full_name}</h4>
            <span className="text-[11px] text-muted font-medium block mt-0.5">Human Reviewer Role</span>
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
            {filteredFlags.map((flag) => (
              <TableRow
                key={flag.id}
                onClick={() => navigate(`/reviewer/case/${flag.id}`)}
                className="cursor-pointer group"
              >
                <TableCell>
                  <div className="font-semibold text-ink text-xs group-hover:text-accent transition-colors">
                    {flag.candidate_name}
                  </div>
                  <div className="text-[11px] text-muted font-medium mt-0.5">CASE #{flag.id.slice(0, 8)}</div>
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
                      flag.priority === 'high'
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
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};
