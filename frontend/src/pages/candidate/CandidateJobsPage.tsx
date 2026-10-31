import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
import { Job } from '../../contracts/models';
import { Search, Briefcase, ChevronRight, Layers } from 'lucide-react';
import { Button } from '../../components/ui';

export const CandidateJobsPage: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('all');

  useEffect(() => {
    mockService.listJobs().then(setJobs);
  }, []);

  const filteredJobs = jobs.filter((job) => {
    const matchesSearch =
      job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (job.description && job.description.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesDept = departmentFilter === 'all' || job.department === departmentFilter;
    return matchesSearch && matchesDept;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="pb-3 border-b border-subtle">
        <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">Active Requisitions</h1>
        <p className="text-xs text-muted mt-1 font-medium">
          Transparent criteria definitions. Know exactly what each role requires before applying.
        </p>
      </div>

      {/* ── Filter and Search Bar ──────────────────────────────── */}
      <div className="bg-surface p-4 rounded-card border border-subtle shadow-card flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-muted absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by role title or skill..."
            className="w-full bg-elevated border border-subtle pl-10 pr-4 py-2 rounded-pill text-xs text-ink placeholder:text-muted focus:outline-none focus:border-subtle-strong transition-all font-medium"
          />
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          <span className="text-xs font-semibold text-muted">Department:</span>
          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="text-xs font-semibold text-ink bg-elevated border border-subtle px-3.5 py-2 rounded-pill focus:outline-none cursor-pointer"
          >
            <option value="all" className="bg-surface text-ink">All Departments</option>
            <option value="Core Infrastructure" className="bg-surface text-ink">Core Infrastructure</option>
            <option value="Product Design" className="bg-surface text-ink">Product Design</option>
          </select>
        </div>
      </div>

      {/* ── Job Card Grid ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {filteredJobs.map((job) => (
          <div
            key={job.id}
            onClick={() => navigate(`/candidate/jobs/${job.id}`)}
            className="bg-surface rounded-card p-6 border border-subtle hover:border-subtle-strong shadow-card transition-all cursor-pointer flex flex-col justify-between group space-y-4"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-medium px-2.5 py-0.5 rounded-pill bg-elevated text-muted border border-subtle">
                  {job.department}
                </span>
                <span className="text-[10px] text-success font-medium bg-success-dim px-2.5 py-0.5 rounded-pill border border-success/30">
                  Active
                </span>
              </div>

              <h2 className="text-base font-semibold text-ink group-hover:text-accent transition-colors">
                {job.title}
              </h2>

              <p className="text-xs text-muted mt-2 line-clamp-2 leading-relaxed font-medium">
                {job.description}
              </p>

              {/* Criteria Pills Preview */}
              <div className="mt-4 pt-4 border-t border-subtle space-y-2">
                <span className="block text-[10px] font-semibold text-muted uppercase tracking-wider">
                  Screening Benchmarks ({job.criteria.length})
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {job.criteria.slice(0, 3).map((crit) => (
                    <span
                      key={crit.id}
                      className="text-[11px] font-medium bg-elevated px-2.5 py-1 rounded-pill border border-subtle text-ink/90"
                    >
                      {crit.name}
                    </span>
                  ))}
                  {job.criteria.length > 3 && (
                    <span className="text-[11px] font-medium bg-elevated px-2 py-1 rounded-pill border border-subtle text-muted">
                      +{job.criteria.length - 3} more
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-subtle flex items-center justify-between">
              <span className="text-xs font-medium text-muted">Transparent Evaluation</span>
              <span className="text-xs font-semibold text-accent flex items-center gap-1 group-hover:underline">
                <span>View Criteria & Apply</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
