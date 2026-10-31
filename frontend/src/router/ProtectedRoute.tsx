import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../stores/authStore';
import { UserRole } from '../contracts/enums';

interface ProtectedRouteProps {
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles }) => {
  const { isAuthenticated, role, isInitializing } = useAuth();
  const location = useLocation();

  // Display minimal branded spinner while restoring JWT session from localStorage
  if (isInitializing) {
    return (
      <div className="min-h-screen w-full bg-canvas flex flex-col items-center justify-center p-4 select-none">
        <div className="w-8 h-8 rounded-full border-2 border-subtle border-t-accent animate-spin" />
        <span className="text-xs text-muted mt-3 font-medium">
          Verifying session...
        </span>
      </div>
    );
  }

  // Not authenticated: redirect to /login with state to allow return
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Authenticated, but role does not match requirements for this section
  if (allowedRoles && role && !allowedRoles.includes(role)) {
    return <Navigate to="/403" replace />;
  }

  // Authorized: render child routes
  return <Outlet />;
};
