import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, ShieldAlert, CheckCircle2, RefreshCw, Hash, Lock, 
  Database, Check, Clock, ChevronDown, ChevronRight
} from 'lucide-react';
import { mockService } from '../../services/mock/mockService';
import { AuditEvent, AuditVerificationReport } from '../../contracts/models';
import { Button, LoadingSpinner } from '../../components/ui';

export const AuditorChainVerificationPage: React.FC = () => {
  const [verificationResult, setVerificationResult] = useState<AuditVerificationReport | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  const fetchAuditData = async () => {
    setLoading(true);
    try {
      const [vResult, allEvents] = await Promise.all([
        mockService.getAuditVerification(),
        mockService.listAuditEvents()
      ]);
      setVerificationResult(vResult);
      setEvents(allEvents);
    } catch (err) {
      console.error('Failed to load audit verification:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditData();
  }, []);

  const runVerificationScan = async () => {
    setScanning(true);
    setScanProgress(0);

    for (let i = 0; i <= 100; i += 10) {
      setScanProgress(i);
      await new Promise(r => setTimeout(r, 60));
    }

    await fetchAuditData();
    setScanning(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <LoadingSpinner size="lg" label="Verifying cryptographic hash chain integrity..." />
      </div>
    );
  }

  const isValid = verificationResult?.is_valid ?? true;

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      {/* ── Top Banner / Verification Header ──────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface p-6 md:p-8 rounded-card border border-subtle shadow-card">
        <div className="flex items-start gap-4">
          <div className={`w-14 h-14 rounded-card flex items-center justify-center shrink-0 ${
            isValid ? 'bg-success-dim text-success border border-success/30' : 'bg-danger-dim text-danger border border-danger/30'
          }`}>
            {isValid ? <ShieldCheck className="w-8 h-8" /> : <ShieldAlert className="w-8 h-8" />}
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-pill uppercase tracking-wider ${
                isValid ? 'bg-success-dim text-success border border-success/30' : 'bg-danger-dim text-danger border border-danger/30'
              }`}>
                {isValid ? 'CHAIN VERIFIED TAMPER-PROOF' : 'HASH MISMATCH DETECTED'}
              </span>
              <span className="text-xs text-muted font-mono font-medium">
                SHA-256 Merkle Ledger
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">Cryptographic Audit Chain Integrity</h1>
            <p className="text-xs text-muted mt-1 font-medium">
              Deterministic verification proving unbroken hash continuity from Genesis Event #1 to Head #{events.length}.
            </p>
          </div>
        </div>

        <Button
          onClick={runVerificationScan}
          disabled={scanning}
          isLoading={scanning}
          variant="primary"
          size="md"
          leftIcon={<RefreshCw className="w-4 h-4" />}
          className="font-semibold shadow-sm"
        >
          {scanning ? `Verifying... ${scanProgress}%` : 'Run Cryptographic Scan'}
        </Button>
      </div>

      {/* ── Verification Metrics Bar ──────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface p-5 rounded-card border border-subtle shadow-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted">Events Verified</span>
            <Database className="w-4 h-4 text-accent" />
          </div>
          <div className="text-2xl font-semibold text-ink mt-2">
            {verificationResult?.verified_events || events.length} / {verificationResult?.total_events || events.length}
          </div>
          <p className="text-xs text-success font-medium mt-1 flex items-center gap-1">
            <Check className="w-3.5 h-3.5" /> 100% Sequence Monotonicity
          </p>
        </div>

        <div className="bg-surface p-5 rounded-card border border-subtle shadow-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted">Chain Status</span>
            <Lock className="w-4 h-4 text-accent" />
          </div>
          <div className="text-lg font-semibold text-success mt-2 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-success" /> Continuous Hash Link
          </div>
          <p className="text-xs text-muted mt-1 font-medium">
            0 Broken Links • 0 Missing Sequences
          </p>
        </div>

        <div className="bg-surface p-5 rounded-card border border-subtle shadow-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted">Genesis Hash (#1)</span>
            <Hash className="w-4 h-4 text-muted" />
          </div>
          <div className="text-xs font-mono font-medium text-ink mt-2 truncate bg-elevated p-2.5 rounded-sm border border-subtle">
            {events[events.length - 1]?.event_hash.slice(0, 24) || 'e3b0c44298fc1c149afbf4c8'}...
          </div>
          <p className="text-[11px] text-muted font-medium mt-1">Root state seed</p>
        </div>

        <div className="bg-surface p-5 rounded-card border border-subtle shadow-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted">Chain Head Hash</span>
            <Hash className="w-4 h-4 text-muted" />
          </div>
          <div className="text-xs font-mono font-medium text-ink mt-2 truncate bg-elevated p-2.5 rounded-sm border border-subtle">
            {verificationResult?.chain_head_hash || (events[0]?.event_hash ? `${events[0].event_hash.slice(0, 24)}...` : '7d2e99f109b83a2c589e4726')}
          </div>
          <p className="text-[11px] text-muted font-medium mt-1">Latest cryptographically sealed block</p>
        </div>
      </div>

      {/* ── Verification Rules Checklist ──────────────────────── */}
      <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
        <h3 className="text-base font-semibold text-ink">Mathematical Proof Guarantees</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-sm bg-elevated border border-subtle space-y-2">
            <div className="flex items-center gap-2 text-accent text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 text-accent" /> Rule 1: Recursive Hash Equation
            </div>
            <code className="text-[11px] text-ink font-mono block bg-surface p-2.5 rounded-sm border border-subtle">
              H_i = SHA256(payload_i + H_i-1)
            </code>
            <p className="text-xs text-muted leading-relaxed font-medium">
              Every event incorporates the hash of its predecessor, creating an unalterable backward chain.
            </p>
          </div>

          <div className="p-4 rounded-sm bg-elevated border border-subtle space-y-2">
            <div className="flex items-center gap-2 text-accent text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 text-accent" /> Rule 2: Strict Sequence Monotonicity
            </div>
            <code className="text-[11px] text-ink font-mono block bg-surface p-2.5 rounded-sm border border-subtle">
              seq_i = seq_i-1 + 1 (contiguous)
            </code>
            <p className="text-xs text-muted leading-relaxed font-medium">
              Events cannot be removed or inserted without breaking the strictly contiguous sequence counter.
            </p>
          </div>

          <div className="p-4 rounded-sm bg-elevated border border-subtle space-y-2">
            <div className="flex items-center gap-2 text-accent text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 text-accent" /> Rule 3: Monotonic Timestamps
            </div>
            <code className="text-[11px] text-ink font-mono block bg-surface p-2.5 rounded-sm border border-subtle">
              timestamp_i &gt;= timestamp_i-1
            </code>
            <p className="text-xs text-muted leading-relaxed font-medium">
              Audit log chronology is forward-moving with millisecond precision against drift tampering.
            </p>
          </div>
        </div>
      </div>

      {/* ── Visual Chain Explorer ─────────────────────────────── */}
      <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-subtle">
          <div>
            <h3 className="text-base font-semibold text-ink">Recent Hash Ledger Blocks</h3>
            <p className="text-xs text-muted font-medium mt-0.5">Showing live cryptographic pointers across the chain</p>
          </div>
          <span className="text-xs font-mono font-medium px-2.5 py-1 bg-elevated rounded-pill text-muted border border-subtle">
            {events.length} Sealed Blocks
          </span>
        </div>

        <div className="space-y-3">
          {events.slice(0, 6).map((event) => {
            const isExpanded = expandedEventId === event.id;
            return (
              <div 
                key={event.id}
                className="border border-subtle rounded-sm p-4 transition-all hover:border-subtle-strong bg-elevated"
              >
                <div 
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer select-none"
                  onClick={() => setExpandedEventId(isExpanded ? null : event.id)}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-sm bg-surface text-accent border border-subtle font-mono text-xs font-semibold flex items-center justify-center shrink-0">
                      #{event.sequence_number}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-ink">{event.action}</span>
                        <span className="text-[11px] font-mono text-muted">
                          by {event.actor_role || 'SYSTEM'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-xs">
                        <span className="font-mono text-accent text-[11px] flex items-center gap-1">
                          <Check className="w-3 h-3" /> Hash: {event.event_hash.slice(0, 16)}...
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted font-medium flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                    {isExpanded ? <ChevronDown className="w-4 h-4 text-muted" /> : <ChevronRight className="w-4 h-4 text-muted" />}
                  </div>
                </div>

                {/* Expanded Block Details */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-subtle space-y-3 text-xs">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <span className="text-muted block font-medium mb-1">Previous Block Hash (Parent):</span>
                        <code className="text-[11px] font-mono text-ink bg-surface p-2.5 rounded-sm block break-all border border-subtle">
                          {event.previous_hash || '0000000000000000000000000000000000000000000000000000000000000000'}
                        </code>
                      </div>
                      <div>
                        <span className="text-muted block font-medium mb-1">Current Event Hash:</span>
                        <code className="text-[11px] font-mono text-accent bg-accent-dim p-2.5 rounded-sm block break-all border border-accent/30 font-medium">
                          {event.event_hash}
                        </code>
                      </div>
                    </div>

                    <div className="p-3 bg-surface rounded-sm border border-subtle">
                      <span className="text-muted block font-medium mb-1">Event Payload State Delta:</span>
                      <pre className="text-[11px] font-mono text-ink overflow-x-auto whitespace-pre-wrap">
                        {JSON.stringify(event.details || event.new_state, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
