import React from 'react';
import { EvidenceCoverageSummary } from '../../contracts/models';
import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck } from 'lucide-react';

interface CoverageSummaryBarProps {
  coverage: EvidenceCoverageSummary;
}

export const CoverageSummaryBar: React.FC<CoverageSummaryBarProps> = ({ coverage }) => {
  const supportedPercent = Math.round((coverage.supported_count / coverage.total_criteria) * 100) || 0;
  const ambiguousPercent = Math.round((coverage.ambiguous_count / coverage.total_criteria) * 100) || 0;
  const notFoundPercent = Math.round((coverage.not_found_count / coverage.total_criteria) * 100) || 0;

  return (
    <div className="bg-surface rounded-card p-6 border border-subtle shadow-card mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-accent" />
            <h3 className="font-semibold text-ink text-base tracking-tight">Factual Evidence Coverage</h3>
          </div>
          <p className="text-xs text-muted mt-0.5">
            ClearHire maps structured claims directly to versioned criteria. No opaque AI scoring.
          </p>
        </div>

        {/* Counts summary pills */}
        <div className="flex items-center gap-2 flex-wrap text-xs font-medium">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-pill bg-success-dim text-success border border-success/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{coverage.supported_count} Supported</span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1 rounded-pill bg-warn-dim text-warn border border-warn/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>{coverage.ambiguous_count} Ambiguous</span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1 rounded-pill bg-danger-dim text-danger border border-danger/20">
            <XCircle className="w-3.5 h-3.5" />
            <span>{coverage.not_found_count} Not Found</span>
          </div>
        </div>
      </div>

      {/* Segmented Progress Bar */}
      <div className="w-full h-2.5 rounded-pill bg-elevated overflow-hidden flex mb-3">
        <div
          style={{ width: `${supportedPercent}%` }}
          className="bg-success h-full transition-all duration-500"
          title={`Supported: ${supportedPercent}%`}
        />
        <div
          style={{ width: `${ambiguousPercent}%` }}
          className="bg-warn h-full transition-all duration-500"
          title={`Ambiguous: ${ambiguousPercent}%`}
        />
        <div
          style={{ width: `${notFoundPercent}%` }}
          className="bg-danger h-full transition-all duration-500"
          title={`Not Found: ${notFoundPercent}%`}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-muted">
        <span>Criteria Evaluated: {coverage.total_criteria} Total</span>
        <span className="font-semibold text-ink">{supportedPercent}% Grounded</span>
      </div>
    </div>
  );
};
