import React from 'react';

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'md', className = '', label }) => {
  const sizeClass = { sm: 'w-4 h-4 border-2', md: 'w-6 h-6 border-2', lg: 'w-8 h-8 border-2' }[size];
  return (
    <div className={`flex flex-col items-center justify-center gap-2 ${className}`}>
      <div className={`${sizeClass} border-subtle border-t-accent rounded-full animate-spin`} role="status" aria-label={label || 'Loading'} />
      {label && <p className="text-xs text-muted">{label}</p>}
    </div>
  );
};
