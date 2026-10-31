import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, ArrowLeft, LogOut } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { UserRole } from '../../contracts/enums';
import { Button } from '../../components/ui';

export const AccessDeniedPage: React.FC = () => {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleReturnToDashboard = () => {
    if (user?.role === UserRole.CANDIDATE) navigate('/candidate/dashboard');
    else if (user?.role === UserRole.EMPLOYER_ADMIN) navigate('/employer/dashboard');
    else if (user?.role === UserRole.REVIEWER || user?.role === UserRole.SYSTEM_AUDITOR) navigate('/reviewer/queue');
    else navigate('/login');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-6 select-none">
      <div className="bg-surface rounded-card border border-subtle p-8 max-w-md w-full text-center shadow-card space-y-6">
        <div className="w-14 h-14 rounded-card bg-danger-dim border border-danger/30 text-danger flex items-center justify-center mx-auto">
          <ShieldAlert className="w-7 h-7" />
        </div>

        <div>
          <span className="text-[11px] font-semibold text-danger uppercase tracking-wider">
            HTTP 403 • FORBIDDEN
          </span>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink mt-1">Access Restricted</h1>
          <p className="text-xs text-muted mt-2 leading-relaxed font-medium">
            Your current authenticated account (<strong className="text-ink">{user?.role ? user.role.replace('_', ' ') : 'Guest'}</strong>) does not have authorization to view this endpoint or resource.
          </p>
        </div>

        <div className="space-y-3 pt-2">
          <Button
            onClick={handleReturnToDashboard}
            variant="primary"
            size="md"
            leftIcon={<ArrowLeft className="w-4 h-4" />}
            className="w-full justify-center font-semibold"
          >
            Return to My Console
          </Button>

          <Button
            onClick={handleLogout}
            variant="secondary"
            size="md"
            leftIcon={<LogOut className="w-4 h-4" />}
            className="w-full justify-center font-semibold"
          >
            Sign Out to Switch Accounts
          </Button>
        </div>
      </div>
    </div>
  );
};
