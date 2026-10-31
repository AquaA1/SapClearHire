import React, { useEffect, useState } from 'react';
import { mockService } from '../../services/mock/mockService';
import { CandidateSkill } from '../../contracts/models';
import { useAuth } from '../../stores/authStore';
import { Sparkles, FileText, UserCheck } from 'lucide-react';

export const CandidateProfilePage: React.FC = () => {
  const { user } = useAuth();
  const [skills, setSkills] = useState<CandidateSkill[]>([]);

  useEffect(() => {
    mockService.getCandidateSkills().then(setSkills);
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-6 select-none">
      {/* ── Profile Header ────────────────────────────────────── */}
      <div className="bg-surface rounded-card p-6 md:p-8 border border-subtle shadow-card flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-card bg-elevated border border-subtle text-accent flex items-center justify-center font-semibold text-lg">
            {user.full_name.split(' ').map((n) => n[0]).join('')}
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">{user.full_name}</h1>
              <span className="text-[11px] font-medium px-2.5 py-0.5 rounded-pill bg-success-dim text-success border border-success/30 flex items-center gap-1">
                <UserCheck className="w-3 h-3" />
                Verified Candidate
              </span>
            </div>
            <p className="text-xs text-muted mt-1 font-medium">{user.email}</p>
          </div>
        </div>

        <div className="text-right hidden sm:block">
          <span className="block text-xs font-semibold text-muted uppercase tracking-wider">
            Verified Inventory
          </span>
          <span className="text-3xl font-semibold text-ink block mt-0.5">{skills.length} Skills</span>
        </div>
      </div>

      {/* ── Skills Grid ───────────────────────────────────────── */}
      <div className="bg-surface rounded-card p-6 md:p-8 border border-subtle shadow-card space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-subtle">
          <div>
            <h2 className="text-base font-semibold text-ink tracking-tight">Verified Skills & Qualifications</h2>
            <p className="text-xs text-muted font-medium mt-0.5">
              Extracted directly from resume citations during AI evidence extraction.
            </p>
          </div>
          <span className="text-xs font-medium text-accent bg-accent-dim px-3 py-1 rounded-pill border border-accent/30 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            Grounding Verified
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {skills.map((skill) => (
            <div
              key={skill.id}
              className="p-4 rounded-sm border border-subtle bg-elevated space-y-2.5"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-ink">{skill.skill_name}</span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-pill bg-surface text-muted uppercase tracking-wider border border-subtle">
                  {skill.category || 'Skill'}
                </span>
              </div>

              {skill.source_excerpt && (
                <p className="text-xs text-ink/90 font-mono italic bg-surface p-3 rounded-sm border border-subtle leading-relaxed">
                  "{skill.source_excerpt}"
                </p>
              )}

              <div className="flex items-center justify-between text-[11px] text-muted font-medium pt-1">
                <span>Confidence: {Math.round(skill.confidence * 100)}% Verified</span>
                {skill.source_page && (
                  <span className="flex items-center gap-1 font-mono text-ink">
                    <FileText className="w-3 h-3 text-muted" /> Page {skill.source_page}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
