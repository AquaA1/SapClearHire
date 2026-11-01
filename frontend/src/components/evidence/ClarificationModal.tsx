import React, { useState } from 'react';
import { X, Upload, MessageSquare } from 'lucide-react';
import { Button } from '../ui/Button';

interface ClarificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (statement: string, documentId?: string) => Promise<void>;
  criterionName?: string;
}

export const ClarificationModal: React.FC<ClarificationModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  criterionName = 'Requirement',
}) => {
  const [statement, setStatement] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!statement.trim()) return;
    setIsSubmitting(true);
    try {
      await onSubmit(statement);
      setStatement('');
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/75 backdrop-blur-xs" onClick={onClose} />
      <div className="relative z-10 w-full max-w-xl bg-surface border border-subtle rounded-card shadow-modal overflow-hidden p-6 sm:p-7 space-y-5">
        <div className="flex items-start justify-between border-b border-subtle pb-4">
          <div>
            <h3 className="text-lg sm:text-[19px] font-semibold text-ink tracking-tight">Submit Evidence Clarification</h3>
            <p className="text-[14px] text-muted mt-1 leading-relaxed">
              Contesting qualification: <span className="text-ink font-semibold">{criterionName}</span>
            </p>
          </div>
          <button onClick={onClose} className="text-muted hover:text-ink cursor-pointer p-1.5 rounded transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <label className="block text-[13px] font-semibold text-ink uppercase tracking-wider">
              Explanatory Clarification Statement
            </label>
            <textarea
              rows={5}
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
              placeholder="Cite your specific experience, projects, or repository commits that verify this criterion..."
              className="w-full bg-elevated border border-subtle rounded-sm p-4 text-[15px] text-ink placeholder:text-muted focus:border-accent focus:outline-none transition-colors leading-[1.6]"
              required
            />
            <p className="text-xs text-muted">
              Provide factual, grounded details. Your statement will be permanently recorded in the auditable review dossier.
            </p>
          </div>

          <div className="p-4 bg-elevated/60 border border-dashed border-subtle rounded-sm flex items-center gap-3.5">
            <Upload className="w-5 h-5 text-muted shrink-0" />
            <div className="text-xs sm:text-[13px] text-muted">
              <span>Supplementary documentation or certification link (optional)</span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button type="button" variant="ghost" size="md" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="md" isLoading={isSubmitting}>
              Submit Clarification
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
