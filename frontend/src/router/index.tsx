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
import { CandidateProfilePage } from '../pages/candidate/CandidateProfilePage';

// Employer Pages
import { EmployerDashboardPage } from '../pages/employer/EmployerDashboardPage';
import { EmployerJobsPage } from '../pages/employer/EmployerJobsPage';
import { EmployerJobCreatePage } from '../pages/employer/EmployerJobCreatePage';
import { EmployerJobDetailPage } from '../pages/employer/EmployerJobDetailPage';
import { EmployerApplicationsPage } from '../pages/employer/EmployerApplicationsPage';
import { EmployerApplicationDetailPage } from '../pages/employer/EmployerApplicationDetailPage';

// Reviewer Pages
import { ReviewerDashboardPage } from '../pages/reviewer/ReviewerDashboardPage';
import { ReviewerQueuePage } from '../pages/reviewer/ReviewerQueuePage';
import { ReviewCaseDetailPage } from '../pages/reviewer/ReviewCaseDetailPage';

// Auditor Pages
import { AuditorChainVerificationPage } from '../pages/auditor/AuditorChainVerificationPage';
import { AuditorEventsPage } from '../pages/auditor/AuditorEventsPage';

// Benchmark Page
import { BenchmarkExplorerPage } from '../pages/benchmark/BenchmarkExplorerPage';

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
        element: <CandidateProfilePage />
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
        element: <EmployerJobCreatePage />
      },
      {
        path: '/employer/jobs/:jobId',
        element: <EmployerJobDetailPage />
      },
      {
        path: '/employer/applications',
        element: <EmployerApplicationsPage />
      },
      {
        path: '/employer/applications/:id',
        element: <EmployerApplicationDetailPage />
      },

      // Reviewer Routes
      {
        path: '/reviewer/dashboard',
        element: <ReviewerDashboardPage />
      },
      {
        path: '/reviewer/queue',
        element: <ReviewerQueuePage />
      },
      {
        path: '/reviewer/case/:caseId',
        element: <ReviewCaseDetailPage />
      },

      // Auditor Routes
      {
        path: '/auditor/chain',
        element: <AuditorChainVerificationPage />
      },
      {
        path: '/auditor/events',
        element: <AuditorEventsPage />
      },
      {
        path: '/auditor/dashboard',
        element: <Navigate to="/auditor/chain" replace />
      },

      // Benchmark / Simulation Explorer
      {
        path: '/benchmark',
        element: <BenchmarkExplorerPage />
      }
    ]
  },

  // 404 Catch-All
  {
    path: '*',
    element: <NotFoundPage />
  }
]);
