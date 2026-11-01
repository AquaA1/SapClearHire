import React, { useState } from 'react';
import { X, HelpCircle, FileText, MessageSquareQuote, ShieldCheck } from 'lucide-react';
import { Button } from '../ui/Button';
import { CriterionEvaluationItem } from '../../contracts/models';

interface EmployerClarificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (question: string) => Promise<void>;
  item: CriterionEvaluationItem;
  isFurtherClarification?: boolean;
}

export const EmployerClarificationModal: React.FC<EmployerClarificationModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  item,
  isFurtherClarification = false,
}) => {
  const [question, setQuestion] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = question.trim();
    if (clean.length < 10) {
      setError('Please provide a specific, detailed clarification question (at least 10 characters).');
      return;
    }
    setError('');
    setIsSubmitting(true);
    try {
      await onSubmit(clean);
      setQuestion('');
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to submit clarification request.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface border border-subtle rounded-card shadow-modal max-w-lg w-full p-6 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-subtle pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-warn-dim text-warn">
                <HelpCircle className="w-4 h-4" />
              </span>
              <h3 className="text-sm font-semibold text-ink">
                {isFurtherClarification ? 'Request Further Clarification' : 'Request Candidate Clarification'}
              </h3>
            </div>
            <p className="text-xs text-muted mt-1 font-medium">
              Target Criterion: <span className="text-ink font-semibold">{item.criterion_name}</span>
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="text-muted hover:text-ink cursor-pointer p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Grounding & Evidence Reference */}
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between text-muted">
            <span className="font-semibold uppercase tracking-wider text-[10px]">
              AI Assessment: <span className="capitalize font-semibold text-ink">{item.status.replace('_', ' ')}</span>
            </span>
            {item.source_page && (
              <span className="flex items-center gap-1 text-[10px] text-muted font-medium bg-elevated px-2 py-0.5 rounded border border-subtle">
                <FileText className="w-3 h-3" /> Page {item.source_page}
              </span>
            )}
          </div>

          {item.source_excerpt ? (
            <div className="bg-elevated border border-subtle rounded p-3 text-xs">
              <div className="flex items-center gap-1.5 text-muted mb-1 text-[11px] font-medium">
                <MessageSquareQuote className="w-3.5 h-3.5 text-accent shrink-0" />
                <span>Resume Evidence Excerpt:</span>
              </div>
              <p className="italic font-mono text-ink text-[11px] leading-relaxed">
                "{item.source_excerpt}"
              </p>
            </div>
          ) : (
            <div className="bg-elevated/50 border border-dashed border-subtle rounded p-2.5 text-center text-[11px] text-muted italic">
              No direct resume excerpt available for this requirement.
            </div>
          )}
        </div>

        {/* Question Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs font-semibold text-ink">
                Clarification Question for Candidate <span className="text-danger">*</span>
              </label>
              <span
                className={`text-[10px] font-medium ${
                  question.trim().length >= 10 ? 'text-accent' : 'text-muted'
                }`}
              >
                {question.trim().length}/10 min characters
              </span>
            </div>
            <textarea
              rows={4}
              value={question}
              onChange={(e) => {
                setQuestion(e.target.value);
                if (error) setError('');
              }}
              placeholder="e.g. Your resume mentions that you created a REST API using Python. Could you clarify whether you used FastAPI or another framework? If possible, explain which parts of the project you implemented."
              className={`w-full text-xs p-3 rounded-sm border ${
                error ? 'border-danger bg-danger-dim/30' : 'border-subtle bg-elevated'
              } text-ink placeholder:text-muted focus:outline-none focus:border-accent font-medium leading-relaxed`}
              required
            />
            {error && <p className="text-xs text-danger mt-1 font-medium">{error}</p>}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-subtle">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              disabled={isSubmitting || question.trim().length < 10}
              leftIcon={<ShieldCheck className="w-3.5 h-3.5" />}
              className="font-semibold"
            >
              Send Clarification Request
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
