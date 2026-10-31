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
      <div className="fixed inset-0 bg-black/75" onClick={onClose} />
      <div className="relative z-10 w-full max-w-lg bg-surface border border-subtle rounded-card shadow-modal overflow-hidden p-6 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-base font-semibold text-ink">Submit Evidence Clarification</h3>
            <p className="text-xs text-muted mt-0.5">Contesting qualification: <span className="text-ink font-medium">{criterionName}</span></p>
          </div>
          <button onClick={onClose} className="text-muted hover:text-ink cursor-pointer p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted">Explanatory Clarification Statement</label>
            <textarea
              rows={4}
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
              placeholder="Cite your specific experience, projects, or repository commits that verify this criterion..."
              className="w-full bg-elevated border border-subtle rounded-sm p-3 text-xs text-ink placeholder:text-muted focus:border-accent focus:outline-none transition-colors"
              required
            />
          </div>

          <div className="p-3 bg-elevated/50 border border-dashed border-subtle rounded-sm flex items-center gap-3">
            <Upload className="w-4 h-4 text-muted shrink-0" />
            <div className="text-xs text-muted">
              <span>Supplementary documentation or cert (optional)</span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
              Submit Clarification
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
