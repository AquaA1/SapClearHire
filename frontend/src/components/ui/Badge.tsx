import React from 'react';
import {
  EvidenceStatus,
  VerificationState,
  ApplicationStatus,
  ReviewFlagStatus,
} from '../../contracts/enums';

export interface StatusBadgeProps {
  status: EvidenceStatus | VerificationState | ApplicationStatus | ReviewFlagStatus | string;
  size?: 'sm' | 'md';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  className = '',
}) => {
  const norm = String(status).toLowerCase();
  let dotCls = 'bg-muted';
  let pillCls = 'bg-elevated text-ink border-subtle font-medium';
  let label = String(status).replace(/_/g, ' ');

  if (norm === VerificationState.HUMAN_VERIFIED || norm === 'human_verified') {
    dotCls  = 'bg-success';
    pillCls = 'bg-success-dim text-success border-success/30 font-semibold';
    label   = 'Human Verified';
  } else if (norm === VerificationState.HUMAN_REJECTED || norm === 'human_rejected') {
    dotCls  = 'bg-danger';
    pillCls = 'bg-danger-dim text-danger border-danger/30 font-semibold';
    label   = 'Human Rejected';
  } else if (norm === VerificationState.CANDIDATE_CLARIFIED || norm === 'candidate_clarified' || norm === 'clarified') {
    dotCls  = 'bg-accent';
    pillCls = 'bg-accent-dim text-accent border-accent/30 font-semibold';
    label   = 'Clarification Under Review';
  } else if (norm === 'awaiting_candidate_response' || norm === 'awaiting_clarification') {
    dotCls  = 'bg-warn';
    pillCls = 'bg-warn-dim text-warn border-warn/30 font-semibold';
    label   = 'Awaiting Candidate Response';
  } else if (norm === EvidenceStatus.SUPPORTED || norm === 'supported' || norm === 'evidence_supported') {
    dotCls  = 'bg-success';
    pillCls = 'bg-success-dim text-success border-success/30 font-medium';
    label   = 'Evidence Supported';
  } else if (norm === EvidenceStatus.PARTIALLY_SUPPORTED || norm === 'partially_supported') {
    dotCls  = 'bg-amber-500';
    pillCls = 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30 font-medium';
    label   = 'Partially Supported';
  } else if (norm === 'active' || norm === 'resolved') {
    dotCls  = 'bg-success';
    pillCls = 'bg-success-dim text-success border-success/30 font-medium';
    label   = norm === 'active' ? 'Active' : 'Resolved';
  } else if (norm === 'pending' || norm === 'under_review') {
    dotCls  = 'bg-pending';
    pillCls = 'bg-pending-dim text-pending border-pending/30 font-medium';
    label   = norm === 'pending' ? 'Pending' : 'Under Review';
  } else if (
    norm === EvidenceStatus.AMBIGUOUS ||
    norm === 'ambiguous' ||
    norm === 'needs_review' ||
    norm === 'warning'
  ) {
    dotCls  = 'bg-warn';
    pillCls = 'bg-warn-dim text-warn border-warn/30 font-medium';
    label   = norm === 'needs_review' ? 'Needs Review' : 'Ambiguous Evidence';
  } else if (
    norm === EvidenceStatus.NOT_FOUND ||
    norm === 'not_found' ||
    norm === 'rejected' ||
    norm === 'failed'
  ) {
    dotCls  = 'bg-danger';
    pillCls = 'bg-danger-dim text-danger border-danger/30 font-medium';
    label   = norm === 'not_found' ? 'Not Found in Evidence' : 'Rejected';
  } else if (norm === 'screening' || norm === 'reviewed') {
    dotCls  = 'bg-success';
    pillCls = 'bg-success-dim text-success border-success/30 font-medium';
    label   = norm === 'reviewed' ? 'Reviewed' : 'Screening';
  } else if (norm === 'info') {
    dotCls  = 'bg-info';
    pillCls = 'bg-info-dim text-info border-info/30 font-medium';
    label   = 'Information';
  } else if (norm === 'unverified') {
    dotCls  = 'bg-muted';
    pillCls = 'bg-elevated text-muted border-subtle font-medium';
    label   = 'Awaiting Human Review';
  } else {
    // Submitted or default state
    dotCls  = 'bg-muted';
    pillCls = 'bg-elevated text-ink/90 border-subtle font-medium';
    label   = label.toUpperCase();
  }

  const sizeClass = size === 'sm' ? 'px-2.5 py-0.5 text-[10px]' : 'px-3 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-pill border tracking-wide uppercase ${sizeClass} ${pillCls} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotCls}`} />
      {label}
    </span>
  );
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'info' | 'pending' | 'warn' | 'danger' | 'accent' | 'outline';
  size?: 'sm' | 'md';
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'default',
  size = 'md',
  dot = false,
  children,
  className = '',
  ...props
}) => {
  const sizeClass = size === 'sm' ? 'px-2.5 py-0.5 text-[10px]' : 'px-3 py-1 text-xs';

  const variantClass: Record<string, string> = {
    default: 'bg-elevated text-ink border-subtle',
    success: 'bg-success-dim text-success border-success/30 font-medium',
    info:    'bg-info-dim text-info border-info/30 font-medium',
    pending: 'bg-pending-dim text-pending border-pending/30 font-medium',
    warn:    'bg-warn-dim text-warn border-warn/30 font-medium',
    danger:  'bg-danger-dim text-danger border-danger/30 font-medium',
    accent:  'bg-accent-dim text-accent border-accent/30 font-medium',
    outline: 'bg-transparent text-ink border-subtle font-medium',
  };

  const dotClass: Record<string, string> = {
    default: 'bg-muted',
    success: 'bg-success',
    info:    'bg-info',
    pending: 'bg-pending',
    warn:    'bg-warn',
    danger:  'bg-danger',
    accent:  'bg-accent',
    outline: 'bg-muted',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-pill border tracking-wide ${sizeClass} ${variantClass[variant]} ${className}`}
      {...props}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotClass[variant]}`} />}
      {children}
    </span>
  );
};
