import React from 'react';
import { useAuth } from '../../stores/authStore';
import { UserRole } from '../../contracts/enums';

const formatRole = (role?: UserRole | string | null): string => {
  if (!role) return 'Candidate';
  switch (role) {
    case UserRole.EMPLOYER_ADMIN:
      return 'Employer';
    case UserRole.REVIEWER:
      return 'Reviewer';
    case UserRole.SYSTEM_AUDITOR:
      return 'Auditor';
    case UserRole.CANDIDATE:
    default:
      return 'Candidate';
  }
};

export const TopNavbar: React.FC = () => {
  const { user, role } = useAuth();

  return (
    <header
      className="h-[68px] bg-canvas px-8 md:px-10 flex items-center justify-between sticky top-0 z-20 select-none shrink-0 border-b border-subtle"
      style={{ backgroundColor: 'var(--canvas)', borderBottomColor: 'var(--border)' }}
    >
      {/* Left: Branding & Role Identity */}
      <div className="flex items-center gap-4 shrink-0 whitespace-nowrap">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center font-extrabold text-xs tracking-wider shrink-0 select-none"
            style={{ backgroundColor: 'var(--accent)', color: 'var(--canvas)' }}
          >
            CH
          </div>
          <span className="text-lg font-bold text-ink tracking-tight whitespace-nowrap">ClearHire</span>
        </div>
        <span className="text-muted/40 font-light select-none text-base">/</span>
        <span className="text-sm font-semibold text-accent capitalize whitespace-nowrap">
          {formatRole(role)} Console
        </span>
      </div>

      {/* Right: User Profile Identity */}
      <div className="flex items-center gap-3.5 shrink-0 whitespace-nowrap">
        <div className="text-right hidden sm:block">
          <span className="block text-sm font-semibold text-ink leading-tight truncate max-w-[180px] whitespace-nowrap">
            {user?.full_name || 'ClearHire User'}
          </span>
          <span className="text-xs text-muted font-medium capitalize block mt-0.5 whitespace-nowrap">
            {formatRole(role)}
          </span>
        </div>
        <div
          className="w-9 h-9 rounded-full bg-surface border border-subtle text-ink font-bold text-xs flex items-center justify-center shrink-0"
          title={user?.full_name || 'User Profile'}
        >
          {user?.full_name
            ? user.full_name
                .split(' ')
                .map((n) => n[0])
                .slice(0, 2)
                .join('')
            : 'U'}
        </div>
      </div>
    </header>
  );
};

