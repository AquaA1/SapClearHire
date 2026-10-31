import React from 'react';
import { Search, Bell, SlidersHorizontal, Shield } from 'lucide-react';
import { useAuth } from '../../stores/authStore';
import { UserRole } from '../../contracts/enums';
import { useNavigate } from 'react-router-dom';

export const TopNavbar: React.FC = () => {
  const { user, role } = useAuth();
  const navigate = useNavigate();

  const formattedDate = new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  }).format(new Date());

  const getPrimaryActionLabel = () => {
    if (role === UserRole.EMPLOYER_ADMIN) return '+ Manage requisitions';
    if (role === UserRole.CANDIDATE) return 'Browse jobs';
    if (role === UserRole.REVIEWER) return 'Triage queue';
    if (role === UserRole.SYSTEM_AUDITOR) return 'Audit queue';
    return 'Browse jobs';
  };

  const handlePrimaryAction = () => {
    if (role === UserRole.EMPLOYER_ADMIN) navigate('/employer/jobs');
    else if (role === UserRole.CANDIDATE) navigate('/candidate/jobs');
    else if (role === UserRole.REVIEWER || role === UserRole.SYSTEM_AUDITOR) navigate('/reviewer/queue');
    else navigate('/candidate/jobs');
  };

  return (
    <header className="h-16 bg-canvas px-6 md:px-8 flex items-center justify-between sticky top-0 z-20 select-none border-b border-subtle">
      {/* Left: Date & Context Header with seamless alignment */}
      <div className="flex items-center gap-3">
        <div className="flex flex-col justify-center">
          <div className="flex items-center gap-2 text-[11px] text-muted font-medium leading-none">
            <span>{formattedDate}</span>
            <span className="text-muted/60">•</span>
            <span className="flex items-center gap-1.5 text-accent font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
              Ledger Active
            </span>
          </div>
          <div className="text-sm font-semibold text-ink tracking-tight flex items-center gap-1.5 mt-1 leading-tight">
            <span>ClearHire</span>
            <span className="text-muted/60 font-normal">•</span>
            <span className="text-xs font-medium text-ink/90 capitalize">
              {(role || UserRole.CANDIDATE).replace('_', ' ')} Console
            </span>
          </div>
        </div>
      </div>

      {/* Center: Search pill with filter sliders icon */}
      <div className="relative w-72 md:w-80 lg:w-96 hidden md:flex items-center">
        <Search className="w-3.5 h-3.5 text-muted absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input
          type="text"
          placeholder="Search candidates, criteria, hashes..."
          className="w-full h-9 bg-surface border border-subtle pl-9 pr-9 rounded-pill text-xs text-ink placeholder:text-muted focus:outline-none focus:border-subtle-strong transition-all font-medium"
        />
        <button
          className="w-7 h-7 absolute right-1 top-1/2 -translate-y-1/2 rounded-full flex items-center justify-center text-muted hover:text-ink transition-colors cursor-pointer"
          title="Filter options"
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Right: Role Badge, Notification, Profile, Action Button (all matching h-9) */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        {/* Authenticated Role Badge */}
        <div className="hidden sm:flex items-center gap-1.5 h-9 bg-surface border border-subtle px-3 rounded-pill text-xs">
          <Shield className="w-3.5 h-3.5 text-accent shrink-0" />
          <span className="text-xs font-semibold text-ink capitalize">
            {(role || UserRole.CANDIDATE).replace('_', ' ')}
          </span>
        </div>

        {/* Notifications Icon Button */}
        <button
          className="w-9 h-9 rounded-full bg-surface border border-subtle text-ink/80 hover:text-ink flex items-center justify-center relative transition-colors cursor-pointer shrink-0"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="w-1.5 h-1.5 rounded-full bg-accent absolute top-2 right-2" />
        </button>

        {/* User Profile Info */}
        <div className="flex items-center gap-2 pl-0.5">
          <div className="w-9 h-9 rounded-full bg-elevated border border-subtle text-ink flex items-center justify-center font-semibold text-xs shrink-0">
            {user?.full_name
              ? user.full_name
                  .split(' ')
                  .map((n) => n[0])
                  .join('')
              : 'U'}
          </div>
          <div className="text-left hidden xl:block">
            <span className="block text-xs font-semibold text-ink leading-tight truncate max-w-[120px]">
              {user?.full_name || 'ClearHire User'}
            </span>
            <span className="text-[10px] text-muted font-medium capitalize block mt-0.5">
              {(role || UserRole.CANDIDATE).replace('_', ' ')}
            </span>
          </div>
        </div>

        {/* Primary Action Button */}
        <button
          onClick={handlePrimaryAction}
          className="hidden sm:flex items-center gap-1.5 h-9 px-4 bg-accent hover:bg-accent-secondary text-canvas text-xs font-semibold rounded-pill transition-all cursor-pointer shadow-sm shrink-0"
        >
          <span>{getPrimaryActionLabel()}</span>
        </button>
      </div>
    </header>
  );
};
