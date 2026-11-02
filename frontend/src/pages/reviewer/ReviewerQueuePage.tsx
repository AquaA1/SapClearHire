import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { reviewService } from '../../services/api/reviewService';
import { ReviewFlagSummary } from '../../contracts/models';
import { ReviewFlagStatus } from '../../contracts/enums';
import { StatusBadge } from '../../components/ui/Badge';
import { ChevronRight, ShieldCheck, CheckSquare, Clock, Inbox, RotateCw } from 'lucide-react';
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

export const ReviewerQueuePage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [flags, setFlags] = useState<ReviewFlagSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<'ALL' | ReviewFlagStatus>('ALL');

  const deduplicateFlags = (list: ReviewFlagSummary[]): ReviewFlagSummary[] => {
    const map = new Map<string, ReviewFlagSummary>();
    for (const f of list) {
      const key = f.criterion_evidence_id
        ? `${f.application_id}_${f.criterion_evidence_id}`
        : f.id;
      if (!map.has(key)) {
        map.set(key, f);
      } else {
        const existing = map.get(key)!;
        if (new Date(f.created_at).getTime() > new Date(existing.created_at).getTime()) {
          map.set(key, f);
        }
      }
    }
    return Array.from(map.values());
  };

  const fetchFlags = async () => {
    try {
      const data = await reviewService.listReviewFlags();
      setFlags(deduplicateFlags(data || []));
    } catch (err) {
      console.error('Failed to load review cases queue:', err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchFlags();
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchFlags();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[450px]">
        <LoadingSpinner size="lg" label="Loading reviewer case queue..." />
      </div>
    );
  }

  // Authoritative counts: pendingCount includes all genuinely unresolved cases (PENDING and UNDER_REVIEW)
  const pendingCount = flags.filter(
    (f) => f.status === ReviewFlagStatus.PENDING || f.status === ReviewFlagStatus.UNDER_REVIEW
  ).length;
  const underReviewCount = flags.filter((f) => f.status === ReviewFlagStatus.UNDER_REVIEW).length;
  const resolvedCount = flags.filter((f) => f.status === ReviewFlagStatus.RESOLVED).length;

  const filteredFlags =
    statusFilter === 'ALL'
      ? flags
      : statusFilter === ReviewFlagStatus.PENDING
      ? flags.filter(
          (f) => f.status === ReviewFlagStatus.PENDING || f.status === ReviewFlagStatus.UNDER_REVIEW
        )
      : flags.filter((f) => f.status === statusFilter);

  return (
    <div className="max-w-7xl mx-auto space-y-8 select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-subtle">
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold text-ink tracking-tight">
            Review Cases Queue & Triage
          </h1>
          <p className="text-sm sm:text-base text-ink-secondary mt-1.5 font-medium leading-relaxed">
            Triage ambiguous and disputed candidate criteria. Select any case to open the side-by-side Decision Studio.
          </p>
        </div>
        <Button
          onClick={handleRefresh}
          variant="secondary"
          size="md"
          isLoading={isRefreshing}
          leftIcon={<RotateCw className="w-4 h-4" />}
          className="self-start sm:self-auto font-semibold"
        >
          Refresh Queue
        </Button>
      </div>

      {/* ── Integrated Workload & Specialist Authority Stats ──── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-surface border border-subtle rounded-card p-6 shadow-card flex items-center justify-between">
          <div>
            <span className="text-4xl sm:text-5xl font-bold text-warn tracking-tight block">
              {pendingCount}
            </span>
            <span className="text-sm text-muted mt-2 font-semibold block">
              Pending Adjudication
            </span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-warn-dim border border-warn/30 text-warn flex items-center justify-center">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-surface border border-subtle rounded-card p-6 shadow-card flex items-center justify-between">
          <div>
            <span className="text-4xl sm:text-5xl font-bold text-success tracking-tight block">
              {resolvedCount}
            </span>
            <span className="text-sm text-muted mt-2 font-semibold block">
              Signed Off Determinations
            </span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-success-dim border border-success/30 text-success flex items-center justify-center">
            <CheckSquare className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-surface border border-subtle rounded-card p-6 shadow-card flex items-center justify-between">
          <div className="min-w-0 pr-3">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-2 h-2 rounded-full bg-accent" />
              <span className="text-xs text-accent uppercase font-bold tracking-wider">Authorized Signer</span>
            </div>
            <h4 className="text-base sm:text-lg font-bold text-ink truncate">{user?.full_name || 'Reviewer'}</h4>
            <span className="text-xs sm:text-sm text-muted font-medium block mt-1">Human Reviewer Role</span>
          </div>
          <div className="w-12 h-12 rounded-xl bg-elevated border border-subtle text-accent flex items-center justify-center shrink-0">
            <ShieldCheck className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* ── Filter Tabs ───────────────────────────────────────── */}
      <div className="bg-surface p-4 rounded-card border border-subtle shadow-card flex items-center gap-2.5 overflow-x-auto">
        <button
          onClick={() => setStatusFilter('ALL')}
          className={`px-4 py-2 rounded-pill text-xs sm:text-sm font-bold transition-all cursor-pointer ${
            statusFilter === 'ALL'
              ? 'bg-elevated text-ink border border-subtle shadow-sm'
              : 'text-muted hover:text-ink'
          }`}
        >
          All Cases ({flags.length})
        </button>
        <button
          onClick={() => setStatusFilter(ReviewFlagStatus.PENDING)}
          className={`px-4 py-2 rounded-pill text-xs sm:text-sm font-bold transition-all cursor-pointer ${
            statusFilter === ReviewFlagStatus.PENDING
              ? 'bg-elevated text-ink border border-subtle shadow-sm'
              : 'text-muted hover:text-ink'
          }`}
        >
          Pending Action ({pendingCount})
        </button>
        <button
          onClick={() => setStatusFilter(ReviewFlagStatus.UNDER_REVIEW)}
          className={`px-4 py-2 rounded-pill text-xs sm:text-sm font-bold transition-all cursor-pointer ${
            statusFilter === ReviewFlagStatus.UNDER_REVIEW
              ? 'bg-elevated text-ink border border-subtle shadow-sm'
              : 'text-muted hover:text-ink'
          }`}
        >
          Under Review ({underReviewCount})
        </button>
        <button
          onClick={() => setStatusFilter(ReviewFlagStatus.RESOLVED)}
          className={`px-4 py-2 rounded-pill text-xs sm:text-sm font-bold transition-all cursor-pointer ${
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
                  <div className="max-w-sm mx-auto space-y-2">
                    <Inbox className="w-12 h-12 text-muted mx-auto opacity-40" />
                    <p className="text-base sm:text-lg font-bold text-ink">Review Queue Empty</p>
                    <p className="text-xs sm:text-sm text-muted">
                      No candidate criteria flags currently require adjudication.
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              filteredFlags.map((flag) => (
                <TableRow
                  key={flag.id}
                  onClick={() => navigate(`/reviewer/case/${flag.id}`)}
                  className="cursor-pointer group hover:bg-elevated/40"
                >
                  <TableCell>
                    <div className="font-bold text-ink text-sm sm:text-base group-hover:text-accent transition-colors">
                      {flag.candidate_name || `Candidate #${flag.candidate_id.slice(0, 8)}`}
                    </div>
                    <div className="text-xs font-mono text-muted font-medium mt-1">
                      CASE #{flag.id.slice(0, 8)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm sm:text-base font-semibold text-ink">
                      {flag.job_title}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="font-bold text-ink text-sm sm:text-base block max-w-sm truncate">
                      {flag.criterion_name}
                    </span>
                    <span className="text-xs sm:text-sm text-ink-secondary block truncate max-w-sm font-medium mt-0.5">
                      {flag.reason}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span
                      className={`text-xs font-bold px-3 py-1 rounded-pill uppercase tracking-wider ${
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
                    <span className="text-sm sm:text-base font-bold text-accent group-hover:underline inline-flex items-center gap-1.5">
                      <span>Open Studio</span>
                      <ChevronRight className="w-4 h-4" />
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
