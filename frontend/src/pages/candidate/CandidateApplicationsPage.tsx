import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { applicationService } from '../../services/api/applicationService';
import { Application } from '../../contracts/models';
import { StatusBadge } from '../../components/ui/Badge';
import { Clock, FileCheck, ChevronRight, Briefcase } from 'lucide-react';
import { Button, LoadingSpinner } from '../../components/ui';

export const CandidateApplicationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchApplications = async () => {
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
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" label="Loading submitted applications..." />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-subtle">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">
            My Submitted Applications
          </h1>
          <p className="text-xs text-muted mt-1 font-medium">
            Track the screening status and evidence evaluation for all your job submissions.
          </p>
        </div>

        <Button
          onClick={() => navigate('/candidate/jobs')}
          variant="secondary"
          size="sm"
          leftIcon={<Briefcase className="w-4 h-4" />}
          className="self-start sm:self-auto font-medium"
        >
          Explore Positions
        </Button>
      </div>

      <div className="bg-surface rounded-card p-6 border border-subtle shadow-card">
        {applications.length === 0 ? (
          <div className="text-center py-16 text-muted font-medium space-y-3">
            <FileCheck className="w-12 h-12 mx-auto opacity-40 text-muted" />
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-ink">No Submitted Applications</h3>
              <p className="text-xs text-muted max-w-sm mx-auto">
                You haven't submitted any applications yet. Browse open positions and apply with your resume to see transparent screening results.
              </p>
            </div>
            <Button
              onClick={() => navigate('/candidate/jobs')}
              variant="primary"
              size="sm"
              className="mt-2"
            >
              Browse Open Positions
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {applications.map((app) => (
              <div
                key={app.id}
                onClick={() => navigate(`/candidate/applications/${app.id}`)}
                className="p-5 rounded-sm border border-subtle bg-elevated hover:bg-elevated/80 transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
              >
                <div>
                  <h3 className="text-sm font-semibold text-ink group-hover:text-accent transition-colors">
                    {app.job_title}
                  </h3>
                  <div className="flex items-center gap-3 text-xs text-muted font-medium mt-1">
                    <span>{app.department || 'General'}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      Submitted on{' '}
                      {new Date(app.submitted_at || app.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </span>
                    <span>•</span>
                    <span className="text-[11px] text-muted">ID: #{app.id.slice(0, 8)}</span>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <StatusBadge status={app.status} />
                  <span className="text-xs font-semibold text-accent flex items-center gap-1 group-hover:underline">
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
