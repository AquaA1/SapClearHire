import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'white';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', isLoading, leftIcon, rightIcon, children, className = '', disabled, ...props }, ref) => {
    const sizeClass = {
      sm: 'h-8 px-4 text-xs gap-1.5',
      md: 'h-10 px-5 text-sm gap-2',
      lg: 'h-12 px-6 text-base gap-2',
    }[size];

    const variantClass = {
      primary:   'bg-accent text-canvas font-medium hover:opacity-90 active:opacity-80',
      secondary: 'bg-elevated text-ink border border-subtle hover:border-subtle-strong hover:bg-surface',
      ghost:     'bg-transparent text-muted hover:text-ink hover:bg-elevated',
      danger:    'bg-danger-dim text-danger border border-danger/25 hover:bg-danger/20',
      white:     'bg-ink text-canvas font-medium hover:opacity-90 active:opacity-80',
    }[variant];

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`inline-flex items-center justify-center rounded-pill font-medium transition-all duration-150 outline-none focus-visible:ring-2 focus-visible:ring-accent/40 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer select-none ${sizeClass} ${variantClass} ${className}`}
        {...props}
      >
        {isLoading ? (
          <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        ) : leftIcon ? (
          <span className="shrink-0">{leftIcon}</span>
        ) : null}
        <span>{children}</span>
        {!isLoading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);
Button.displayName = 'Button';
