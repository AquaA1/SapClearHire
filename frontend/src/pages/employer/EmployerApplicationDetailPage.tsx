import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { mockService } from '../../services/mock/mockService';
import { Application, Evaluation } from '../../contracts/models';
import { StatusBadge } from '../../components/ui/Badge';
import { CoverageSummaryBar } from '../../components/evidence/CoverageSummaryBar';
import { CriterionEvidenceCard } from '../../components/evidence/CriterionEvidenceCard';
import {
  Mail,
  Plus,
  Play,
  Flag,
  Clock,
  Check,
} from 'lucide-react';
import { Button, LoadingSpinner } from '../../components/ui';

export const EmployerApplicationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [allApps, setAllApps] = useState<Application[]>([]);
  const [activeApp, setActiveApp] = useState<Application | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [activeTab, setActiveTab] = useState<'DETAILS' | 'RESUME' | 'HIRING PIPELINE' | 'EVIDENCE'>('DETAILS');
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isFlagging, setIsFlagging] = useState(false);
  const [notes, setNotes] = useState<Array<{ id: string; author: string; time: string; text: string; role: string }>>([
    {
      id: 'n1',
      author: 'Sarah Jenkins',
      role: 'Employer Admin',
      time: '31 Oct 2026 • 04:23 PM',
      text: 'Candidate demonstrated strong distributed systems background. Flagged Kafka requirement for human reviewer verification due to ambiguous bullet point citation.',
    },
    {
      id: 'n2',
      author: 'Marcus Vance',
      role: 'Lead Reviewer',
      time: '31 Oct 2026 • 05:00 PM',
      text: 'Reviewed candidate clarification statement regarding Apache Kafka cluster throughput on Page 2, lines 18-24. Prepared for signoff.',
    },
  ]);
  const [newNoteText, setNewNoteText] = useState('');
  const [showAddNote, setShowAddNote] = useState(false);

  useEffect(() => {
    mockService.listApplications().then((apps) => {
      setAllApps(apps);
      const current = apps.find((a) => a.id === id) || apps[0];
      setActiveApp(current);
      if (current) {
        mockService.getEvaluation(current.id).then(setEvaluation);
      }
    });
  }, [id]);

  const handleSelectApp = (app: Application) => {
    setActiveApp(app);
    mockService.getEvaluation(app.id).then(setEvaluation);
  };

  const handleTriggerEvaluation = async () => {
    if (!activeApp) return;
    setIsEvaluating(true);
    const updated = await mockService.evaluateApplication(activeApp.id);
    setEvaluation(updated);
    setIsEvaluating(false);
  };

  const handleAutoFlag = async () => {
    if (!activeApp) return;
    setIsFlagging(true);
    await mockService.createReviewFlags(activeApp.id);
    setIsFlagging(false);
    navigate('/reviewer/queue');
  };

  const handleAddNote = () => {
    if (!newNoteText.trim()) return;
    setNotes([
      ...notes,
      {
        id: `note-${Date.now()}`,
        author: 'Sarah Jenkins',
        role: 'Employer Admin',
        time: 'Just now',
        text: newNoteText.trim(),
      },
    ]);
    setNewNoteText('');
    setShowAddNote(false);
  };

  if (!activeApp) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <LoadingSpinner size="lg" label="Loading candidate dossier..." />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 select-none">
      {/* ── 2-Column Split Dossier Layout ──────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Column: Candidate Roster (4 Cols) */}
        <div className="lg:col-span-4 bg-surface rounded-card border border-subtle p-5 shadow-card space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-subtle">
            <h3 className="font-semibold text-ink text-sm">
              All Applicants ({allApps.length})
            </h3>
            <span className="text-[11px] text-muted font-medium">Requisition Cohort</span>
          </div>

          <div className="space-y-2.5 max-h-[calc(100vh-220px)] overflow-y-auto pr-1">
            {allApps.map((app) => {
              const isActive = app.id === activeApp.id;

              return (
                <div
                  key={app.id}
                  onClick={() => handleSelectApp(app)}
                  className={`p-3.5 rounded-sm border transition-all cursor-pointer relative flex flex-col justify-between ${
                    isActive
                      ? 'bg-elevated border-accent ring-1 ring-accent'
                      : 'bg-elevated/40 border-subtle hover:border-subtle-strong hover:bg-elevated/70'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-pill bg-surface border border-subtle text-accent font-semibold flex items-center justify-center text-xs shrink-0">
                        {app.candidate_name
                          ?.split(' ')
                          .map((n) => n[0])
                          .join('') || 'C'}
                      </div>
                      <div className="min-w-0">
                        <h4 className="font-semibold text-ink text-xs truncate">
                          {app.candidate_name || 'Candidate'}
                        </h4>
                        <p className="text-[11px] text-muted font-medium truncate mt-0.5">
                          {app.job_title}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-subtle">
                    <StatusBadge status={app.status} size="sm" />
                    <span className="text-[10px] font-medium text-muted">
                      #{app.id.slice(0, 8)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Full Candidate Detail Dossier (8 Cols) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Header Banner */}
          <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-card bg-elevated border border-subtle text-accent font-semibold text-lg flex items-center justify-center">
                  {activeApp.candidate_name
                    ?.split(' ')
                    .map((n) => n[0])
                    .join('') || 'C'}
                </div>
                <div>
                  <div className="flex items-center gap-2.5 mb-1">
                    <h2 className="text-xl font-semibold text-ink tracking-tight">
                      {activeApp.candidate_name}
                    </h2>
                    <StatusBadge status={activeApp.status} size="sm" />
                  </div>
                  <div className="flex items-center gap-2.5 text-xs text-muted font-medium">
                    <span>{activeApp.job_title}</span>
                    <span>•</span>
                    <span className="font-medium text-ink">{activeApp.candidate_email}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                <Button
                  onClick={handleTriggerEvaluation}
                  disabled={isEvaluating}
                  isLoading={isEvaluating}
                  variant="primary"
                  size="sm"
                  leftIcon={<Play className="w-3.5 h-3.5 fill-current" />}
                  className="font-semibold"
                >
                  <span>Re-Screen Evidence</span>
                </Button>

                <Button
                  onClick={handleAutoFlag}
                  disabled={isFlagging}
                  isLoading={isFlagging}
                  variant="secondary"
                  size="sm"
                  leftIcon={<Flag className="w-3.5 h-3.5 text-warn" />}
                >
                  <span>Triage to Reviewer</span>
                </Button>
              </div>
            </div>

            {/* Pipeline Steps */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2 border-t border-subtle text-center text-xs">
              {[
                { label: '1. Screening', active: true },
                { label: '2. Evidence Grounded', active: true },
                { label: '3. Review Pending', active: activeApp.status === 'needs_review' },
                { label: '4. Decision Finalized', active: activeApp.status === 'reviewed' },
              ].map((step, idx) => (
                <div
                  key={idx}
                  className={`py-2 px-3 rounded-sm border text-[11px] font-medium transition-all ${
                    step.active
                      ? 'bg-accent-dim text-accent border-accent/40 font-semibold'
                      : 'bg-elevated/40 text-muted border-subtle'
                  }`}
                >
                  {step.label}
                </div>
              ))}
            </div>

            {/* Dossier Tabs */}
            <div className="flex items-center gap-2 pt-2 border-t border-subtle">
              {(['DETAILS', 'EVIDENCE', 'RESUME', 'HIRING PIPELINE'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3.5 py-1.5 rounded-pill text-xs font-semibold transition-all cursor-pointer ${
                    activeTab === tab
                      ? 'bg-elevated text-ink border border-subtle shadow-sm'
                      : 'text-muted hover:text-ink'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content: DETAILS & EVIDENCE */}
          {(activeTab === 'DETAILS' || activeTab === 'EVIDENCE') && evaluation && (
            <div className="space-y-6">
              {/* Coverage Summary Bar */}
              <CoverageSummaryBar coverage={evaluation.coverage} />

              {/* Criteria Evidence Cards List */}
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-subtle">
                  <h3 className="font-semibold text-ink text-sm">
                    Grounded Criteria Evaluations ({evaluation.criteria_evaluations.length})
                  </h3>
                  <span className="text-[11px] font-medium text-muted">
                    Run #{evaluation.extraction_run_id}
                  </span>
                </div>

                <div className="space-y-3">
                  {evaluation.criteria_evaluations.map((item) => (
                    <CriterionEvidenceCard key={item.criterion_id} item={item} />
                  ))}
                </div>
              </div>

              {/* Reviewer Notes Timeline */}
              <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-subtle">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">Reviewer Audit Timeline</h3>
                    <p className="text-[11px] text-muted font-medium mt-0.5">Collaborative notes and determination records</p>
                  </div>
                  <Button
                    onClick={() => setShowAddNote(!showAddNote)}
                    variant="secondary"
                    size="sm"
                    leftIcon={<Plus className="w-3.5 h-3.5" />}
                  >
                    Add Note
                  </Button>
                </div>

                {showAddNote && (
                  <div className="p-4 rounded-sm bg-elevated border border-subtle space-y-3">
                    <textarea
                      rows={3}
                      value={newNoteText}
                      onChange={(e) => setNewNoteText(e.target.value)}
                      placeholder="Add an auditable note about this candidate's evidence..."
                      className="w-full text-xs p-3 rounded-sm bg-surface border border-subtle text-ink placeholder:text-muted focus:border-accent focus:outline-none font-medium"
                    />
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowAddNote(false)}
                      >
                        Cancel
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={handleAddNote}
                        className="font-semibold"
                      >
                        Save Note
                      </Button>
                    </div>
                  </div>
                )}

                <div className="space-y-3 pt-1">
                  {notes.map((note) => (
                    <div key={note.id} className="p-4 rounded-sm bg-elevated border border-subtle space-y-1.5">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-semibold text-ink">{note.author} ({note.role})</span>
                        <span className="text-[10px] text-muted font-medium">{note.time}</span>
                      </div>
                      <p className="text-xs text-muted leading-relaxed font-medium">{note.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Tab Content: RESUME */}
          {activeTab === 'RESUME' && (
            <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-subtle">
                <h3 className="font-semibold text-ink text-sm">Indexed Source Document</h3>
                <span className="text-xs font-medium text-accent">OCR Parsed & Sealed</span>
              </div>
              <div className="p-6 rounded-sm bg-elevated border border-subtle text-xs text-ink space-y-4 leading-relaxed">
                <div className="border-b border-subtle pb-2 font-semibold text-ink">
                  Elena Rostova — Distributed Systems & Cloud Infrastructure Engineer
                </div>
                <p>
                  <strong className="text-accent">WORK EXPERIENCE:</strong><br />
                  Lead Cloud Infrastructure Architect | CloudMatrix Inc (2020 - Present)<br />
                  • Architected high-throughput message bus processing 25,000 msg/sec using Apache Kafka across 4 regional Kubernetes clusters.<br />
                  • Directed migration of legacy monolith to 65 microservices with zero downtime using Docker and Envoy service mesh.<br />
                  • Implemented Raft consensus protocols for distributed key-value state replication in Go.
                </p>
                <p>
                  <strong className="text-accent">TECHNICAL PROFICIENCIES:</strong><br />
                  Languages: Go, Rust, Python, TypeScript, SQL<br />
                  Distributed Systems: Apache Kafka, RabbitMQ, gRPC, Etcd, Redis<br />
                  Orchestration: Kubernetes (EKS, GKE, Bare-Metal), Terraform, Docker
                </p>
              </div>
            </div>
          )}

          {/* Tab Content: HIRING PIPELINE */}
          {activeTab === 'HIRING PIPELINE' && (
            <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
              <h3 className="font-semibold text-ink text-sm pb-2 border-b border-subtle">Pipeline Milestones</h3>
              <div className="space-y-3">
                <div className="p-4 rounded-sm bg-elevated border border-subtle flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-ink block">Step 1: Application Ingestion</span>
                    <span className="text-[11px] text-muted font-medium">Received via ClearHire Portal</span>
                  </div>
                  <span className="text-accent text-xs font-semibold flex items-center gap-1">
                    <Check className="w-4 h-4" /> Completed
                  </span>
                </div>
                <div className="p-4 rounded-sm bg-elevated border border-subtle flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-ink block">Step 2: Automated Evidence Grounding</span>
                    <span className="text-[11px] text-muted font-medium">OCR text parsed with coordinate indexing</span>
                  </div>
                  <span className="text-accent text-xs font-semibold flex items-center gap-1">
                    <Check className="w-4 h-4" /> 5/6 Verified
                  </span>
                </div>
                <div className="p-4 rounded-sm bg-elevated border border-subtle flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-ink block">Step 3: Human Oversight Review</span>
                    <span className="text-[11px] text-muted font-medium">Triage of contested Kafka criterion</span>
                  </div>
                  <span className="text-warn text-xs font-semibold flex items-center gap-1">
                    <Clock className="w-4 h-4" /> In Triage
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
