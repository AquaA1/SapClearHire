import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
import { Job } from '../../contracts/models';
import { StatusBadge } from '../../components/ui/Badge';
import { Plus, ChevronRight, Layers } from 'lucide-react';
import {
  Button,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '../../components/ui';

export const EmployerJobsPage: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    mockService.listJobs().then(setJobs);
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-6 select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-subtle">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">Job Requisitions</h1>
          <p className="text-xs text-muted mt-1 font-medium">
            Manage organization postings and inspect versioned screening criteria.
          </p>
        </div>

        <Button
          onClick={() => navigate('/employer/jobs/new')}
          variant="white"
          size="sm"
          leftIcon={<Plus className="w-4 h-4" />}
          className="shrink-0 self-start sm:self-auto cursor-pointer font-semibold shadow-sm"
        >
          New Requisition
        </Button>
      </div>

      {/* ── Requisitions Table Card ───────────────────────────── */}
      <div className="bg-surface rounded-card p-6 border border-subtle shadow-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Position Title</TableHead>
              <TableHead>Department</TableHead>
              <TableHead>Criteria</TableHead>
              <TableHead>Applicants</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.map((job) => (
              <TableRow
                key={job.id}
                onClick={() => navigate(`/employer/jobs/${job.id}`)}
                className="cursor-pointer group"
              >
                <TableCell>
                  <div className="font-semibold text-ink text-xs group-hover:text-accent transition-colors">
                    {job.title}
                  </div>
                  <div className="text-[11px] text-muted font-mono mt-0.5">REQ #{job.id.slice(0, 8)}</div>
                </TableCell>
                <TableCell>
                  <span className="text-xs font-medium text-ink">
                    {job.department || 'Engineering'}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center gap-1.5 font-medium text-ink bg-elevated border border-subtle px-2.5 py-0.5 rounded-pill text-[11px]">
                    <Layers className="w-3 h-3 text-accent" />
                    {job.criteria.length} Benchmarks
                  </span>
                </TableCell>
                <TableCell>
                  <span className="text-xs font-semibold text-ink">
                    {job.applicants_count || 12}
                  </span>
                </TableCell>
                <TableCell>
                  <StatusBadge status={job.status} size="sm" />
                </TableCell>
                <TableCell className="text-right">
                  <span className="text-xs font-semibold text-accent group-hover:underline inline-flex items-center gap-1">
                    <span>Manage</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};
