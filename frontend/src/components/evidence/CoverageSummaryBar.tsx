import React from 'react';
import { EvidenceCoverageSummary } from '../../contracts/models';
import { ShieldCheck } from 'lucide-react';

interface CoverageSummaryBarProps {
  coverage: EvidenceCoverageSummary;
}

export const CoverageSummaryBar: React.FC<CoverageSummaryBarProps> = ({ coverage }) => {
  const supportedPercent = Math.round((coverage.supported_count / coverage.total_criteria) * 100) || 0;
  const ambiguousPercent = Math.round((coverage.ambiguous_count / coverage.total_criteria) * 100) || 0;
  const notFoundPercent = Math.round((coverage.not_found_count / coverage.total_criteria) * 100) || 0;

  return (
    <div className="bg-surface rounded-card p-4 sm:p-4.5 border border-subtle shadow-card space-y-2.5">
      {/* Top Header: Title & Inline Counts Summary */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 sm:w-5 sm:h-5 text-accent shrink-0" />
          <h3 className="font-bold text-ink text-base tracking-tight">
            Factual Evidence Coverage
          </h3>
        </div>

        {/* Compact inline summary */}
        <div className="flex items-center gap-1.5 text-xs sm:text-sm font-medium flex-wrap">
          <span className="text-success font-semibold">
            {coverage.supported_count} supported
          </span>
          <span className="text-muted/50 select-none">·</span>
          <span className="text-warn font-semibold">
            {coverage.ambiguous_count} ambiguous
          </span>
          <span className="text-muted/50 select-none">·</span>
          <span className="text-danger font-semibold">
            {coverage.not_found_count} missing
          </span>
        </div>
      </div>

      {/* Segmented Progress Bar */}
      <div className="w-full h-2 rounded-pill bg-elevated overflow-hidden flex my-2">
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
          title={`Missing: ${notFoundPercent}%`}
        />
      </div>

      {/* Bottom Metrics: Criteria Evaluated & Percentage Grounded */}
      <div className="flex items-center justify-between text-xs text-muted font-medium">
        <span>Criteria Evaluated: {coverage.total_criteria} Total</span>
        <span className="font-bold text-ink text-xs sm:text-sm">{supportedPercent}% Grounded</span>
      </div>
    </div>
  );
};
