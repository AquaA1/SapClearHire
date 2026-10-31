import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
import { CriterionCategory } from '../../contracts/enums';
import { Plus, Trash2, ArrowLeft, Sparkles } from 'lucide-react';
import { Button } from '../../components/ui';

interface CriterionInput {
  name: string;
  description: string;
  category: CriterionCategory;
  weight: number;
}

export const EmployerJobCreatePage: React.FC = () => {
  const navigate = useNavigate();

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

  const handleSubmit = async (e: React.FormEvent) => {
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
      navigate(`/employer/jobs/${created.id}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 select-none">
      {/* ── Back Navigation ───────────────────────────────────── */}
      <div>
        <button
          onClick={() => navigate('/employer/jobs')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to job requisitions
        </button>
      </div>

      <div className="pb-3 border-b border-subtle">
        <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">Create Job Requisition</h1>
        <p className="text-xs text-muted mt-1 font-medium">
          Define explicit, versioned criteria. Candidates will be evaluated strictly on these benchmarks.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Job Details */}
        <div className="bg-surface rounded-card p-6 md:p-8 border border-subtle shadow-card space-y-4">
          <h2 className="text-base font-semibold text-ink tracking-tight pb-3 border-b border-subtle">
            Requisition Details
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">
                Job Title *
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Senior Backend Engineer"
                className="w-full px-3.5 py-2.5 rounded-sm border border-subtle text-ink bg-elevated placeholder:text-muted focus:border-accent focus:outline-none text-xs font-medium"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">
                Department
              </label>
              <select
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-sm border border-subtle text-ink bg-elevated focus:border-accent focus:outline-none text-xs font-medium cursor-pointer"
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
              Role Description
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Outline role responsibilities and team mission..."
              className="w-full px-3.5 py-2.5 rounded-sm border border-subtle text-ink bg-elevated placeholder:text-muted focus:border-accent focus:outline-none text-xs font-medium"
            />
          </div>
        </div>

        {/* Dynamic Criteria Builder */}
        <div className="bg-surface rounded-card p-6 md:p-8 border border-subtle shadow-card space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-subtle">
            <div>
              <h2 className="text-base font-semibold text-ink tracking-tight">Versioned Evaluation Criteria</h2>
              <span className="text-xs text-muted font-medium">
                AI extraction engine directly links candidate resume claims to these criteria.
              </span>
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              leftIcon={<Plus className="w-3.5 h-3.5" />}
              onClick={handleAddCriterion}
            >
              Add Criterion
            </Button>
          </div>

          <div className="space-y-4 pt-2">
            {criteria.map((crit, index) => (
              <div
                key={index}
                className="p-4 rounded-sm border border-subtle bg-elevated space-y-3 relative group"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1">
                    <label className="block text-[11px] font-semibold text-muted uppercase tracking-wider mb-1">
                      Criterion #{index + 1} Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={crit.name}
                      onChange={(e) => handleUpdateCriterion(index, 'name', e.target.value)}
                      placeholder="e.g. 3+ Years React.js & TypeScript"
                      className="w-full px-3 py-2 rounded-sm border border-subtle bg-surface text-xs text-ink font-medium focus:border-accent focus:outline-none"
                    />
                  </div>

                  <div className="w-36">
                    <label className="block text-[11px] font-semibold text-muted uppercase tracking-wider mb-1">
                      Category
                    </label>
                    <select
                      value={crit.category}
                      onChange={(e) => handleUpdateCriterion(index, 'category', e.target.value)}
                      className="w-full px-3 py-2 rounded-sm border border-subtle bg-surface text-xs text-ink font-semibold focus:border-accent focus:outline-none cursor-pointer"
                    >
                      <option value={CriterionCategory.REQUIRED} className="bg-surface text-ink">Required</option>
                      <option value={CriterionCategory.PREFERRED} className="bg-surface text-ink">Preferred</option>
                    </select>
                  </div>

                  {criteria.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveCriterion(index)}
                      className="p-2 text-muted hover:text-danger rounded-sm transition-colors mt-5 cursor-pointer"
                      title="Remove Criterion"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <div>
                  <input
                    type="text"
                    value={crit.description}
                    onChange={(e) => handleUpdateCriterion(index, 'description', e.target.value)}
                    placeholder="Brief explanation of acceptable evidence for this criterion..."
                    className="w-full px-3 py-1.5 rounded-sm border border-subtle bg-surface text-xs text-ink placeholder:text-muted focus:border-accent focus:outline-none font-medium"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Submit Bar */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            type="button"
            variant="ghost"
            size="md"
            onClick={() => navigate('/employer/jobs')}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={isSubmitting}
            isLoading={isSubmitting}
            variant="primary"
            size="md"
            rightIcon={<Sparkles className="w-3.5 h-3.5" />}
            className="font-semibold"
          >
            Publish Versioned Requisition
          </Button>
        </div>
      </form>
    </div>
  );
};
