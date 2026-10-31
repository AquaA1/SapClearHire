import React from 'react';
import { CriterionEvaluationItem } from '../../contracts/models';
import { StatusBadge } from '../ui/Badge';
import { FileText, MessageSquareQuote, HelpCircle, ArrowUpRight } from 'lucide-react';
import { EvidenceStatus } from '../../contracts/enums';

interface CriterionEvidenceCardProps {
  item: CriterionEvaluationItem;
  onClarify?: (criterionId: string) => void;
  showClarifyButton?: boolean;
}

export const CriterionEvidenceCard: React.FC<CriterionEvidenceCardProps> = ({
  item,
  onClarify,
  showClarifyButton = false,
}) => {
  const isAmbiguousOrMissing =
    item.status === EvidenceStatus.AMBIGUOUS || item.status === EvidenceStatus.NOT_FOUND;

  return (
    <div className="bg-surface rounded-card p-5 border border-subtle shadow-card hover:border-subtle-strong transition-all">
      {/* Top Header: Criterion Name, Category, Status */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span
              className={`text-[10px] font-medium px-2 py-0.5 rounded-sm uppercase tracking-wider ${
                item.category === 'required'
                  ? 'bg-accent-dim text-accent border border-accent/20'
                  : 'bg-elevated text-muted border border-subtle'
              }`}
            >
              {item.category}
            </span>
            <h4 className="text-sm font-semibold text-ink tracking-tight">{item.criterion_name}</h4>
          </div>
          <p className="text-xs text-muted leading-relaxed">{item.plain_language_explanation}</p>
        </div>

        <div className="shrink-0">
          <StatusBadge status={item.verification_state || item.status} />
        </div>
      </div>

      {/* Source Excerpt / Grounding Box */}
      {item.source_excerpt ? (
        <div className="mt-3 bg-elevated border border-subtle rounded-sm p-3.5 text-xs relative group">
          <div className="flex items-center justify-between mb-1.5 text-[11px] font-medium text-muted">
            <span className="flex items-center gap-1.5 text-ink font-medium">
              <MessageSquareQuote className="w-3.5 h-3.5 text-accent" />
              Verbatim Resume Evidence
            </span>
            {item.source_page && (
              <span className="flex items-center gap-1 px-2 py-0.5 bg-surface border border-subtle rounded text-[10px] text-muted font-mono">
                <FileText className="w-3 h-3 text-muted" />
                Page {item.source_page}
              </span>
            )}
          </div>
          <p className="text-ink italic font-mono text-[11px] leading-relaxed">
            "{item.source_excerpt}"
          </p>
        </div>
      ) : (
        <div className="mt-3 bg-elevated/50 border border-dashed border-subtle rounded-sm p-3 text-xs text-muted italic">
          No explicit matching citation found in resume text.
        </div>
      )}

      {/* Clarification Trigger Button */}
      {showClarifyButton && isAmbiguousOrMissing && onClarify && (
        <div className="mt-3 pt-3 border-t border-subtle flex items-center justify-between">
          <span className="text-[11px] text-warn flex items-center gap-1">
            <HelpCircle className="w-3.5 h-3.5" />
            Think this is incorrect?
          </span>
          <button
            onClick={() => onClarify(item.criterion_id)}
            className="inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline cursor-pointer"
          >
            <span>Contest with clarification</span>
            <ArrowUpRight className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
};
