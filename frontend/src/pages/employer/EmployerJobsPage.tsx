import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
import { Job } from '../../contracts/models';
import { CriterionCategory } from '../../contracts/enums';
import { StatusBadge } from '../../components/ui/Badge';
import { Plus, ChevronRight, Layers, X, Sparkles, Trash2, Users, ShieldCheck } from 'lucide-react';
import {
  Button,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '../../components/ui';

interface CriterionInput {
  name: string;
  description: string;
  category: CriterionCategory;
  weight: number;
}

export const EmployerJobsPage: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // New Requisition Form State
  const [title, setTitle] = useState('');
  const [department, setDepartment] = useState('Core Infrastructure');
  const [description, setDescription] = useState('');
  const [criteria, setCriteria] = useState<CriterionInput[]>([
    {
      name: '5+ Years Production Python (FastAPI / AsyncIO)',
      description: 'Hands-on experience with asynchronous web APIs and microservices.',
      category: CriterionCategory.REQUIRED,
      weight: 1.0,
    },
    {
      name: 'PostgreSQL Scaling & Index Optimization',
      description: 'Experience analyzing explain plans and optimizing relational tables.',
      category: CriterionCategory.REQUIRED,
      weight: 1.0,
    },
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    mockService.listJobs().then((list) => {
      setJobs(list);
      if (list.length > 0) setSelectedJob(list[0]);
    });
  }, []);

  const handleAddCriterion = () => {
    setCriteria([
      ...criteria,
      {
        name: '',
        description: '',
        category: CriterionCategory.PREFERRED,
        weight: 0.8,
      },
    ]);
  };

  const handleRemoveCriterion = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index));
  };

  const handleUpdateCriterion = (index: number, field: keyof CriterionInput, val: any) => {
    const updated = [...criteria];
    updated[index] = { ...updated[index], [field]: val };
    setCriteria(updated);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || criteria.length === 0) return;

    setIsSubmitting(true);
    try {
      const created = await mockService.createJob({
        title,
        department,
        description,
        criteria,
      });
      setJobs([created, ...jobs]);
      setSelectedJob(created);
      setIsCreateModalOpen(false);
      // Reset form
      setTitle('');
      setDescription('');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 select-none">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-subtle">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">Job Requisitions Console</h1>
          <p className="text-xs text-muted mt-1 font-medium">
            Manage organization postings, inspect versioned criteria benchmarks, and create requisitions.
          </p>
        </div>

        <Button
          onClick={() => setIsCreateModalOpen(true)}
          variant="primary"
          size="sm"
          leftIcon={<Plus className="w-4 h-4" />}
          className="shrink-0 self-start sm:self-auto cursor-pointer font-semibold shadow-sm"
        >
          New Requisition
        </Button>
      </div>

      {/* ── 2-Column Consolidated Management: Table on Left, Criteria Drawer on Right ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left: Requisitions Table (7 cols) */}
        <div className="lg:col-span-7 bg-surface rounded-card p-6 border border-subtle shadow-card space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-subtle">
            <h3 className="text-sm font-semibold text-ink">Active Postings ({jobs.length})</h3>
            <span className="text-xs text-muted font-medium">Click row to preview criteria</span>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Position Title</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Criteria</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Dossier</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((job) => {
                const isSelected = selectedJob?.id === job.id;
                return (
                  <TableRow
                    key={job.id}
                    onClick={() => setSelectedJob(job)}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? 'bg-elevated border-l-2 border-l-accent' : ''
                    }`}
                  >
                    <TableCell>
                      <div className="font-semibold text-ink text-xs">{job.title}</div>
                      <div className="text-[11px] text-muted font-medium mt-0.5">REQ #{job.id.slice(0, 8)}</div>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs font-medium text-ink">
                        {job.department || 'Engineering'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1.5 font-medium text-ink bg-elevated border border-subtle px-2.5 py-0.5 rounded-pill text-[11px]">
                        <Layers className="w-3 h-3 text-accent" />
                        {job.criteria.length}
                      </span>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={job.status || 'active'} size="sm" />
                    </TableCell>
                    <TableCell className="text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate('/employer/applications/app-001');
                        }}
                        className="text-xs font-semibold text-accent hover:underline inline-flex items-center gap-1 cursor-pointer"
                        title="View candidate dossier"
                      >
                        <Users className="w-3.5 h-3.5" />
                        <span>Applicants</span>
                      </button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>

        {/* Right: Selected Job Criteria Inspector (5 cols) */}
        <div className="lg:col-span-5 bg-surface rounded-card p-6 border border-subtle shadow-card space-y-4">
          {selectedJob ? (
            <>
              <div className="flex items-center justify-between pb-3 border-b border-subtle">
                <div>
                  <span className="text-[10px] font-semibold text-accent uppercase tracking-wider block">
                    Versioned Benchmark Inspector
                  </span>
                  <h3 className="text-base font-semibold text-ink mt-0.5">{selectedJob.title}</h3>
                </div>
                <span className="text-xs font-medium text-muted bg-elevated px-2.5 py-0.5 rounded-pill border border-subtle">
                  v1.0 Immutable
                </span>
              </div>

              <p className="text-xs text-muted leading-relaxed font-medium">
                {selectedJob.description || 'Active requisition evaluated strictly against explicit resume citations.'}
              </p>

              <div className="pt-2 border-t border-subtle space-y-3">
                <span className="text-xs font-semibold text-ink uppercase tracking-wider block">
                  Configured Criteria ({selectedJob.criteria.length})
                </span>

                <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
                  {selectedJob.criteria.map((c, i) => (
                    <div key={c.id || i} className="p-3.5 rounded-sm border border-subtle bg-elevated space-y-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-medium text-muted">#0{i + 1}</span>
                        <span
                          className={`text-[9px] font-semibold px-2 py-0.5 rounded-pill uppercase tracking-wider ${
                            c.category === 'required'
                              ? 'bg-accent-dim text-accent border border-accent/30'
                              : 'bg-surface text-muted border border-subtle'
                          }`}
                        >
                          {c.category}
                        </span>
                      </div>
                      <h4 className="text-xs font-semibold text-ink">{c.name}</h4>
                      {c.description && (
                        <p className="text-[11px] text-muted leading-relaxed font-medium">{c.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-3 border-t border-subtle flex justify-between items-center">
                <span className="text-xs text-muted font-medium">Screen candidates for this role</span>
                <Button
                  onClick={() => navigate('/employer/applications/app-001')}
                  variant="primary"
                  size="sm"
                  rightIcon={<ChevronRight className="w-3.5 h-3.5" />}
                  className="font-semibold"
                >
                  Candidate Dossier
                </Button>
              </div>
            </>
          ) : (
            <div className="text-center py-12 text-muted">
              Select a requisition on the left to inspect its criteria benchmarks.
            </div>
          )}
        </div>

      </div>

      {/* ── Integrated Requisition Builder Modal ─────────────────── */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-surface rounded-card max-w-2xl w-full p-6 sm:p-8 shadow-modal border border-subtle relative max-h-[90vh] overflow-y-auto space-y-5">
            <div className="flex items-start justify-between pb-3 border-b border-subtle">
              <div>
                <h3 className="text-lg font-semibold text-ink">Create New Requisition</h3>
                <p className="text-xs text-muted mt-0.5 font-medium">
                  Define versioned criteria benchmarks for deterministic AI grounding.
                </p>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="p-1.5 rounded-full text-muted hover:text-ink transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">
                    Position Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Senior Backend Engineer"
                    className="w-full px-3.5 py-2 rounded-sm border border-subtle text-ink bg-elevated placeholder:text-muted focus:border-accent focus:outline-none text-xs font-medium"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">
                    Department
                  </label>
                  <select
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-sm border border-subtle text-ink bg-elevated focus:border-accent focus:outline-none text-xs font-medium cursor-pointer"
                  >
                    <option value="Core Infrastructure" className="bg-surface text-ink">Core Infrastructure</option>
                    <option value="Product Design" className="bg-surface text-ink">Product Design</option>
                    <option value="Security & Compliance" className="bg-surface text-ink">Security & Compliance</option>
                    <option value="Data Engineering" className="bg-surface text-ink">Data Engineering</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">
                  Role Overview
                </label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Outline responsibilities and core mission..."
                  className="w-full px-3.5 py-2 rounded-sm border border-subtle text-ink bg-elevated placeholder:text-muted focus:border-accent focus:outline-none text-xs font-medium"
                />
              </div>

              {/* Dynamic Criteria Builder */}
              <div className="space-y-3 pt-2 border-t border-subtle">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-xs font-semibold text-ink uppercase tracking-wider">Evaluation Criteria</h4>
                    <span className="text-[11px] text-muted font-medium">Claims must be grounded against these items</span>
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    leftIcon={<Plus className="w-3.5 h-3.5" />}
                    onClick={handleAddCriterion}
                  >
                    Add Benchmark
                  </Button>
                </div>

                <div className="space-y-3 max-h-[280px] overflow-y-auto pr-1">
                  {criteria.map((crit, index) => (
                    <div key={index} className="p-3.5 rounded-sm border border-subtle bg-elevated space-y-2">
                      <div className="flex items-center justify-between gap-3">
                        <input
                          type="text"
                          required
                          value={crit.name}
                          onChange={(e) => handleUpdateCriterion(index, 'name', e.target.value)}
                          placeholder="Benchmark name, e.g. 5+ Years Python"
                          className="flex-1 px-3 py-1.5 rounded-sm border border-subtle bg-surface text-xs text-ink font-medium focus:border-accent focus:outline-none"
                        />
                        <select
                          value={crit.category}
                          onChange={(e) => handleUpdateCriterion(index, 'category', e.target.value)}
                          className="w-32 px-2.5 py-1.5 rounded-sm border border-subtle bg-surface text-xs text-ink font-semibold focus:border-accent focus:outline-none cursor-pointer"
                        >
                          <option value={CriterionCategory.REQUIRED} className="bg-surface text-ink">Required</option>
                          <option value={CriterionCategory.PREFERRED} className="bg-surface text-ink">Preferred</option>
                        </select>
                        {criteria.length > 1 && (
                          <button
                            type="button"
                            onClick={() => handleRemoveCriterion(index)}
                            className="p-1.5 text-muted hover:text-danger rounded transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                      <input
                        type="text"
                        value={crit.description}
                        onChange={(e) => handleUpdateCriterion(index, 'description', e.target.value)}
                        placeholder="Acceptable evidence description..."
                        className="w-full px-3 py-1.5 rounded-sm border border-subtle bg-surface text-xs text-ink placeholder:text-muted focus:border-accent focus:outline-none font-medium"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-3 border-t border-subtle flex justify-end gap-3">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsCreateModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  isLoading={isSubmitting}
                  variant="primary"
                  size="sm"
                  rightIcon={<Sparkles className="w-3.5 h-3.5" />}
                  className="font-semibold"
                >
                  Publish Requisition
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
