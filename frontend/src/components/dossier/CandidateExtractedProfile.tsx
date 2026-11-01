import React, { useEffect, useState } from 'react';
import { documentService } from '../../services/api/documentService';
import { profileService } from '../../services/api/profileService';
import {
  Application,
  ExtractionRunResponse,
  CandidateSkill,
  EvidenceItem,
  DocumentStatusResponse,
} from '../../contracts/models';
import {
  User,
  Mail,
  Briefcase,
  GraduationCap,
  Award,
  FolderGit2,
  Cpu,
  Calendar,
  AlertTriangle,
  FileText,
  Play,
  CheckCircle2,
  Clock,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { Button, LoadingSpinner, StatusBadge } from '../ui';

interface CandidateExtractedProfileProps {
  application: Application;
  documentId: string;
}

export const CandidateExtractedProfile: React.FC<CandidateExtractedProfileProps> = ({
  application,
  documentId,
}) => {
  const [extractionRun, setExtractionRun] = useState<ExtractionRunResponse | null>(null);
  const [docStatus, setDocStatus] = useState<DocumentStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [selectedRawPage, setSelectedRawPage] = useState<string>('1');

  const startPolling = (docId: string) => {
    setIsExtracting(true);
    let attempts = 0;
    const maxAttempts = 30; // 45 seconds total
    const interval = setInterval(async () => {
      attempts += 1;
      try {
        const pollRes = await documentService.getExtractionResults(docId);
        setExtractionRun(pollRes);
        if (pollRes.status === 'completed' || pollRes.status === 'failed' || attempts >= maxAttempts) {
          clearInterval(interval);
          setIsExtracting(false);
        }
      } catch {
        if (attempts >= maxAttempts) {
          clearInterval(interval);
          setIsExtracting(false);
        }
      }
    }, 1500);
  };

  useEffect(() => {
    let isCancelled = false;

    const loadExtractedData = async () => {
      setLoading(true);
      setError(null);

      try {
        // Fetch extraction results
        try {
          const results = await documentService.getExtractionResults(documentId);
          if (!isCancelled) {
            setExtractionRun(results);
            if (results.status === 'queued' || results.status === 'processing') {
              startPolling(documentId);
            }
          }
        } catch {
          // If 404, extraction has not run yet. Fetch raw document status as fallback
          if (!isCancelled) {
            setExtractionRun(null);
          }
        }

        // Also fetch raw document status for page text fallback and metadata
        try {
          const status = await documentService.getDocumentStatus(documentId);
          if (!isCancelled) {
            setDocStatus(status);
            const pages = Object.keys(status.extracted_text_by_page || {});
            if (pages.length > 0) {
              setSelectedRawPage(pages[0]);
            }
          }
        } catch (statusErr: any) {
          console.warn('Failed to fetch document status:', statusErr);
        }
      } catch (err: any) {
        if (!isCancelled) {
          setError(err?.message || 'Failed to load candidate extracted information');
        }
      } finally {
        if (!isCancelled) {
          setLoading(false);
        }
      }
    };

    if (documentId) {
      loadExtractedData();
    }

    return () => {
      isCancelled = true;
    };
  }, [documentId]);

  const handleTriggerExtraction = async () => {
    if (!documentId) return;
    setIsExtracting(true);
    setError(null);
    try {
      const res = await documentService.triggerAIExtraction(documentId);
      setExtractionRun(res);
      if (res.status === 'completed') {
        setIsExtracting(false);
      } else {
        startPolling(documentId);
      }
    } catch (err: any) {
      console.error('Extraction trigger failed:', err);
      setIsExtracting(false);
      setError(err?.message || 'Failed to trigger AI claim extraction');
    }
  };

  if (loading) {
    return (
      <div className="bg-surface rounded-card border border-subtle p-12 text-center shadow-card space-y-4">
        <LoadingSpinner size="lg" label="Loading candidate extracted profile..." />
        <p className="text-xs text-muted max-w-sm mx-auto">
          Parsing structured claims, skills inventory, and page references...
        </p>
      </div>
    );
  }

  // Group evidence items by item_type from raw_metadata
  const evidenceItems = extractionRun?.evidence_items || [];
  const experiences = evidenceItems.filter(
    (e) => e.raw_metadata?.item_type === 'experience'
  );
  const educations = evidenceItems.filter(
    (e) => e.raw_metadata?.item_type === 'education'
  );
  const projects = evidenceItems.filter(
    (e) => e.raw_metadata?.item_type === 'project'
  );
  const certifications = evidenceItems.filter(
    (e) => e.raw_metadata?.item_type === 'certification'
  );

  // Group skills by category
  const skills = extractionRun?.skills || [];
  const skillsByCategory: Record<string, CandidateSkill[]> = {};
  skills.forEach((skill) => {
    const cat = skill.category || 'General & Core Skills';
    if (!skillsByCategory[cat]) skillsByCategory[cat] = [];
    skillsByCategory[cat].push(skill);
  });

  const rawPageEntries = Object.entries(docStatus?.extracted_text_by_page || {}).sort(
    ([a], [b]) => parseInt(a, 10) - parseInt(b, 10)
  );

  const rawOutput = extractionRun?.raw_output;
  const candidateName = rawOutput?.candidate_name || application.candidate_name || `Candidate #${application.candidate_id.slice(0, 8)}`;
  const contactInfo = rawOutput?.contact_information || {};
  const summary = rawOutput?.summary;

  return (
    <div className="space-y-6">
      {/* ── Candidate Contact & Target Header Card ────────────────── */}
      <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-subtle">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded bg-elevated border border-subtle flex items-center justify-center text-accent font-semibold text-base">
              {candidateName
                ? candidateName
                    .split(' ')
                    .map((n: string) => n[0])
                    .join('')
                : 'C'}
            </div>
            <div>
              <h2 className="text-base font-semibold text-ink">
                {candidateName}
              </h2>
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted font-medium mt-0.5">
                <Mail className="w-3.5 h-3.5 text-muted" />
                <span>{contactInfo.email || application.candidate_email || 'Email not provided'}</span>
                {contactInfo.phone && (
                  <>
                    <span>•</span>
                    <span>{contactInfo.phone}</span>
                  </>
                )}
                {contactInfo.location && (
                  <>
                    <span>•</span>
                    <span>{contactInfo.location}</span>
                  </>
                )}
                <span>•</span>
                <span className="font-mono text-[11px]">ID: #{application.candidate_id.slice(0, 8)}</span>
              </div>
            </div>
          </div>

          <div className="text-right sm:border-l sm:border-subtle sm:pl-5 space-y-1">
            <span className="text-[10px] text-muted font-semibold uppercase tracking-wider block">
              Applied Requisition
            </span>
            <span className="text-xs font-semibold text-ink block">
              {application.job_title}
            </span>
            <span className="text-[11px] text-muted font-medium block">
              Submitted {new Date(application.submitted_at || application.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>

        {/* ── Mandatory AI Extraction Disclaimer Banner ─────────────── */}
        <div className="p-3.5 rounded bg-elevated/80 border border-subtle text-xs flex items-start gap-3">
          <Sparkles className="w-4 h-4 text-accent shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-ink text-xs">
                AI-Extracted Profile Data (Unverified by Human Reviewer)
              </span>
              <span className="text-[10px] bg-surface px-2 py-0.5 rounded border border-subtle text-muted font-medium">
                Automated Extraction
              </span>
            </div>
            <p className="text-muted leading-relaxed">
              The claims, work history, and qualifications below were parsed automatically from the candidate's uploaded resume using deterministic extraction. All items maintain exact page references to the original document.
            </p>
          </div>
        </div>

        {summary && (
          <div className="p-3.5 rounded bg-elevated/50 border border-subtle text-xs space-y-1">
            <span className="text-[10px] text-muted font-semibold uppercase tracking-wider block">
              Professional Summary
            </span>
            <p className="text-ink/90 leading-relaxed italic">
              "{summary}"
            </p>
          </div>
        )}
      </div>

      {/* ── Active Extraction Banner ─────────────────────────────── */}
      {(isExtracting || extractionRun?.status === 'queued' || extractionRun?.status === 'processing') && (
        <div className="p-4 rounded bg-accent-dim/30 border border-accent/40 text-xs flex items-center justify-between gap-3 shadow-sm">
          <div className="flex items-center gap-3">
            <LoadingSpinner size="sm" />
            <div>
              <span className="font-semibold text-ink block">
                AI Claim Extraction in Progress...
              </span>
              <span className="text-muted text-[11px] block">
                Parsing structured qualifications, validating source grounding, and checking chronological consistency with Gemini AI.
              </span>
            </div>
          </div>
          <span className="text-[10px] font-mono font-semibold text-accent bg-surface px-2.5 py-1 rounded border border-accent/30">
            {extractionRun?.status?.toUpperCase() || 'EXTRACTING'}
          </span>
        </div>
      )}

      {/* ── Failed State Banner ──────────────────────────────────── */}
      {extractionRun && extractionRun.status === 'failed' && (
        <div className="bg-surface rounded-card border border-red-500/30 p-5 shadow-card space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-ink">AI Claim Extraction Failed</h3>
                <p className="text-xs text-muted max-w-lg leading-relaxed">
                  {extractionRun.error_message || error || 'The extraction worker encountered an error while processing the resume. Click retry below to execute extraction again.'}
                </p>
              </div>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleTriggerExtraction}
              isLoading={isExtracting}
              leftIcon={<Play className="w-3.5 h-3.5 fill-current" />}
              className="shrink-0 font-semibold"
            >
              Retry Claim Extraction
            </Button>
          </div>
        </div>
      )}

      {/* ── If Structured Claims Exist ─────────────────────────────── */}
      {extractionRun && extractionRun.status === 'completed' ? (
        <div className="space-y-6">
          {/* 1. Skills Inventory */}
          <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-subtle">
              <div className="flex items-center gap-2.5">
                <Cpu className="w-4 h-4 text-accent" />
                <h3 className="font-semibold text-ink text-sm">
                  Extracted Skills Inventory ({skills.length})
                </h3>
              </div>
              <span className="text-[11px] text-muted font-medium">
                Grounded to Original Page Coordinates
              </span>
            </div>

            {skills.length > 0 ? (
              <div className="space-y-4">
                {Object.entries(skillsByCategory).map(([category, catSkills]) => (
                  <div key={category} className="space-y-2">
                    <span className="text-[11px] font-semibold text-muted uppercase tracking-wider block">
                      {category} ({catSkills.length})
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {catSkills.map((skill) => (
                        <div
                          key={skill.id}
                          className="bg-elevated border border-subtle rounded px-2.5 py-1.5 flex items-center gap-2 text-xs"
                          title={skill.source_excerpt ? `Excerpt: "${skill.source_excerpt}"` : undefined}
                        >
                          <span className="font-medium text-ink">{skill.skill_name}</span>
                          <span className="text-[10px] text-accent font-semibold bg-surface px-1.5 py-0.5 rounded border border-subtle">
                            {Math.round(skill.confidence * 100)}%
                          </span>
                          {skill.source_page && (
                            <span className="text-[10px] text-muted bg-surface/50 px-1.5 py-0.5 rounded border border-subtle">
                              p.{skill.source_page}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-xs text-muted italic">
                No distinct skills identified in this resume.
              </div>
            )}
          </div>

          {/* 2. Work Experience */}
          <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-subtle">
              <div className="flex items-center gap-2.5">
                <Briefcase className="w-4 h-4 text-accent" />
                <h3 className="font-semibold text-ink text-sm">
                  Work History & Professional Experience ({experiences.length})
                </h3>
              </div>
              <span className="text-[11px] text-muted font-medium">Chronological Claims</span>
            </div>

            {experiences.length > 0 ? (
              <div className="space-y-4">
                {experiences.map((exp) => {
                  const meta = exp.raw_metadata || {};
                  return (
                    <div
                      key={exp.id}
                      className="p-4 rounded bg-elevated/50 border border-subtle space-y-2.5"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <h4 className="font-semibold text-ink text-xs">
                            {meta.job_title || exp.claim_text}
                          </h4>
                          <span className="text-xs text-accent font-medium">
                            {meta.company || 'Company Unspecified'}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 text-[11px] text-muted shrink-0">
                          <span className="flex items-center gap-1 font-medium bg-surface px-2 py-0.5 rounded border border-subtle">
                            <Calendar className="w-3 h-3 text-muted" />
                            {meta.start_date || 'N/A'} — {meta.is_current ? 'Present' : (meta.end_date || 'N/A')}
                          </span>
                          <span className="bg-surface px-2 py-0.5 rounded border border-subtle font-medium text-ink">
                            Page {exp.source_page}
                          </span>
                        </div>
                      </div>

                      {/* Date Conflict Warning if flagged */}
                      {meta.date_conflict && (
                        <div className="p-2 rounded bg-warn-dim border border-warn/30 text-[11px] text-warn flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                          <span>Potential chronology conflict: {meta.date_conflict}</span>
                        </div>
                      )}

                      {/* Responsibilities */}
                      {meta.responsibilities && Array.isArray(meta.responsibilities) && meta.responsibilities.length > 0 && (
                        <ul className="list-disc list-inside text-xs text-ink/80 space-y-1 font-medium pl-1">
                          {meta.responsibilities.map((resp: string, idx: number) => (
                            <li key={idx} className="leading-relaxed">
                              {resp}
                            </li>
                          ))}
                        </ul>
                      )}

                      {/* Source Excerpt */}
                      {exp.source_excerpt && (
                        <div className="pt-2 border-t border-subtle/60 text-[11px] text-muted italic font-mono bg-surface/40 p-2.5 rounded">
                          "{exp.source_excerpt}"
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-6 text-xs text-muted italic">
                No formal work experience claims extracted from resume.
              </div>
            )}
          </div>

          {/* 3. Education */}
          <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-subtle">
              <div className="flex items-center gap-2.5">
                <GraduationCap className="w-4 h-4 text-accent" />
                <h3 className="font-semibold text-ink text-sm">
                  Education & Academic Credentials ({educations.length})
                </h3>
              </div>
              <span className="text-[11px] text-muted font-medium">Academic History</span>
            </div>

            {educations.length > 0 ? (
              <div className="space-y-3">
                {educations.map((edu) => {
                  const meta = edu.raw_metadata || {};
                  return (
                    <div
                      key={edu.id}
                      className="p-4 rounded bg-elevated/50 border border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      <div>
                        <h4 className="font-semibold text-ink text-xs">
                          {meta.degree || edu.claim_text}
                        </h4>
                        <div className="text-xs text-muted mt-0.5">
                          <span className="text-accent font-medium">{meta.institution || 'Institution Unspecified'}</span>
                          {meta.field_of_study && <span> • {meta.field_of_study}</span>}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-[11px] text-muted shrink-0">
                        {meta.graduation_year && (
                          <span className="bg-surface px-2 py-0.5 rounded border border-subtle font-medium">
                            Class of {meta.graduation_year}
                          </span>
                        )}
                        <span className="bg-surface px-2 py-0.5 rounded border border-subtle font-medium text-ink">
                          Page {edu.source_page}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-6 text-xs text-muted italic">
                No academic degree claims detected in resume.
              </div>
            )}
          </div>

          {/* 4. Projects & Certifications Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Projects */}
            <div className="bg-surface rounded-card border border-subtle p-5 shadow-card space-y-3">
              <div className="flex items-center gap-2 pb-2 border-b border-subtle">
                <FolderGit2 className="w-4 h-4 text-accent" />
                <h3 className="font-semibold text-ink text-sm">Projects ({projects.length})</h3>
              </div>

              {projects.length > 0 ? (
                <div className="space-y-2.5">
                  {projects.map((proj) => {
                    const meta = proj.raw_metadata || {};
                    return (
                      <div key={proj.id} className="p-3 rounded bg-elevated/50 border border-subtle space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <strong className="text-ink font-semibold">{meta.project_name || proj.claim_text}</strong>
                          <span className="text-[10px] text-muted font-medium">p.{proj.source_page}</span>
                        </div>
                        {meta.technologies && (
                          <span className="text-[11px] text-accent block">
                            Tech: {Array.isArray(meta.technologies) ? meta.technologies.join(', ') : meta.technologies}
                          </span>
                        )}
                        {meta.description && (
                          <p className="text-[11px] text-muted line-clamp-2">{meta.description}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-6 text-xs text-muted italic">
                  No individual projects detected in resume.
                </div>
              )}
            </div>

            {/* Certifications */}
            <div className="bg-surface rounded-card border border-subtle p-5 shadow-card space-y-3">
              <div className="flex items-center gap-2 pb-2 border-b border-subtle">
                <Award className="w-4 h-4 text-accent" />
                <h3 className="font-semibold text-ink text-sm">Certifications ({certifications.length})</h3>
              </div>

              {certifications.length > 0 ? (
                <div className="space-y-2.5">
                  {certifications.map((cert) => {
                    const meta = cert.raw_metadata || {};
                    return (
                      <div key={cert.id} className="p-3 rounded bg-elevated/50 border border-subtle space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <strong className="text-ink font-semibold">{meta.certification_name || cert.claim_text}</strong>
                          <span className="text-[10px] text-muted font-medium">p.{cert.source_page}</span>
                        </div>
                        {meta.issuing_organization && (
                          <span className="text-[11px] text-accent block">
                            Issuer: {meta.issuing_organization}
                          </span>
                        )}
                        {meta.issue_date && (
                          <span className="text-[10px] text-muted block">Issued: {meta.issue_date}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-6 text-xs text-muted italic">
                  No certifications detected in resume.
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* ── Fallback State: Structured Claims Not Yet Extracted ───── */
        <div className="space-y-6">
          <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-semibold text-ink">Structured Claim Extraction Pending</h3>
                <p className="text-xs text-muted mt-1 max-w-lg leading-relaxed">
                  The AI pipeline has not generated structured qualification claims for this candidate resume yet. You can trigger claim extraction now or view the raw extracted text below.
                </p>
              </div>

              <Button
                variant="primary"
                size="sm"
                onClick={handleTriggerExtraction}
                isLoading={isExtracting}
                leftIcon={<Play className="w-3.5 h-3.5 fill-current" />}
                className="shrink-0 font-semibold"
              >
                Run Claim Extraction
              </Button>
            </div>
          </div>

          {/* Raw Extracted Text Page-by-Page View */}
          <div className="bg-surface rounded-card border border-subtle p-6 shadow-card space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-subtle">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-accent" />
                <h3 className="font-semibold text-ink text-sm">
                  Verbatim Extracted Resume Text (PyMuPDF)
                </h3>
              </div>
              <span className="text-[11px] text-muted font-medium">
                Page {selectedRawPage} of {rawPageEntries.length || 1}
              </span>
            </div>

            {/* Page Tabs */}
            {rawPageEntries.length > 0 && (
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
                {rawPageEntries.map(([pageNum]) => (
                  <button
                    key={pageNum}
                    type="button"
                    onClick={() => setSelectedRawPage(pageNum)}
                    className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
                      selectedRawPage === pageNum
                        ? 'bg-accent text-surface shadow-sm'
                        : 'bg-elevated text-muted hover:text-ink border border-subtle'
                    }`}
                  >
                    Page {pageNum}
                  </button>
                ))}
              </div>
            )}

            <div className="bg-elevated/60 border border-subtle rounded p-5 max-h-[450px] overflow-y-auto font-mono text-xs text-ink/90 whitespace-pre-wrap leading-relaxed select-text">
              {docStatus?.extracted_text_by_page?.[selectedRawPage] || (
                <span className="text-muted italic">
                  No extractable digital text found on Page {selectedRawPage}.
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
