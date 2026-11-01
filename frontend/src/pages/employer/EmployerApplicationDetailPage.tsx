import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { applicationService } from '../../services/api/applicationService';
import { evaluationService } from '../../services/api/evaluationService';
import { documentService } from '../../services/api/documentService';
import { reviewService } from '../../services/api/reviewService';
import { Application, Evaluation } from '../../contracts/models';
import { StatusBadge } from '../../components/ui/Badge';
import { CoverageSummaryBar } from '../../components/evidence/CoverageSummaryBar';
import { CriterionEvidenceCard } from '../../components/evidence/CriterionEvidenceCard';
import {
  Users,
  Play,
  Flag,
  Clock,
  ArrowLeft,
  FileText,
  AlertCircle,
  Briefcase,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import { Button, LoadingSpinner } from '../../components/ui';
import { ResumePdfViewer } from '../../components/dossier/ResumePdfViewer';
import { CandidateExtractedProfile } from '../../components/dossier/CandidateExtractedProfile';

export const EmployerApplicationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [allApps, setAllApps] = useState<Application[]>([]);
  const [activeApp, setActiveApp] = useState<Application | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [activeTab, setActiveTab] = useState<'DETAILS' | 'RESUME' | 'HIRING PIPELINE' | 'EVIDENCE'>('DETAILS');
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isResolvingPrereq, setIsResolvingPrereq] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [prereqRequired, setPrereqRequired] = useState(false);
  const [isFlagging, setIsFlagging] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState<Array<{ id: string; author: string; time: string; text: string; role: string }>>([]);
  const [newNoteText, setNewNoteText] = useState('');
  const [showAddNote, setShowAddNote] = useState(false);

  useEffect(() => {
    const loadDossiers = async () => {
      setLoading(true);
      try {
        const apps = await applicationService.listApplications();
        setAllApps(apps);

        if (apps.length > 0) {
          const current = (id ? apps.find((a) => a.id === id) : null) || apps[0];
          setActiveApp(current);

          if (current) {
            try {
              const ev = await evaluationService.getEvaluationByApplication(current.id);
              setEvaluation(ev);
            } catch {
              setEvaluation(null);
            }
          }
        }
      } catch (err) {
        console.error('Failed to load application dossiers:', err);
      } finally {
        setLoading(false);
      }
    };

    loadDossiers();
  }, [id]);

  const handleSelectApp = async (app: Application) => {
    setActiveApp(app);
    setEvalError(null);
    setPrereqRequired(false);
    try {
      const ev = await evaluationService.getEvaluationByApplication(app.id);
      setEvaluation(ev);
    } catch {
      setEvaluation(null);
    }
  };

  const handleTriggerEvaluation = async () => {
    if (!activeApp) return;
    setIsEvaluating(true);
    setEvalError(null);
    setPrereqRequired(false);
    try {
      const updated = await evaluationService.evaluateApplication(activeApp.id);
      setEvaluation(updated);
      setActiveApp({ ...activeApp, status: 'screening' as any });
      setAllApps((prev) =>
        prev.map((a) => (a.id === activeApp.id ? { ...a, status: 'screening' as any } : a))
      );
    } catch (err: any) {
      console.error('Failed to trigger evaluation:', err);
      const errMsg = err?.message || err?.detail || 'Failed to execute screening evaluation';
      setEvalError(errMsg);
      if (
        errMsg.toLowerCase().includes('prerequisite') ||
        errMsg.toLowerCase().includes('claim extraction') ||
        errMsg.toLowerCase().includes('evidence extraction')
      ) {
        setPrereqRequired(true);
      }
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleResolvePrereqAndEvaluate = async () => {
    if (!activeApp || !activeApp.primary_document_id) return;
    setIsResolvingPrereq(true);
    setEvalError(null);
    try {
      // 1. Trigger AI claim extraction
      await documentService.triggerAIExtraction(activeApp.primary_document_id);

      // 2. Poll extraction until completed (up to 45s)
      let attempts = 0;
      const maxAttempts = 30;
      let completed = false;
      while (attempts < maxAttempts) {
        attempts += 1;
        await new Promise((resolve) => setTimeout(resolve, 1500));
        try {
          const ext = await documentService.getExtractionResults(activeApp.primary_document_id);
          if (ext.status === 'completed') {
            completed = true;
            break;
          }
          if (ext.status === 'failed') {
            throw new Error(ext.error_message || 'AI claim extraction failed');
          }
        } catch (pollErr: any) {
          if (pollErr?.message?.includes('failed')) throw pollErr;
        }
      }

      if (!completed) {
        throw new Error('AI claim extraction timed out. Please try again.');
      }

      // 3. Now execute evaluation
      const updated = await evaluationService.evaluateApplication(activeApp.id);
      setEvaluation(updated);
      setPrereqRequired(false);
      setActiveApp({ ...activeApp, status: 'screening' as any });
      setAllApps((prev) =>
        prev.map((a) => (a.id === activeApp.id ? { ...a, status: 'screening' as any } : a))
      );
    } catch (err: any) {
      console.error('Failed to resolve prerequisite and evaluate:', err);
      setEvalError(err?.message || 'Failed to complete extraction and evaluation');
    } finally {
      setIsResolvingPrereq(false);
    }
  };

  const handleAutoFlag = async () => {
    if (!activeApp) return;
    setIsFlagging(true);
    try {
      await reviewService.createReviewFlags({ application_id: activeApp.id });
      navigate('/employer/reviews');
    } catch (err) {
      console.error('Failed to flag review cases:', err);
    } finally {
      setIsFlagging(false);
    }
  };

  const handleAddNote = () => {
    if (!newNoteText.trim()) return;
    setNotes([
      ...notes,
      {
        id: `note-${Date.now()}`,
        author: 'Administrator',
        role: 'Employer Admin',
        time: 'Just now',
        text: newNoteText.trim(),
      },
    ]);
    setNewNoteText('');
    setShowAddNote(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <LoadingSpinner size="lg" label="Loading candidate dossiers..." />
      </div>
    );
  }

  // Honest empty state when no applications exist
  if (allApps.length === 0 || !activeApp) {
    return (
      <div className="bg-surface rounded-card border border-subtle p-12 text-center max-w-lg mx-auto mt-12 space-y-4 shadow-card">
        <Users className="w-12 h-12 text-muted mx-auto opacity-50" />
        <h3 className="text-base font-semibold text-ink">No Candidate Applications Submitted</h3>
        <p className="text-xs text-muted max-w-sm mx-auto leading-relaxed">
          Candidates who apply to your active job requisitions will appear here with extracted resumes, evidence grounding, and verification benchmarks.
        </p>
        <Button onClick={() => navigate('/employer/jobs')} variant="secondary" size="sm">
          <Briefcase className="w-4 h-4 mr-1.5" /> Manage Requisitions
        </Button>
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
                          ? app.candidate_name
                              .split(' ')
                              .map((n) => n[0])
                              .join('')
                          : 'C'}
                      </div>
                      <div className="min-w-0">
                        <h4 className="font-semibold text-ink text-xs truncate">
                          {app.candidate_name || `Applicant #${app.candidate_id.slice(0, 8)}`}
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
                    ? activeApp.candidate_name
                        .split(' ')
                        .map((n) => n[0])
                        .join('')
                    : 'C'}
                </div>
                <div>
                  <div className="flex items-center gap-2.5 mb-1">
                    <h2 className="text-xl font-semibold text-ink tracking-tight">
                      {activeApp.candidate_name || `Applicant #${activeApp.candidate_id.slice(0, 8)}`}
                    </h2>
                    <StatusBadge status={activeApp.status} size="sm" />
                  </div>
                  <div className="flex items-center gap-2.5 text-xs text-muted font-medium">
                    <span>{activeApp.job_title}</span>
                    <span>•</span>
                    <span className="font-medium text-ink">
                      App #{activeApp.id.slice(0, 8)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                <Button
                  onClick={handleTriggerEvaluation}
                  disabled={isEvaluating || isResolvingPrereq}
                  isLoading={isEvaluating || isResolvingPrereq}
                  variant="primary"
                  size="sm"
                  leftIcon={<Play className="w-3.5 h-3.5 fill-current" />}
                  className="font-semibold"
                >
                  <span>{isResolvingPrereq ? 'Extracting & Screening...' : (evaluation ? 'Re-Screen Evidence' : 'Screen Evidence')}</span>
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
                { label: '1. Submitted', active: true },
                { label: '2. Evidence Grounded', active: !!evaluation },
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

          {/* Tab Content: DETAILS (Extracted Candidate Profile) */}
          {activeTab === 'DETAILS' && (
            <CandidateExtractedProfile
              application={activeApp}
              documentId={activeApp.primary_document_id}
            />
          )}

          {activeTab === 'EVIDENCE' && (
            <div className="space-y-6">
              {/* Prerequisite Alert Banner */}
              {prereqRequired && (
                <div className="bg-surface rounded-card border border-amber-500/40 p-5 shadow-card space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                      <div className="space-y-1">
                        <h4 className="text-sm font-semibold text-ink">
                          Prerequisite Required: Structured AI Claim Extraction
                        </h4>
                        <p className="text-xs text-muted max-w-lg leading-relaxed">
                          Evidence screening requires structured candidate claims and grounded quotes from the resume. The AI claim extraction pipeline has not completed for this resume yet.
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleResolvePrereqAndEvaluate}
                      isLoading={isResolvingPrereq}
                      disabled={isResolvingPrereq || isEvaluating}
                      leftIcon={<Sparkles className="w-3.5 h-3.5 fill-current" />}
                      className="shrink-0 font-semibold"
                    >
                      <span>Extract Claims & Screen</span>
                    </Button>
                  </div>
                </div>
              )}

              {evalError && !prereqRequired && (
                <div className="p-4 rounded bg-red-500/10 border border-red-500/30 text-xs text-red-400 flex items-center justify-between">
                  <span>{evalError}</span>
                  <Button variant="secondary" size="sm" onClick={() => setEvalError(null)}>
                    Dismiss
                  </Button>
                </div>
              )}

              {evaluation ? (
                <>
                  {/* Coverage Summary Bar */}
                  <CoverageSummaryBar coverage={evaluation.coverage} />

                  {/* Criteria Evidence Cards List */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between pb-2 border-b border-subtle">
                      <h3 className="font-semibold text-ink text-sm">
                        Grounded Criteria Evaluations ({evaluation.criteria_evaluations.length})
                      </h3>
                      <span className="text-[11px] font-medium text-muted">
                        Extraction Run #{evaluation.extraction_run_id?.slice(0, 8)}
                      </span>
                    </div>

                    <div className="space-y-3">
                      {evaluation.criteria_evaluations.map((item) => (
                        <CriterionEvidenceCard key={item.criterion_id} item={item} />
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="bg-surface rounded-card border border-subtle p-10 text-center shadow-card space-y-3">
                  <FileText className="w-10 h-10 text-accent mx-auto opacity-70" />
                  <h3 className="text-sm font-semibold text-ink">Screening Evaluation Pending</h3>
                  <p className="text-xs text-muted max-w-md mx-auto leading-relaxed">
                    This candidate application has not been evaluated against criteria benchmarks yet. Click "Screen Evidence" above or use the automated extraction workflow below.
                  </p>
                  <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
                    <Button
                      onClick={handleTriggerEvaluation}
                      disabled={isEvaluating || isResolvingPrereq}
                      isLoading={isEvaluating}
                      variant="primary"
                      size="sm"
                    >
                      Execute Screening Evaluation
                    </Button>
                    <Button
                      onClick={handleResolvePrereqAndEvaluate}
                      disabled={isEvaluating || isResolvingPrereq}
                      isLoading={isResolvingPrereq}
                      variant="secondary"
                      size="sm"
                      leftIcon={<Sparkles className="w-3.5 h-3.5 fill-current" />}
                    >
                      Extract Claims & Screen
                    </Button>
                  </div>
                </div>
              )}

              {/* Reviewer Notes Timeline */}
              <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-subtle">
                  <div>
                    <h3 className="font-semibold text-ink text-sm">Adjudication Notes</h3>
                    <p className="text-xs text-muted font-medium mt-0.5">
                      Internal reviewer determinations and rationale logs
                    </p>
                  </div>
                  <Button
                    onClick={() => setShowAddNote(!showAddNote)}
                    variant="secondary"
                    size="sm"
                    className="text-xs"
                  >
                    {showAddNote ? 'Cancel' : '+ Add Note'}
                  </Button>
                </div>

                {showAddNote && (
                  <div className="p-4 rounded-sm bg-elevated border border-subtle space-y-3">
                    <textarea
                      value={newNoteText}
                      onChange={(e) => setNewNoteText(e.target.value)}
                      placeholder="Add an internal reviewer note or observation regarding candidate evidence..."
                      rows={3}
                      className="w-full bg-surface border border-subtle rounded-sm p-3 text-xs text-ink placeholder:text-muted focus:outline-none focus:border-subtle-strong resize-none font-medium"
                    />
                    <div className="flex justify-end gap-2">
                      <Button
                        onClick={() => setShowAddNote(false)}
                        variant="secondary"
                        size="sm"
                        className="text-xs"
                      >
                        Cancel
                      </Button>
                      <Button onClick={handleAddNote} variant="primary" size="sm" className="text-xs">
                        Save Note
                      </Button>
                    </div>
                  </div>
                )}

                {notes.length === 0 ? (
                  <div className="text-center py-6 text-muted text-xs font-medium">
                    No reviewer notes recorded for this candidate dossier yet.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {notes.map((note) => (
                      <div key={note.id} className="p-3.5 rounded-sm bg-elevated border border-subtle space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-ink">{note.author}</span>
                          <span className="text-[10px] text-muted font-medium">{note.time}</span>
                        </div>
                        <p className="text-xs text-ink/90 font-medium leading-relaxed">{note.text}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tab Content: RESUME (Authenticated Original PDF & OCR Viewer) */}
          {activeTab === 'RESUME' && (
            <ResumePdfViewer
              documentId={activeApp.primary_document_id}
              applicationId={activeApp.id}
            />
          )}

          {/* Tab Content: HIRING PIPELINE */}
          {activeTab === 'HIRING PIPELINE' && (
            <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
              <h3 className="font-semibold text-ink text-sm">Hiring Workflow Status</h3>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-2 border-b border-subtle">
                  <span className="text-muted">Current Application Status:</span>
                  <StatusBadge status={activeApp.status} size="sm" />
                </div>
                <div className="flex justify-between py-2 border-b border-subtle">
                  <span className="text-muted">Submission Date:</span>
                  <span className="text-ink font-medium">
                    {new Date(activeApp.submitted_at || activeApp.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex justify-between py-2">
                  <span className="text-muted">Target Requisition:</span>
                  <span className="text-ink font-medium">{activeApp.job_title}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
