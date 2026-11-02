import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { applicationService } from '../../services/api/applicationService';
import { Application } from '../../contracts/models';
import { StatusBadge } from '../../components/ui/Badge';
import { Clock, FileCheck, ChevronRight, Briefcase } from 'lucide-react';
import { Button, LoadingSpinner } from '../../components/ui';
import { useAuthStore } from '../../stores/authStore';

export const CandidateApplicationsPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchApplications = async () => {
      setLoading(true);
      try {
        const apps = await applicationService.listApplications();
        setApplications(apps);
      } catch (err) {
        console.error('Failed to load applications:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchApplications();
  }, [user?.id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" label="Loading submitted applications..." />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8 select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-subtle">
        <div>
          <h1 className="text-3xl sm:text-4xl font-bold text-ink tracking-tight">
            My Submitted Applications
          </h1>
          <p className="text-sm sm:text-base text-ink-secondary mt-1.5 font-medium leading-relaxed">
            Track the screening status and evidence evaluation for all your job submissions.
          </p>
        </div>

        <Button
          onClick={() => navigate('/candidate/jobs')}
          variant="secondary"
          size="md"
          leftIcon={<Briefcase className="w-4 h-4" />}
          className="self-start sm:self-auto font-semibold"
        >
          Explore Positions
        </Button>
      </div>

      <div className="bg-surface rounded-card p-6 border border-subtle shadow-card">
        {applications.length === 0 ? (
          <div className="text-center py-16 text-muted font-medium space-y-3.5">
            <FileCheck className="w-14 h-14 mx-auto opacity-40 text-muted" />
            <div className="space-y-1.5">
              <h3 className="text-base sm:text-lg font-bold text-ink">No Submitted Applications</h3>
              <p className="text-xs sm:text-sm text-muted max-w-sm mx-auto leading-relaxed">
                You haven't submitted any applications yet. Browse open positions and apply with your resume to see transparent screening results.
              </p>
            </div>
            <Button
              onClick={() => navigate('/candidate/jobs')}
              variant="primary"
              size="md"
              className="mt-3 font-bold"
            >
              Browse Open Positions
            </Button>
          </div>
        ) : (
          <div className="space-y-3.5">
            {applications.map((app) => (
              <div
                key={app.id}
                onClick={() => navigate(`/candidate/applications/${app.id}`)}
                className="p-5 sm:p-6 rounded-card border border-subtle bg-elevated hover:bg-elevated/80 transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
              >
                <div>
                  <h3 className="text-base sm:text-lg font-bold text-ink group-hover:text-accent transition-colors">
                    {app.job_title}
                  </h3>
                  <div className="flex items-center gap-3 text-xs sm:text-sm text-muted font-medium mt-1.5">
                    <span className="font-semibold text-ink/80">{app.department || 'General'}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-4 h-4" />
                      Submitted on{' '}
                      {new Date(app.submitted_at || app.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </span>
                    <span>•</span>
                    <span className="text-xs font-mono text-muted">ID: #{app.id.slice(0, 8)}</span>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <StatusBadge status={app.status} size="sm" />
                  <span className="text-sm sm:text-base font-bold text-accent flex items-center gap-1.5 group-hover:underline">
                    <span>Inspect Evidence</span>
                    <ChevronRight className="w-4 h-4" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
