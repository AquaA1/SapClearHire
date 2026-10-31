import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Briefcase,
  Users,
  CheckSquare,
  ShieldCheck,
  Settings,
  LogOut,
  FileCheck2,
} from 'lucide-react';
import { useAuth } from '../../stores/authStore';
import { UserRole } from '../../contracts/enums';

export const Sidebar: React.FC = () => {
  const { role, logout } = useAuth();
  const location = useLocation();

  const getNavLinks = () => {
    if (role === UserRole.CANDIDATE) return [
      { to: '/candidate/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
      { to: '/candidate/jobs',      icon: Briefcase,       label: 'Open Positions' },
      { to: '/candidate/applications', icon: FileCheck2,   label: 'Applications' },
    ];
    if (role === UserRole.REVIEWER) return [
      { to: '/reviewer/queue',      icon: CheckSquare,     label: 'Review Queue', badge: true },
    ];
    if (role === UserRole.SYSTEM_AUDITOR) return [
      { to: '/reviewer/queue',      icon: ShieldCheck,     label: 'Audit Queue', badge: true },
      { to: '/employer/applications', icon: Users,         label: 'Candidate Dossiers' },
      { to: '/employer/jobs',       icon: Briefcase,       label: 'Requisitions' },
    ];
    return [
      { to: '/employer/dashboard',  icon: LayoutDashboard, label: 'Dashboard' },
      { to: '/employer/jobs',       icon: Briefcase,       label: 'Requisitions' },
      { to: '/employer/applications', icon: Users,         label: 'Candidates', badge: true },
      { to: '/employer/reviews',      icon: CheckSquare,     label: 'Review Triage' },
    ];
  };

  const navLinks = getNavLinks();

  return (
    <aside
      className="shrink-0 h-screen sticky top-0 z-30 flex flex-col items-center justify-between py-5 select-none"
      style={{ width: 'var(--sidebar-w)', backgroundColor: 'var(--sidebar)', borderRight: '1px solid var(--border)' }}
    >
      {/* Brand mark */}
      <div className="flex flex-col items-center gap-6">
        <div
          className="w-9 h-9 rounded-card flex items-center justify-center font-semibold text-sm cursor-pointer"
          style={{ backgroundColor: 'var(--accent)', color: 'var(--canvas)' }}
          title="ClearHire"
        >
          CH
        </div>

        {/* Nav items */}
        <nav className="flex flex-col items-center gap-1">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname.startsWith(link.to);
            return (
              <NavLink
                key={link.to}
                to={link.to}
                title={link.label}
                className="relative w-11 h-11 rounded-xl flex items-center justify-center transition-all group cursor-pointer"
                style={isActive
                  ? { backgroundColor: 'var(--elevated)', color: 'var(--ink)' }
                  : { color: 'var(--muted)' }
                }
              >
                {/* Active left bar */}
                {isActive && (
                  <span
                    className="absolute -left-px top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full"
                    style={{ backgroundColor: 'var(--accent)' }}
                  />
                )}
                <Icon className="w-[18px] h-[18px] transition-colors group-hover:text-ink" />
                {/* Badge dot */}
                {link.badge && (
                  <span
                    className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full"
                    style={{ backgroundColor: 'var(--accent)' }}
                  />
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Bottom: Settings + Logout */}
      <div className="flex flex-col items-center gap-1">
        <button
          className="w-11 h-11 rounded-xl flex items-center justify-center transition-colors cursor-pointer"
          style={{ color: 'var(--muted)' }}
          title="Settings"
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--ink)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--muted)')}
        >
          <Settings className="w-[18px] h-[18px]" />
        </button>
        <button
          onClick={logout}
          className="w-11 h-11 rounded-xl flex items-center justify-center transition-colors cursor-pointer"
          style={{ color: 'var(--muted)' }}
          title="Sign Out"
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--danger)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--muted)')}
        >
          <LogOut className="w-[18px] h-[18px]" />
        </button>
      </div>
    </aside>
  );
};
