import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
import { ReviewFlagSummary } from '../../contracts/models';
import { ReviewFlagStatus } from '../../contracts/enums';
import { StatusBadge } from '../../components/ui/Badge';
import { ChevronRight } from 'lucide-react';
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
  const [flags, setFlags] = useState<ReviewFlagSummary[]>([]);
  const [statusFilter, setStatusFilter] = useState<'ALL' | ReviewFlagStatus>('ALL');

  useEffect(() => {
    mockService.listReviewCases().then(setFlags);
  }, []);

  const filteredFlags =
    statusFilter === 'ALL'
      ? flags
      : flags.filter((f) => f.status === statusFilter);

  return (
    <div className="max-w-7xl mx-auto space-y-6 select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="pb-3 border-b border-subtle">
        <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">Review Cases Queue</h1>
        <p className="text-xs text-muted mt-1 font-medium">
          Triage ambiguous and disputed candidate criteria. Select a case to open the side-by-side Decision Studio.
        </p>
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
          Pending Action ({flags.filter((f) => f.status === ReviewFlagStatus.PENDING).length})
        </button>
        <button
          onClick={() => setStatusFilter(ReviewFlagStatus.UNDER_REVIEW)}
          className={`px-3.5 py-1.5 rounded-pill text-xs font-semibold transition-all cursor-pointer ${
            statusFilter === ReviewFlagStatus.UNDER_REVIEW
              ? 'bg-elevated text-ink border border-subtle shadow-sm'
              : 'text-muted hover:text-ink'
          }`}
        >
          Under Review ({flags.filter((f) => f.status === ReviewFlagStatus.UNDER_REVIEW).length})
        </button>
        <button
          onClick={() => setStatusFilter(ReviewFlagStatus.RESOLVED)}
          className={`px-3.5 py-1.5 rounded-pill text-xs font-semibold transition-all cursor-pointer ${
            statusFilter === ReviewFlagStatus.RESOLVED
              ? 'bg-elevated text-ink border border-subtle shadow-sm'
              : 'text-muted hover:text-ink'
          }`}
        >
          Resolved ({flags.filter((f) => f.status === ReviewFlagStatus.RESOLVED).length})
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
                  <div className="text-[11px] text-muted font-mono mt-0.5">CASE #{flag.id.slice(0, 8)}</div>
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
