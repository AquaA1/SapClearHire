import React from 'react';
import { Search, Bell, SlidersHorizontal, Shield } from 'lucide-react';
import { useAuth } from '../../stores/authStore';
import { UserRole } from '../../contracts/enums';
import { useNavigate } from 'react-router-dom';

export const TopNavbar: React.FC = () => {
  const { user, role, switchRole } = useAuth();
  const navigate = useNavigate();

  const handleRoleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newRole = e.target.value as UserRole;
    switchRole(newRole);
    if (newRole === UserRole.CANDIDATE) navigate('/candidate/dashboard');
    else if (newRole === UserRole.EMPLOYER_ADMIN) navigate('/employer/dashboard');
    else if (newRole === UserRole.REVIEWER) navigate('/reviewer/queue');
    else if (newRole === UserRole.SYSTEM_AUDITOR) navigate('/reviewer/queue');
  };

  const getPrimaryActionLabel = () => {
    if (role === UserRole.EMPLOYER_ADMIN) return '+ Manage requisitions';
    if (role === UserRole.CANDIDATE) return 'Browse jobs';
    if (role === UserRole.REVIEWER) return 'Triage queue';
    return 'Review queue';
  };

  const handlePrimaryAction = () => {
    if (role === UserRole.EMPLOYER_ADMIN) navigate('/employer/jobs');
    else if (role === UserRole.CANDIDATE) navigate('/candidate/jobs');
    else if (role === UserRole.REVIEWER) navigate('/reviewer/queue');
    else navigate('/reviewer/queue');
  };

  return (
    <header className="h-20 bg-canvas px-6 md:px-8 flex items-center justify-between sticky top-0 z-20 select-none border-b border-subtle">
      {/* Left: Date & Context Header matching reference */}
      <div className="flex flex-col">
        <div className="flex items-center gap-2 text-xs text-muted font-medium">
          <span>Friday, 31 Oct</span>
          <span className="text-muted/60">•</span>
          <span className="flex items-center gap-1.5 text-accent text-xs font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            Ledger Active
          </span>
        </div>
        <div className="text-lg font-semibold text-ink tracking-tight flex items-center gap-2 mt-0.5">
          <span>ClearHire</span>
          <span className="text-muted/60 text-sm font-normal">•</span>
          <span className="text-sm font-medium text-ink/90 capitalize">
            {role.replace('_', ' ')} Console
          </span>
        </div>
      </div>

      {/* Center: Search pill with filter sliders icon */}
      <div className="relative w-72 md:w-96 hidden md:block">
        <Search className="w-4 h-4 text-muted absolute left-4 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          placeholder="Search candidates, criteria, hashes..."
          className="w-full bg-surface border border-subtle pl-10 pr-10 py-2 rounded-pill text-xs text-ink placeholder:text-muted/80 focus:outline-none focus:border-subtle-strong transition-all font-medium"
        />
        <button
          className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted hover:text-ink cursor-pointer"
          title="Filter options"
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Right: Role Switcher, Notification, Profile, Action Button */}
      <div className="flex items-center gap-3">
        {/* Persona Switcher */}
        <div className="flex items-center gap-1.5 bg-surface border border-subtle px-3.5 py-1.5 rounded-pill text-xs">
          <Shield className="w-3.5 h-3.5 text-accent" />
          <select
            value={role}
            onChange={handleRoleChange}
            className="text-xs font-semibold text-ink bg-transparent border-none focus:outline-none cursor-pointer pr-1"
          >
            <option value={UserRole.EMPLOYER_ADMIN} className="bg-surface text-ink">Employer Admin</option>
            <option value={UserRole.REVIEWER} className="bg-surface text-ink">Reviewer</option>
            <option value={UserRole.CANDIDATE} className="bg-surface text-ink">Candidate</option>
            <option value={UserRole.SYSTEM_AUDITOR} className="bg-surface text-ink">System Auditor</option>
          </select>
        </div>

        {/* Notifications Icon Button */}
        <button
          className="w-9 h-9 rounded-full bg-surface border border-subtle text-ink/80 hover:text-ink flex items-center justify-center relative transition-colors cursor-pointer"
          title="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="w-1.5 h-1.5 rounded-full bg-accent absolute top-2.5 right-2.5" />
        </button>

        {/* User Profile Info */}
        <div className="flex items-center gap-2.5 pl-1">
          <div className="w-9 h-9 rounded-full bg-elevated border border-subtle text-ink flex items-center justify-center font-semibold text-xs">
            {user.full_name
              .split(' ')
              .map((n) => n[0])
              .join('')}
          </div>
          <div className="text-left hidden xl:block">
            <span className="block text-xs font-semibold text-ink leading-tight">
              {user.full_name}
            </span>
            <span className="text-[10px] text-muted font-medium capitalize">
              {role.replace('_', ' ')}
            </span>
          </div>
        </div>

        {/* Primary Action Button */}
        <button
          onClick={handlePrimaryAction}
          className="hidden sm:flex items-center gap-1.5 px-4 py-2 bg-accent hover:bg-accent-secondary text-canvas text-xs font-semibold rounded-pill transition-all cursor-pointer shadow-sm"
        >
          <span>{getPrimaryActionLabel()}</span>
        </button>
      </div>
    </header>
  );
};
