import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
import { Application } from '../../contracts/models';
import { StatusBadge } from '../../components/ui/Badge';
import {
  Filter,
  Mail,
  Calendar,
  ChevronRight,
  Printer,
  Download,
  ExternalLink,
} from 'lucide-react';
import { Button } from '../../components/ui';

export const EmployerApplicationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  useEffect(() => {
    mockService.listApplications().then(setApplications);
  }, []);

  const toggleSelect = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 select-none">
      {/* ── Top Header ────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface p-6 rounded-card border border-subtle shadow-card">
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">
            {applications.length} Candidates
          </h1>
          <span className="text-xs font-medium px-2.5 py-0.5 rounded-pill bg-success-dim text-success border border-success/30">
            Active Roster
          </span>
        </div>

        {/* Selected counter and actions */}
        <div className="flex items-center gap-2">
          {selectedIds.length > 0 && (
            <span className="text-xs font-semibold text-canvas px-3 py-1 bg-accent rounded-pill">
              {selectedIds.length} Selected
            </span>
          )}

          <button
            className="w-9 h-9 rounded-pill border border-subtle bg-elevated text-muted hover:text-ink flex items-center justify-center transition-colors cursor-pointer"
            title="Export candidates"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Candidate Cards Grid ──────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
        {applications.map((app) => {
          const isSelected = selectedIds.includes(app.id);

          return (
            <div
              key={app.id}
              onClick={() => navigate(`/employer/applications/${app.id}`)}
              className={`bg-surface rounded-card p-5 border transition-all cursor-pointer relative flex flex-col justify-between hover:border-subtle-strong shadow-card group space-y-4 ${
                isSelected
                  ? 'border-accent ring-1 ring-accent'
                  : 'border-subtle'
              }`}
            >
              <div>
                {/* Card Top: Checkbox & Status Pill */}
                <div className="flex items-center justify-between mb-3.5">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={(e) => toggleSelect(app.id, e as any)}
                    className="w-4 h-4 rounded-sm border-subtle bg-elevated text-accent focus:ring-0 cursor-pointer accent-accent"
                  />
                  <StatusBadge status={app.status} size="sm" />
                </div>

                {/* Candidate Info with Avatar */}
                <div className="flex items-center gap-3 mb-3.5">
                  <div className="w-10 h-10 rounded-pill bg-elevated border border-subtle text-accent font-semibold flex items-center justify-center text-xs shrink-0">
                    {app.candidate_name
                      ?.split(' ')
                      .map((n) => n[0])
                      .join('') || 'C'}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-semibold text-ink text-sm truncate group-hover:text-accent transition-colors">
                      {app.candidate_name || 'Candidate'}
                    </h3>
                    <p className="text-xs text-muted font-medium truncate mt-0.5">
                      {app.job_title}
                    </p>
                  </div>
                </div>

                {/* Details Box */}
                <div className="p-3 rounded-sm bg-elevated border border-subtle space-y-1.5 text-xs">
                  <div className="flex items-center gap-2 text-muted font-medium truncate">
                    <Mail className="w-3.5 h-3.5 text-muted shrink-0" />
                    <span className="truncate">{app.candidate_email || 'candidate@example.com'}</span>
                  </div>
                  <div className="flex items-center gap-2 text-muted font-medium">
                    <Calendar className="w-3.5 h-3.5 text-muted shrink-0" />
                    <span>Applied {new Date(app.submitted_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}</span>
                  </div>
                </div>
              </div>

              {/* Bottom Quick Action */}
              <div className="pt-3 border-t border-subtle flex justify-between items-center text-xs">
                <span className="text-[11px] font-mono text-muted">Ref #{app.id.slice(0, 8)}</span>
                <span className="text-accent font-semibold flex items-center gap-1 group-hover:underline">
                  <span>Dossier</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
