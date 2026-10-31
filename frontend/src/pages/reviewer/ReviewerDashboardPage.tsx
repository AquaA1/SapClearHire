import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
import { ReviewFlagSummary } from '../../contracts/models';
import { StatusBadge } from '../../components/ui/Badge';
import {
  CheckSquare,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Clock,
  ChevronRight,
  UserCheck,
  FileSearch,
} from 'lucide-react';
import { useAuth } from '../../stores/authStore';
import { Button, LoadingSpinner } from '../../components/ui';

export const ReviewerDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [flags, setFlags] = useState<ReviewFlagSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    mockService.listReviewCases().then((f) => {
      setFlags(f);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[450px]">
        <LoadingSpinner size="lg" label="Loading reviewer command center..." />
      </div>
    );
  }

  const pendingCount = flags.filter((f) => f.status === 'pending').length;
  const underReviewCount = flags.filter((f) => f.status === 'under_review').length;
  const resolvedCount = flags.filter((f) => f.status === 'resolved').length;
  const highPriorityFlag = flags.find((f) => f.status === 'pending' || f.status === 'under_review') || flags[0];

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-subtle">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">
            Reviewer Decision Console
          </h1>
          <p className="text-xs text-muted mt-1 font-medium">
            Assigned review workload, evidence ambiguity triage, and mandatory determination rationales.
          </p>
        </div>

        <Button
          onClick={() => navigate('/reviewer/queue')}
          variant="white"
          size="sm"
          leftIcon={<CheckSquare className="w-4 h-4" />}
          className="shrink-0 self-start sm:self-auto cursor-pointer font-semibold shadow-sm"
        >
          Triage Queue ({flags.length})
        </Button>
      </div>

      {/* ── Bento Grid ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* Left Column: Stats & The ONE Mint Highlighted Card (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-5">
          
          {/* Bento Stat Card 1: Split Stat (Pending & Resolved) */}
          <div className="bg-surface border border-subtle rounded-card p-5 shadow-card">
            <div className="grid grid-cols-2 divide-x divide-subtle">
              <div className="pr-4">
                <span className="text-3xl sm:text-4xl font-semibold text-warn tracking-tight block">
                  {pendingCount}
                </span>
                <span className="text-xs text-muted mt-1.5 font-medium block">
                  Pending Triage
                </span>
              </div>
              <div className="pl-4">
                <span className="text-3xl sm:text-4xl font-semibold text-success tracking-tight block">
                  {resolvedCount}
                </span>
                <span className="text-xs text-muted mt-1.5 font-medium block">
                  Signed Off
                </span>
              </div>
            </div>
          </div>

          {/* Bento Card 2: Specialist Profile & Authority */}
          <div className="bg-surface border border-subtle rounded-card p-5 shadow-card space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-subtle">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted">Reviewer Key Authority</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-pill bg-success-dim text-success border border-success/30 font-medium">
                Active Signer
              </span>
            </div>

            <div className="flex items-center gap-3 p-3 rounded-sm bg-elevated border border-subtle">
              <div className="w-10 h-10 rounded-pill bg-surface border border-subtle text-accent flex items-center justify-center font-semibold text-xs shrink-0">
                {user.full_name.split(' ').map((n) => n[0]).join('')}
              </div>
              <div className="min-w-0 flex-1">
                <span className="text-xs font-semibold text-ink block truncate">
                  {user.full_name}
                </span>
                <span className="text-[11px] text-muted font-mono block mt-0.5">
                  Human Oversight Specialist
                </span>
              </div>
            </div>
          </div>

          {/* ── THE ONE MINT HIGHLIGHTED CARD ── */}
          <div className="bg-accent-dim border border-accent/30 rounded-card p-5 shadow-card flex flex-col justify-between space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-accent uppercase tracking-wider flex items-center gap-1.5">
                <FileSearch className="w-3.5 h-3.5" />
                Priority Determination
              </span>
              <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-pill bg-accent/20 text-accent border border-accent/40">
                Action Required
              </span>
            </div>

            <div>
              <h3 className="text-base font-semibold text-ink leading-snug">
                {highPriorityFlag ? highPriorityFlag.criterion_name : 'No Pending Flags'}
              </h3>
              <p className="text-xs text-ink/90 mt-1.5 leading-relaxed">
                {highPriorityFlag
                  ? `Candidate ${highPriorityFlag.candidate_name} provided clarification. Adjudicate evidence in Decision Studio.`
                  : 'All flagged criteria have been verified with complete justification notes.'}
              </p>
            </div>

            <Button
              onClick={() => navigate(highPriorityFlag ? `/reviewer/case/${highPriorityFlag.id}` : '/reviewer/queue')}
              variant="primary"
              size="sm"
              rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
              className="w-full justify-between font-semibold"
            >
              <span>Open Decision Studio</span>
            </Button>
          </div>

        </div>

        {/* Right Column: Triage Queue & Audit Timeline (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col gap-5">
          
          {/* Active Triage Queue Panel */}
          <div className="bg-surface border border-subtle rounded-card shadow-card p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-subtle">
              <div>
                <h2 className="text-sm font-semibold text-ink">Active Review Cases</h2>
                <p className="text-xs text-muted font-medium mt-0.5">Escalated criteria awaiting human determination</p>
              </div>
              <Link
                to="/reviewer/queue"
                className="text-xs font-semibold text-muted hover:text-ink flex items-center gap-1 transition-colors"
              >
                <span>Full Queue ({flags.length})</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="space-y-2.5">
              {flags.slice(0, 4).map((f) => (
                <div
                  key={f.id}
                  onClick={() => navigate(`/reviewer/case/${f.id}`)}
                  className="p-4 rounded-sm bg-elevated hover:bg-elevated/80 border border-subtle cursor-pointer transition-colors flex items-center justify-between group"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-ink group-hover:text-accent transition-colors">
                        {f.criterion_name}
                      </span>
                      <StatusBadge status={f.status} size="sm" />
                    </div>
                    <p className="text-[11px] text-muted font-medium">
                      {f.candidate_name} • {f.job_title}
                    </p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted group-hover:text-accent transition-colors" />
                </div>
              ))}
            </div>
          </div>

          {/* Lower Bento Grid: Recent Decisions & Protocol Rules (6 cols each) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            
            {/* Recent Determinations Log */}
            <div className="bg-surface border border-subtle rounded-card p-5 shadow-card space-y-3.5">
              <div className="pb-2 border-b border-subtle">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Recent Determinations</h3>
                <p className="text-xs text-muted font-medium">Signed justification audits</p>
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="p-3.5 rounded-sm bg-elevated border border-subtle space-y-1.5">
                  <div className="flex justify-between items-center font-semibold text-ink">
                    <span>Marcus Vance</span>
                    <span className="text-success font-mono text-[10px]">VERIFIED_MET</span>
                  </div>
                  <p className="text-[11px] text-muted font-mono leading-relaxed">
                    "Verified Kafka cluster throughput on page 2 lines 18-24. Overrode AI unverified status."
                  </p>
                </div>

                <div className="p-3.5 rounded-sm bg-elevated border border-subtle space-y-1.5">
                  <div className="flex justify-between items-center font-semibold text-ink">
                    <span>Sarah Jenkins</span>
                    <span className="text-danger font-mono text-[10px]">UPHELD_REJECT</span>
                  </div>
                  <p className="text-[11px] text-muted font-mono leading-relaxed">
                    "Candidate lacks required 5+ years tenure in distributed consensus. Upheld not met."
                  </p>
                </div>
              </div>
            </div>

            {/* Protocol & Verification Standard */}
            <div className="bg-surface border border-subtle rounded-card p-5 shadow-card space-y-3.5">
              <div className="pb-2 border-b border-subtle">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Adjudication Standard</h3>
                <p className="text-xs text-muted font-medium">ClearHire Transparency Protocol</p>
              </div>

              <div className="space-y-2.5 text-xs text-muted">
                <div className="p-3 rounded-sm bg-elevated border border-subtle flex items-start gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                  <div>
                    <span className="text-xs font-semibold text-ink block">Mandatory Rationale</span>
                    <span className="text-[11px] leading-relaxed">
                      Every verdict requires an explicit 25-character rationale recorded to the audit ledger.
                    </span>
                  </div>
                </div>

                <div className="p-3 rounded-sm bg-elevated border border-subtle flex items-start gap-2.5">
                  <Clock className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                  <div>
                    <span className="text-xs font-semibold text-ink block">Candidate Due Process</span>
                    <span className="text-[11px] leading-relaxed">
                      No candidate can be disqualified without access to written reviewer findings.
                    </span>
                  </div>
                </div>
              </div>
            </div>

          </div>

        </div>

      </div>

    </div>
  );
};
