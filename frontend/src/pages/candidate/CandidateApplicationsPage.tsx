import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
import { Application } from '../../contracts/models';
import { StatusBadge } from '../../components/ui/Badge';
import { Clock, FileCheck, ChevronRight } from 'lucide-react';

export const CandidateApplicationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<Application[]>([]);

  useEffect(() => {
    mockService.listApplications().then(setApplications);
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-6 select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="pb-3 border-b border-subtle">
        <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">My Submitted Applications</h1>
        <p className="text-xs text-muted mt-1 font-medium">
          Track the screening status and evidence evaluation for all your job submissions.
        </p>
      </div>

      <div className="bg-surface rounded-card p-6 border border-subtle shadow-card">
        {applications.length === 0 ? (
          <div className="text-center py-12 text-muted font-medium">
            <FileCheck className="w-10 h-10 mx-auto mb-2 opacity-40 text-muted" />
            <p className="text-sm">You haven't submitted any applications yet.</p>
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
                    <span>{app.department || 'Engineering'}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      Submitted on {new Date(app.submitted_at).toLocaleDateString()}
                    </span>
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
