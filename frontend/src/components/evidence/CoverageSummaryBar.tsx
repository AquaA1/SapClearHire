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
    <div className="bg-surface rounded-card p-6 sm:p-7 border border-subtle shadow-card mb-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-accent shrink-0" />
            <h3 className="font-semibold text-ink text-lg sm:text-[19px] tracking-tight leading-[1.3]">
              Factual Evidence Coverage
            </h3>
          </div>
          <p className="text-[14px] text-muted mt-1 leading-[1.6]">
            ClearHire maps structured claims directly to versioned criteria. No opaque AI scoring.
          </p>
        </div>

        {/* Counts summary pills */}
        <div className="flex items-center gap-2.5 flex-wrap text-xs sm:text-[13px] font-medium">
          <div className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-pill bg-success-dim text-success border border-success/30">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{coverage.supported_count} Supported</span>
          </div>

          <div className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-pill bg-warn-dim text-warn border border-warn/30">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{coverage.ambiguous_count} Ambiguous</span>
          </div>

          <div className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-pill bg-danger-dim text-danger border border-danger/30">
            <XCircle className="w-4 h-4 shrink-0" />
            <span>{coverage.not_found_count} Not Found</span>
          </div>
        </div>
      </div>

      {/* Segmented Progress Bar */}
      <div className="w-full h-3 rounded-pill bg-elevated overflow-hidden flex mb-3">
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

      <div className="flex items-center justify-between text-xs sm:text-[13px] text-muted">
        <span>Criteria Evaluated: {coverage.total_criteria} Total</span>
        <span className="font-semibold text-ink">{supportedPercent}% Grounded</span>
      </div>
    </div>
  );
};
