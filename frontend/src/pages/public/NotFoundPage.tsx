import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Home, ArrowLeft } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { UserRole } from '../../contracts/enums';
import { Button } from '../../components/ui';

export const NotFoundPage: React.FC = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const getHomeRoute = () => {
    if (!user) return '/';
    switch (user.role) {
      case UserRole.CANDIDATE:
        return '/candidate/dashboard';
      case UserRole.EMPLOYER_ADMIN:
        return '/employer/dashboard';
      case UserRole.REVIEWER:
        return '/reviewer/queue';
      case UserRole.SYSTEM_AUDITOR:
        return '/reviewer/queue';
      default:
        return '/';
    }
  };

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-6 select-none">
      <div className="bg-surface rounded-card border border-subtle p-8 max-w-md w-full text-center shadow-card space-y-6">
        <div className="w-14 h-14 rounded-card bg-warn-dim border border-warn/30 text-warn flex items-center justify-center mx-auto">
          <AlertCircle className="w-7 h-7" />
        </div>

        <div>
          <span className="text-[11px] font-semibold text-warn uppercase tracking-wider">
            HTTP 404 • NOT FOUND
          </span>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink mt-1">Page Not Located</h1>
          <p className="text-xs text-muted mt-2 leading-relaxed font-medium">
            The page or resource you requested does not exist or has been relocated to another route.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <Button
            onClick={() => navigate(getHomeRoute())}
            variant="primary"
            size="md"
            leftIcon={<Home className="w-4 h-4" />}
            className="flex-1 justify-center font-semibold"
          >
            Go to Console
          </Button>
          <Button
            onClick={() => navigate('/')}
            variant="secondary"
            size="md"
            className="justify-center"
          >
            Landing
          </Button>
        </div>
      </div>
    </div>
  );
};
