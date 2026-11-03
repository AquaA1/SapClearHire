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
      <div className="bg-surface border border-subtle rounded-card shadow-modal max-w-xl w-full p-6 sm:p-7 space-y-5">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-subtle pb-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="p-1.5 rounded bg-warn-dim text-warn">
                <HelpCircle className="w-5 h-5" />
              </span>
              <h3 className="text-xl sm:text-2xl font-bold text-ink">
                {isFurtherClarification ? 'Request Further Clarification' : 'Request Candidate Clarification'}
              </h3>
            </div>
            <p className="text-sm sm:text-base text-ink-secondary mt-1 font-medium">
              Target Criterion: <span className="text-ink font-semibold">{item.criterion_name}</span>
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="text-ink-secondary hover:text-ink cursor-pointer p-1.5 rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Grounding & Evidence Reference */}
        <div className="space-y-2.5 text-sm">
          <div className="flex items-center justify-between text-ink-secondary font-medium">
            <span className="font-semibold uppercase tracking-wider text-xs">
              AI Assessment: <span className="capitalize font-semibold text-ink">{item.status.replace('_', ' ')}</span>
            </span>
            {item.source_page && (
              <span className="flex items-center gap-1 text-xs text-ink-secondary font-medium">
                <FileText className="w-3.5 h-3.5 text-muted shrink-0" /> Page {item.source_page}
              </span>
            )}
          </div>

          {item.source_excerpt ? (
            <div className="bg-elevated border border-subtle rounded-md p-3.5 space-y-1.5">
              <div className="flex items-center gap-2 text-ink-secondary text-xs font-semibold">
                <MessageSquareQuote className="w-4 h-4 text-accent shrink-0" />
                <span>Resume Evidence Excerpt:</span>
              </div>
              <p className="italic text-ink text-sm sm:text-base leading-relaxed">
                "{item.source_excerpt}"
              </p>
            </div>
          ) : (
            <div className="bg-elevated/50 border border-dashed border-subtle rounded-md p-3 text-center text-sm text-ink-secondary italic">
              No direct resume excerpt available for this requirement.
            </div>
          )}
        </div>

        {/* Question Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-sm sm:text-base font-semibold text-ink">
                Clarification Question for Candidate <span className="text-danger">*</span>
              </label>
              <span
                className={`text-xs font-medium ${
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
              className={`w-full text-base p-4 rounded-md border ${
                error ? 'border-danger bg-danger-dim/30' : 'border-subtle bg-elevated'
              } text-ink placeholder:text-muted focus:outline-none focus:border-accent font-normal leading-relaxed`}
              required
            />
            {error && <p className="text-xs sm:text-sm text-danger mt-1.5 font-medium">{error}</p>}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-subtle">
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isSubmitting}
              disabled={isSubmitting || question.trim().length < 10}
              leftIcon={<ShieldCheck className="w-4 h-4" />}
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
