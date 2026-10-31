import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, ArrowLeft } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { UserRole } from '../../contracts/enums';
import { Button } from '../../components/ui';

export const AccessDeniedPage: React.FC = () => {
  const { user, switchRole } = useAuthStore();
  const navigate = useNavigate();

  const handleSwitchAndRedirect = (role: UserRole) => {
    switchRole(role);
    if (role === UserRole.CANDIDATE) navigate('/candidate/dashboard');
    else if (role === UserRole.EMPLOYER_ADMIN) navigate('/employer/dashboard');
    else if (role === UserRole.REVIEWER) navigate('/reviewer/dashboard');
    else if (role === UserRole.SYSTEM_AUDITOR) navigate('/auditor/chain');
  };

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-6 select-none">
      <div className="bg-surface rounded-card border border-subtle p-8 max-w-md w-full text-center shadow-card space-y-6">
        <div className="w-14 h-14 rounded-card bg-danger-dim border border-danger/30 text-danger flex items-center justify-center mx-auto">
          <ShieldAlert className="w-7 h-7" />
        </div>

        <div>
          <span className="text-[11px] font-mono font-semibold text-danger uppercase tracking-wider">
            HTTP 403 • FORBIDDEN
          </span>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink mt-1">Access Restricted</h1>
          <p className="text-xs text-muted mt-2 leading-relaxed font-medium">
            Your current authenticated persona (<strong className="text-ink">{user?.role}</strong>) does not have authorization to view this endpoint or resource.
          </p>
        </div>

        {/* Switch Persona Shortcuts */}
        <div className="p-4 bg-elevated rounded-card border border-subtle text-left space-y-2.5">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted block">
            Quick Persona Switch
          </span>
          <div className="grid grid-cols-2 gap-2">
            {[
              { role: UserRole.EMPLOYER_ADMIN, label: 'Employer Admin' },
              { role: UserRole.REVIEWER, label: 'Reviewer' },
              { role: UserRole.SYSTEM_AUDITOR, label: 'System Auditor' },
              { role: UserRole.CANDIDATE, label: 'Candidate' },
            ].map(({ role, label }) => (
              <button
                key={role}
                onClick={() => handleSwitchAndRedirect(role)}
                className="px-3 py-2 bg-surface hover:bg-elevated/80 rounded-pill border border-subtle text-xs font-semibold text-ink transition-colors cursor-pointer"
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex justify-center">
          <Button
            onClick={() => navigate('/login')}
            variant="primary"
            size="md"
            leftIcon={<ArrowLeft className="w-4 h-4" />}
            className="w-full justify-center font-semibold"
          >
            Return to Login
          </Button>
        </div>
      </div>
    </div>
  );
};
