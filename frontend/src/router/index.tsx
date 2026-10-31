import React from 'react';
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { DashboardLayout } from '../layouts/DashboardLayout';

// Public Pages
import { LandingPage } from '../pages/public/LandingPage';
import { LoginPage } from '../pages/public/LoginPage';
import { RegisterPage } from '../pages/public/RegisterPage';
import { AccessDeniedPage } from '../pages/public/AccessDeniedPage';
import { NotFoundPage } from '../pages/public/NotFoundPage';

// Candidate Pages
import { CandidateDashboardPage } from '../pages/candidate/CandidateDashboardPage';
import { CandidateJobsPage } from '../pages/candidate/CandidateJobsPage';
import { CandidateJobDetailPage } from '../pages/candidate/CandidateJobDetailPage';
import { CandidateApplicationsPage } from '../pages/candidate/CandidateApplicationsPage';
import { CandidateApplicationDetailPage } from '../pages/candidate/CandidateApplicationDetailPage';

// Employer Pages
import { EmployerDashboardPage } from '../pages/employer/EmployerDashboardPage';
import { EmployerJobsPage } from '../pages/employer/EmployerJobsPage';
import { EmployerApplicationDetailPage } from '../pages/employer/EmployerApplicationDetailPage';

// Reviewer Pages
import { ReviewerQueuePage } from '../pages/reviewer/ReviewerQueuePage';
import { ReviewCaseDetailPage } from '../pages/reviewer/ReviewCaseDetailPage';

export const router = createBrowserRouter([
  // Public Root Routes
  {
    path: '/',
    element: <LandingPage />
  },
  {
    path: '/login',
    element: <LoginPage />
  },
  {
    path: '/register',
    element: <RegisterPage />
  },
  {
    path: '/403',
    element: <AccessDeniedPage />
  },

  // Authenticated Portal Routes wrapped in DashboardLayout
  {
    element: <DashboardLayout />,
    children: [
      // Candidate Routes
      {
        path: '/candidate/dashboard',
        element: <CandidateDashboardPage />
      },
      {
        path: '/candidate/jobs',
        element: <CandidateJobsPage />
      },
      {
        path: '/candidate/jobs/:jobId',
        element: <CandidateJobDetailPage />
      },
      {
        path: '/candidate/applications',
        element: <CandidateApplicationsPage />
      },
      {
        path: '/candidate/applications/:id',
        element: <CandidateApplicationDetailPage />
      },
      {
        path: '/candidate/profile',
        element: <Navigate to="/candidate/dashboard" replace />
      },

      // Employer Routes
      {
        path: '/employer/dashboard',
        element: <EmployerDashboardPage />
      },
      {
        path: '/employer/jobs',
        element: <EmployerJobsPage />
      },
      {
        path: '/employer/jobs/new',
        element: <Navigate to="/employer/jobs" replace />
      },
      {
        path: '/employer/jobs/:jobId',
        element: <Navigate to="/employer/jobs" replace />
      },
      {
        path: '/employer/applications',
        element: <Navigate to="/employer/applications/app-001" replace />
      },
      {
        path: '/employer/applications/:id',
        element: <EmployerApplicationDetailPage />
      },

      // Reviewer Routes
      {
        path: '/reviewer/dashboard',
        element: <Navigate to="/reviewer/queue" replace />
      },
      {
        path: '/reviewer/queue',
        element: <ReviewerQueuePage />
      },
      {
        path: '/reviewer/case/:caseId',
        element: <ReviewCaseDetailPage />
      },

      // Auditor & Benchmark Graceful Redirects
      {
        path: '/auditor/chain',
        element: <Navigate to="/reviewer/queue" replace />
      },
      {
        path: '/auditor/events',
        element: <Navigate to="/reviewer/queue" replace />
      },
      {
        path: '/auditor/dashboard',
        element: <Navigate to="/reviewer/queue" replace />
      },
      {
        path: '/auditor/*',
        element: <Navigate to="/reviewer/queue" replace />
      },
      {
        path: '/benchmark',
        element: <Navigate to="/employer/jobs" replace />
      }
    ]
  },

  // 404 Catch-All
  {
    path: '*',
    element: <NotFoundPage />
  }
]);
