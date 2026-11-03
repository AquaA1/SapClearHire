import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { applicationService } from '../../services/api/applicationService';
import { evaluationService } from '../../services/api/evaluationService';
import { documentService } from '../../services/api/documentService';
import { reviewService } from '../../services/api/reviewService';
import { Application, Evaluation, CriterionEvaluationItem } from '../../contracts/models';
import { ReviewDecisionType } from '../../contracts/enums';
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
import { InterviewTranscriptSection } from '../../components/interview/InterviewTranscriptSection';
import { useWebSocket } from '../../contexts/WebSocketContext';

export const EmployerApplicationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { subscribeToApplication } = useWebSocket();

  const [allApps, setAllApps] = useState<Application[]>([]);
  const [activeApp, setActiveApp] = useState<Application | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [activeTab, setActiveTab] = useState<'DETAILS' | 'RESUME' | 'HIRING PIPELINE' | 'EVIDENCE' | 'INTERVIEW COACH'>('DETAILS');
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
    let isMounted = true;

    const loadDossiers = async () => {
      setLoading(true);
      try {
        const [apps, targetEval] = await Promise.all([
          applicationService.listApplications(),
          id ? evaluationService.getEvaluationByApplication(id).catch(() => null) : Promise.resolve(null),
        ]);
        if (!isMounted) return;
        setAllApps(apps);

        if (apps.length > 0) {
          const current = (id ? apps.find((a) => a.id === id) : null) || apps[0];
          setActiveApp(current);

          if (targetEval && current && current.id === id) {
            setEvaluation(targetEval);
          } else if (current) {
            try {
              const ev = await evaluationService.getEvaluationByApplication(current.id);
              if (isMounted) setEvaluation(ev);
            } catch {
              if (isMounted) setEvaluation(null);
            }
          }
        }
      } catch (err) {
        console.error('Failed to load application dossiers:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadDossiers();

    return () => {
      isMounted = false;
    };
  }, [id]);

  // Real-time WebSocket subscription for live clarification updates
  useEffect(() => {
    const targetId = activeApp?.id || id;
    if (!targetId) return;

    const unsubscribe = subscribeToApplication(targetId, async () => {
      try {
        const [updatedApp, updatedEv] = await Promise.all([
          applicationService.getApplication(targetId).catch(() => null),
          evaluationService.getEvaluationByApplication(targetId).catch(() => null),
        ]);
        if (updatedApp) {
          setActiveApp(updatedApp);
          setAllApps((prev) => prev.map((a) => (a.id === updatedApp.id ? updatedApp : a)));
        }
        if (updatedEv) {
          setEvaluation(updatedEv);
        }
      } catch (err) {
        console.error('Failed to auto-refresh employer dossier via WebSocket:', err);
      }
    });

    return () => {
      unsubscribe();
    };
  }, [activeApp?.id, id, subscribeToApplication]);

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

  const handleReviewDecision = async (
    item: CriterionEvaluationItem,
    decision: ReviewDecisionType,
    rationale: string
  ) => {
    const targetId = item.criterion_evidence_id || item.criterion_id;
    if (!targetId) return;
    await reviewService.recordReviewDecision(targetId, decision, rationale);
    if (activeApp) {
      try {
        const [updatedApp, updatedEval] = await Promise.all([
          applicationService.getApplication(activeApp.id),
          evaluationService.getEvaluationByApplication(activeApp.id),
        ]);
        setActiveApp(updatedApp);
        setEvaluation(updatedEval);
      } catch (e) {
        console.error('Failed to refresh application/evaluation after decision', e);
      }
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
    <div className="max-w-7xl mx-auto space-y-5 select-none">
      {/* ── 2-Column Split Dossier Layout ──────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column: Candidate Roster (4 Cols) */}
        <div className="lg:col-span-4 bg-surface rounded-card border border-subtle p-4 shadow-card space-y-3">
          <div className="flex items-center justify-between pb-2.5 border-b border-subtle">
            <h3 className="font-bold text-ink text-base">
              All Applicants ({allApps.length})
            </h3>
            <span className="text-xs text-ink-secondary font-medium">Requisition Cohort</span>
          </div>

          <div className="space-y-2 max-h-[calc(100vh-190px)] overflow-y-auto pr-1">
            {allApps.map((app) => {
              const isActive = app.id === activeApp.id;

              return (
                <div
                  key={app.id}
                  onClick={() => handleSelectApp(app)}
                  className={`p-3 rounded-lg border transition-all cursor-pointer relative ${
                    isActive
                      ? 'bg-elevated border-accent ring-1 ring-accent'
                      : 'bg-elevated/40 border-subtle hover:border-subtle-strong hover:bg-elevated/70'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-surface border border-subtle text-accent font-bold flex items-center justify-center text-xs shrink-0">
                      {app.candidate_name
                        ? app.candidate_name
                            .split(' ')
                            .map((n) => n[0])
                            .join('')
                        : 'C'}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1.5">
                        <h4 className="font-bold text-ink text-sm truncate">
                          {app.candidate_name || `Applicant #${app.candidate_id.slice(0, 8)}`}
                        </h4>
                        <span className="text-[11px] font-mono text-ink-secondary/70 shrink-0">
                          #{app.id.slice(0, 8)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-1.5 mt-0.5">
                        <p className="text-xs text-ink-secondary truncate">
                          {app.job_title}
                        </p>
                        <div className="shrink-0">
                          <StatusBadge status={app.status} size="sm" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Full Candidate Detail Dossier (8 Cols) */}
        <div className="lg:col-span-8 space-y-5">
          {/* Header Banner */}
          <div className="bg-surface rounded-card border border-subtle p-4 sm:p-4.5 shadow-card space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3.5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-lg bg-elevated border border-subtle text-accent font-bold text-sm sm:text-base flex items-center justify-center shrink-0">
                  {activeApp.candidate_name
                    ? activeApp.candidate_name
                        .split(' ')
                        .map((n) => n[0])
                        .join('')
                    : 'C'}
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                    <h2 className="text-lg sm:text-xl font-bold text-ink tracking-tight">
                      {activeApp.candidate_name || `Applicant #${activeApp.candidate_id.slice(0, 8)}`}
                    </h2>
                    <StatusBadge status={activeApp.status} size="sm" />
                  </div>
                  <div className="flex items-center gap-2 text-xs text-ink-secondary font-medium">
                    <span>{activeApp.job_title}</span>
                    <span>•</span>
                    <span className="font-mono text-ink-secondary/80">
                      App #{activeApp.id.slice(0, 8)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 flex-wrap">
                <Button
                  onClick={handleTriggerEvaluation}
                  disabled={isEvaluating || isResolvingPrereq}
                  isLoading={isEvaluating || isResolvingPrereq}
                  variant="primary"
                  size="sm"
                  leftIcon={<Play className="w-3.5 h-3.5 fill-current" />}
                  className="font-semibold"
                >
                  <span>{isResolvingPrereq ? 'Extracting...' : (evaluation ? 'Re-Screen Evidence' : 'Screen Evidence')}</span>
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

            {/* Dossier Tabs: Compact, evenly spaced, readable */}
            <div className="flex items-center gap-2 pt-2.5 border-t border-subtle flex-wrap">
              {(['DETAILS', 'EVIDENCE', 'RESUME', 'INTERVIEW COACH', 'HIRING PIPELINE'] as const).map((tab) => {
                const tabLabel =
                  tab === 'DETAILS'
                    ? 'Details'
                    : tab === 'EVIDENCE'
                    ? 'Evidence'
                    : tab === 'RESUME'
                    ? 'Resume'
                    : tab === 'INTERVIEW COACH'
                    ? 'Interview Coach'
                    : 'Hiring Pipeline';
                return (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-3.5 py-1.5 rounded-md text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                      activeTab === tab
                        ? 'bg-elevated text-ink border border-subtle shadow-xs'
                        : 'text-ink-secondary hover:text-ink hover:bg-elevated/40 border border-transparent'
                    }`}
                  >
                    {tabLabel}
                  </button>
                );
              })}
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
            <div className="space-y-5">
              {/* Prerequisite Alert Banner */}
              {prereqRequired && (
                <div className="bg-surface rounded-card border border-amber-500/40 p-4 sm:p-4.5 shadow-card space-y-2.5">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                      <div className="space-y-0.5">
                        <h4 className="text-sm sm:text-base font-bold text-ink">
                          Prerequisite Required: Structured AI Claim Extraction
                        </h4>
                        <p className="text-xs sm:text-sm text-ink-secondary max-w-lg leading-relaxed">
                          Evidence screening requires structured candidate claims from the resume. The AI extraction pipeline has not completed for this resume yet.
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
                <div className="p-3.5 rounded-md bg-red-500/10 border border-red-500/30 text-xs sm:text-sm text-red-400 flex items-center justify-between">
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
                  <div className="space-y-3.5">
                    <div className="flex items-center justify-between pb-2.5 border-b border-subtle">
                      <h3 className="font-bold text-ink text-base">
                        Grounded Criteria Evaluations ({evaluation.criteria_evaluations.length})
                      </h3>
                      <span className="text-xs font-mono font-medium text-ink-secondary">
                        Run #{evaluation.extraction_run_id?.slice(0, 8)}
                      </span>
                    </div>

                    <div className="space-y-3.5">
                      {evaluation.criteria_evaluations.map((item) => (
                        <CriterionEvidenceCard
                          key={item.criterion_evidence_id || item.criterion_id}
                          item={item}
                          isReviewerOrEmployer={true}
                          onReviewDecision={handleReviewDecision}
                        />
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="bg-surface rounded-card border border-subtle p-8 text-center shadow-card space-y-3">
                  <FileText className="w-10 h-10 text-accent mx-auto opacity-70" />
                  <h3 className="text-base font-bold text-ink">Screening Evaluation Pending</h3>
                  <p className="text-xs sm:text-sm text-muted max-w-md mx-auto leading-relaxed">
                    This candidate application has not been evaluated against criteria benchmarks yet. Click "Screen Evidence" above or use the automated extraction workflow below.
                  </p>
                  <div className="flex flex-wrap items-center justify-center gap-2.5 mt-2">
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
              <div className="bg-surface rounded-card border border-subtle p-4 sm:p-5 shadow-card space-y-3.5">
                <div className="flex items-center justify-between pb-2.5 border-b border-subtle">
                  <div>
                    <h3 className="font-bold text-ink text-base">Adjudication Notes</h3>
                    <p className="text-xs text-ink-secondary font-medium mt-0.5">
                      Internal reviewer determinations and rationale logs
                    </p>
                  </div>
                  <Button
                    onClick={() => setShowAddNote(!showAddNote)}
                    variant="secondary"
                    size="sm"
                  >
                    {showAddNote ? 'Cancel' : '+ Add Note'}
                  </Button>
                </div>

                {showAddNote && (
                  <div className="p-3.5 rounded-md bg-elevated border border-subtle space-y-2.5">
                    <textarea
                      value={newNoteText}
                      onChange={(e) => setNewNoteText(e.target.value)}
                      placeholder="Add an internal reviewer note or observation regarding candidate evidence..."
                      rows={3}
                      className="w-full bg-surface border border-subtle rounded-md p-3 text-sm text-ink placeholder:text-muted focus:outline-none focus:border-accent resize-none font-medium leading-relaxed"
                    />
                    <div className="flex justify-end gap-2">
                      <Button
                        onClick={() => setShowAddNote(false)}
                        variant="secondary"
                        size="sm"
                      >
                        Cancel
                      </Button>
                      <Button onClick={handleAddNote} variant="primary" size="sm">
                        Save Note
                      </Button>
                    </div>
                  </div>
                )}

                {notes.length === 0 ? (
                  <div className="text-center py-5 text-ink-secondary text-xs sm:text-sm font-medium">
                    No reviewer notes recorded for this candidate dossier yet.
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {notes.map((note) => (
                      <div key={note.id} className="p-3 rounded-md bg-elevated border border-subtle space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-ink">{note.author}</span>
                          <span className="text-ink-secondary font-medium">{note.time}</span>
                        </div>
                        <p className="text-xs sm:text-sm text-ink/90 font-normal leading-relaxed">{note.text}</p>
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

          {/* Tab Content: INTERVIEW COACH */}
          {activeTab === 'INTERVIEW COACH' && (
            <InterviewTranscriptSection applicationId={activeApp.id} isCandidate={false} />
          )}

          {/* Tab Content: HIRING PIPELINE */}
          {activeTab === 'HIRING PIPELINE' && (
            <div className="bg-surface rounded-card border border-subtle p-4 sm:p-5 shadow-card space-y-4">
              <h3 className="font-bold text-ink text-base sm:text-lg">Hiring Workflow Status</h3>
              <div className="space-y-2.5 text-xs sm:text-sm">
                <div className="flex justify-between items-center py-2 border-b border-subtle">
                  <span className="text-ink-secondary font-medium">Current Application Status:</span>
                  <StatusBadge status={activeApp.status} size="sm" />
                </div>
                <div className="flex justify-between items-center py-2 border-b border-subtle">
                  <span className="text-ink-secondary font-medium">Submission Date:</span>
                  <span className="text-ink font-semibold">
                    {new Date(activeApp.submitted_at || activeApp.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-ink-secondary font-medium">Target Requisition:</span>
                  <span className="text-ink font-semibold">{activeApp.job_title}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

};
