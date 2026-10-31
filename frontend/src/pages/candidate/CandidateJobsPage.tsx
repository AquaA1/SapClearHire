import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { jobService } from '../../services/api/jobService';
import { Job } from '../../contracts/models';
import { JobStatus } from '../../contracts/enums';
import { Search, ChevronRight, Layers, AlertCircle, RefreshCw, Briefcase } from 'lucide-react';
import { Button } from '../../components/ui';

export const CandidateJobsPage: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('all');

  const fetchActiveJobs = async (skipCache = false) => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await jobService.listJobs({ status: JobStatus.ACTIVE }, skipCache);
      setJobs(list);
    } catch (err: unknown) {
      const errObj = err as { message?: string };
      setError(errObj.message || 'Failed to retrieve active job openings.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchActiveJobs();
  }, []);

  // Compute unique departments for filter dropdown
  const departments = ['all', ...Array.from(new Set(jobs.map((j) => j.department).filter(Boolean)))];

  const filteredJobs = jobs.filter((job) => {
    const matchesSearch =
      job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (job.description && job.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
      job.criteria?.some((c) => c.name.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesDept = departmentFilter === 'all' || job.department === departmentFilter;
    return matchesSearch && matchesDept;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-subtle">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">Active Requisitions</h1>
          <p className="text-xs text-muted mt-1 font-medium">
            Transparent criteria definitions. Know exactly what each role requires before applying.
          </p>
        </div>

        <Button
          onClick={() => fetchActiveJobs(true)}
          variant="secondary"
          size="sm"
          leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
          className="cursor-pointer font-medium self-start sm:self-auto"
        >
          Refresh
        </Button>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="p-4 rounded-card bg-danger/10 border border-danger/30 text-danger text-xs font-medium flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchActiveJobs(true)}
            className="text-xs"
          >
            Retry
          </Button>
        </div>
      )}

      {/* ── Filter and Search Bar ──────────────────────────────── */}
      <div className="bg-surface p-4 rounded-card border border-subtle shadow-card flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-muted absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by role title or criteria..."
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
            {departments.map((dept) => (
              <option key={dept} value={dept || 'General'} className="bg-surface text-ink">
                {dept === 'all' ? 'All Departments' : dept}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Job Card Grid / Loading / Empty States ──────────────────────── */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="bg-surface rounded-card p-6 border border-subtle shadow-card space-y-4 animate-pulse">
              <div className="h-4 w-28 bg-elevated rounded-pill" />
              <div className="h-6 w-3/4 bg-elevated rounded-sm" />
              <div className="h-10 w-full bg-elevated rounded-sm" />
              <div className="h-8 w-1/2 bg-elevated rounded-pill" />
            </div>
          ))}
        </div>
      ) : filteredJobs.length === 0 ? (
        <div className="bg-surface rounded-card border border-subtle p-12 text-center shadow-card space-y-3">
          <div className="w-12 h-12 rounded-full bg-elevated border border-subtle text-muted flex items-center justify-center mx-auto">
            <Briefcase className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-semibold text-ink">No Active Positions Found</h3>
          <p className="text-xs text-muted max-w-sm mx-auto font-medium leading-relaxed">
            {searchQuery || departmentFilter !== 'all'
              ? 'No open requisitions match your current search criteria. Try adjusting your query or department filter.'
              : 'There are currently no active job requisitions published. Please check back later.'}
          </p>
        </div>
      ) : (
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
                    {job.department || 'General'}
                  </span>
                  <span className="text-[10px] text-success font-medium bg-success-dim px-2.5 py-0.5 rounded-pill border border-success/30">
                    Active
                  </span>
                </div>

                <h2 className="text-base font-semibold text-ink group-hover:text-accent transition-colors">
                  {job.title}
                </h2>

                <p className="text-xs text-muted mt-2 line-clamp-2 leading-relaxed font-medium">
                  {job.description || 'Transparent screening benchmarked directly to factual resume citations.'}
                </p>

                {/* Criteria Pills Preview */}
                <div className="mt-4 pt-4 border-t border-subtle space-y-2">
                  <span className="block text-[10px] font-semibold text-muted uppercase tracking-wider">
                    Screening Benchmarks ({job.criteria ? job.criteria.length : 0})
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {job.criteria && job.criteria.length > 0 ? (
                      <>
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
                      </>
                    ) : (
                      <span className="text-xs text-muted">No criteria defined</span>
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
      )}
    </div>
  );
};
