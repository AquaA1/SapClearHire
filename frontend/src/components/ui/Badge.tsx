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

  if (
    norm === EvidenceStatus.SUPPORTED ||
    norm === VerificationState.HUMAN_VERIFIED ||
    norm === 'active' ||
    norm === 'resolved'
  ) {
    dotCls  = 'bg-success';
    pillCls = 'bg-success-dim text-success border-success/30 font-medium';
    label   = norm === 'active' ? 'Active' : norm === 'resolved' ? 'Resolved' : norm === 'supported' ? 'Supported' : 'Verified';
  } else if (
    norm === EvidenceStatus.AMBIGUOUS ||
    norm === 'needs_review' ||
    norm === 'under_review' ||
    norm === 'pending'
  ) {
    dotCls  = 'bg-warn';
    pillCls = 'bg-warn-dim text-warn border-warn/30 font-medium';
    label   = norm === 'ambiguous' ? 'Ambiguous' : norm === 'pending' ? 'Pending' : norm === 'under_review' ? 'Under Review' : 'Needs Review';
  } else if (
    norm === EvidenceStatus.NOT_FOUND ||
    norm === VerificationState.HUMAN_REJECTED
  ) {
    dotCls  = 'bg-danger';
    pillCls = 'bg-danger-dim text-danger border-danger/30 font-medium';
    label   = norm === 'not_found' ? 'Not Found' : 'Rejected';
  } else if (norm === VerificationState.CANDIDATE_CLARIFIED) {
    dotCls  = 'bg-accent';
    pillCls = 'bg-accent-dim text-accent border-accent/30 font-medium';
    label   = 'Clarified';
  } else if (norm === 'screening' || norm === 'reviewed') {
    dotCls  = 'bg-success';
    pillCls = 'bg-success-dim text-success border-success/30 font-medium';
    label   = norm === 'reviewed' ? 'Reviewed' : 'Screening';
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
  variant?: 'default' | 'success' | 'warn' | 'danger' | 'accent' | 'outline';
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
    warn:    'bg-warn-dim text-warn border-warn/30 font-medium',
    danger:  'bg-danger-dim text-danger border-danger/30 font-medium',
    accent:  'bg-accent-dim text-accent border-accent/30 font-medium',
    outline: 'bg-transparent text-ink border-subtle font-medium',
  };

  const dotClass: Record<string, string> = {
    default: 'bg-muted',
    success: 'bg-success',
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
