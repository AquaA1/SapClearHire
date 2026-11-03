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
import { ExpandableText } from '../ui/ExpandableText';

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
    <div className="space-y-5">
      {/* ── Candidate Contact & Target Header Card ────────────────── */}
      <div className="bg-surface rounded-card border border-subtle p-4 sm:p-5 shadow-card space-y-3.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3.5 pb-3.5 border-b border-subtle">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-elevated border border-subtle flex items-center justify-center text-accent font-bold text-base shrink-0">
              {candidateName
                ? candidateName
                    .split(' ')
                    .map((n: string) => n[0])
                    .join('')
                : 'C'}
            </div>
            <div>
              <h2 className="text-lg sm:text-xl font-bold text-ink">
                {candidateName}
              </h2>
              <div className="flex flex-wrap items-center gap-2 text-xs sm:text-sm text-ink-secondary font-medium mt-0.5">
                <Mail className="w-3.5 h-3.5 text-ink-secondary" />
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
                <span className="font-mono text-xs">ID: #{application.candidate_id.slice(0, 8)}</span>
              </div>
            </div>
          </div>

          <div className="text-right sm:border-l sm:border-subtle sm:pl-4 space-y-0.5">
            <span className="text-[11px] text-ink-secondary font-semibold uppercase tracking-wider block">
              Applied Requisition
            </span>
            <span className="text-xs sm:text-sm font-bold text-ink block">
              {application.job_title}
            </span>
            <span className="text-[11px] text-ink-secondary font-medium block">
              Submitted {new Date(application.submitted_at || application.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>

        {/* ── Compact AI Extraction Disclaimer Notice ─────────────── */}
        <div className="p-3 rounded-lg bg-elevated/60 border border-subtle text-xs flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2 text-ink-secondary">
            <Sparkles className="w-4 h-4 text-accent shrink-0" />
            <span className="font-semibold text-ink">AI Extraction Notice:</span>
            <span>Deterministic resume claim extraction. All items grounded with original page citations.</span>
          </div>
          <span className="text-[11px] bg-surface px-2 py-0.5 rounded border border-subtle text-ink-secondary font-mono font-medium shrink-0">
            Unverified
          </span>
        </div>

        {summary && (
          <div className="p-3 rounded-lg bg-elevated/40 border border-subtle space-y-1">
            <span className="text-xs font-semibold text-ink-secondary uppercase tracking-wider block">
              Professional Summary
            </span>
            <p className="text-ink/90 text-xs sm:text-sm leading-relaxed italic">
              "{summary}"
            </p>
          </div>
        )}
      </div>

      {/* ── Active Extraction Banner ─────────────────────────────── */}
      {(isExtracting || extractionRun?.status === 'queued' || extractionRun?.status === 'processing') && (
        <div className="p-3.5 rounded-lg bg-accent-dim/30 border border-accent/40 text-xs sm:text-sm flex items-center justify-between gap-3 shadow-sm">
          <div className="flex items-center gap-3">
            <LoadingSpinner size="sm" />
            <div>
              <span className="font-bold text-ink block text-sm">
                AI Claim Extraction in Progress...
              </span>
              <span className="text-ink-secondary text-xs block">
                Parsing structured qualifications, validating source grounding, and checking chronological consistency.
              </span>
            </div>
          </div>
          <span className="text-xs font-mono font-bold text-accent bg-surface px-2.5 py-1 rounded-md border border-accent/30">
            {extractionRun?.status?.toUpperCase() || 'EXTRACTING'}
          </span>
        </div>
      )}

      {/* ── Failed State Banner ──────────────────────────────────── */}
      {extractionRun && extractionRun.status === 'failed' && (
        <div className="bg-surface rounded-card border border-red-500/30 p-4 sm:p-5 shadow-card space-y-2.5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h3 className="text-sm sm:text-base font-bold text-ink">AI Claim Extraction Failed</h3>
                <p className="text-xs sm:text-sm text-ink-secondary max-w-lg leading-relaxed">
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
        <div className="space-y-5">
          {/* 1. Skills Inventory */}
          <div className="bg-surface rounded-card border border-subtle p-4 sm:p-5 shadow-card space-y-3">
            <div className="flex items-center justify-between pb-2.5 border-b border-subtle">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-accent" />
                <h3 className="font-bold text-ink text-base">
                  Extracted Skills Inventory ({skills.length})
                </h3>
              </div>
              <span className="text-xs text-ink-secondary font-medium">
                Grounded to Original Page Coordinates
              </span>
            </div>

            {skills.length > 0 ? (
              <div className="space-y-3">
                {Object.entries(skillsByCategory).map(([category, catSkills]) => (
                  <div key={category} className="space-y-1.5">
                    <span className="text-xs font-semibold text-ink-secondary uppercase tracking-wider block">
                      {category} ({catSkills.length})
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {catSkills.map((skill) => (
                        <div
                          key={skill.id}
                          className="bg-elevated border border-subtle rounded-md px-2.5 py-1 flex items-center gap-1.5 text-xs sm:text-sm"
                          title={skill.source_excerpt ? `Excerpt: "${skill.source_excerpt}"` : undefined}
                        >
                          <span className="font-medium text-ink">{skill.skill_name}</span>
                          <span className="text-[11px] text-accent font-bold bg-surface px-1.5 py-0.5 rounded border border-subtle">
                            {Math.round(skill.confidence * 100)}%
                          </span>
                          {skill.source_page && (
                            <span className="text-[11px] text-ink-secondary bg-surface/50 px-1.5 py-0.5 rounded border border-subtle">
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
              <div className="text-center py-5 text-xs sm:text-sm text-ink-secondary italic">
                No distinct skills identified in this resume.
              </div>
            )}
          </div>

          {/* 2. Work Experience */}
          <div className="bg-surface rounded-card border border-subtle p-4 sm:p-5 shadow-card space-y-3">
            <div className="flex items-center justify-between pb-2.5 border-b border-subtle">
              <div className="flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-accent" />
                <h3 className="font-bold text-ink text-base">
                  Work History & Professional Experience ({experiences.length})
                </h3>
              </div>
              <span className="text-xs text-ink-secondary font-medium">Chronological Claims</span>
            </div>

            {experiences.length > 0 ? (
              <div className="space-y-3">
                {experiences.map((exp) => {
                  const meta = exp.raw_metadata || {};
                  return (
                    <div
                      key={exp.id}
                      className="p-3.5 sm:p-4 rounded-md bg-elevated/50 border border-subtle space-y-2"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <h4 className="font-bold text-ink text-sm sm:text-base">
                            {meta.job_title || exp.claim_text}
                          </h4>
                          <span className="text-xs sm:text-sm text-accent font-semibold">
                            {meta.company || 'Company Unspecified'}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 text-xs text-ink-secondary shrink-0">
                          <span className="flex items-center gap-1.5 font-medium bg-surface px-2 py-0.5 rounded border border-subtle">
                            <Calendar className="w-3 h-3 text-ink-secondary" />
                            {meta.start_date || 'N/A'} — {meta.is_current ? 'Present' : (meta.end_date || 'N/A')}
                          </span>
                          <span className="bg-surface px-2 py-0.5 rounded border border-subtle font-semibold text-ink">
                            Page {exp.source_page}
                          </span>
                        </div>
                      </div>

                      {/* Date Conflict Warning if flagged */}
                      {meta.date_conflict && (
                        <div className="p-2 rounded bg-warn-dim border border-warn/30 text-xs text-warn flex items-center gap-2">
                          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                          <span>Potential chronology conflict: {meta.date_conflict}</span>
                        </div>
                      )}

                      {/* Responsibilities */}
                      {meta.responsibilities && Array.isArray(meta.responsibilities) && meta.responsibilities.length > 0 && (
                        <ul className="list-disc list-inside text-xs sm:text-sm text-ink/90 space-y-1 pl-1">
                          {meta.responsibilities.map((resp: string, idx: number) => (
                            <li key={idx} className="leading-relaxed">
                              {resp}
                            </li>
                          ))}
                        </ul>
                      )}

                      {/* Source Excerpt */}
                      {exp.source_excerpt && (
                        <div className="pt-1.5 border-t border-subtle/60">
                          <ExpandableText
                            text={exp.source_excerpt}
                            maxChars={180}
                            quote
                            italic
                            className="text-xs text-ink-secondary bg-surface/40 p-2.5 rounded"
                            expandLabel="View source excerpt"
                            collapseLabel="Collapse excerpt"
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-5 text-xs sm:text-sm text-ink-secondary italic">
                No formal work experience claims extracted from resume.
              </div>
            )}
          </div>

          {/* 3. Education */}
          <div className="bg-surface rounded-card border border-subtle p-4 sm:p-5 shadow-card space-y-3">
            <div className="flex items-center justify-between pb-2.5 border-b border-subtle">
              <div className="flex items-center gap-2">
                <GraduationCap className="w-4 h-4 text-accent" />
                <h3 className="font-bold text-ink text-base">
                  Education & Academic Credentials ({educations.length})
                </h3>
              </div>
              <span className="text-xs text-ink-secondary font-medium">Academic History</span>
            </div>

            {educations.length > 0 ? (
              <div className="space-y-2.5">
                {educations.map((edu) => {
                  const meta = edu.raw_metadata || {};
                  return (
                    <div
                      key={edu.id}
                      className="p-3 sm:p-3.5 rounded-md bg-elevated/50 border border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-2.5"
                    >
                      <div>
                        <h4 className="font-bold text-ink text-sm sm:text-base">
                          {meta.degree || edu.claim_text}
                        </h4>
                        <div className="text-xs sm:text-sm text-ink-secondary mt-0.5">
                          <span className="text-accent font-semibold">{meta.institution || 'Institution Unspecified'}</span>
                          {meta.field_of_study && <span> • {meta.field_of_study}</span>}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-xs text-ink-secondary shrink-0">
                        {meta.graduation_year && (
                          <span className="bg-surface px-2.5 py-0.5 rounded border border-subtle font-semibold">
                            Class of {meta.graduation_year}
                          </span>
                        )}
                        <span className="bg-surface px-2.5 py-0.5 rounded border border-subtle font-bold text-ink">
                          Page {edu.source_page}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-5 text-xs sm:text-sm text-ink-secondary italic">
                No academic degree claims detected in resume.
              </div>
            )}
          </div>

          {/* 4. Projects & Certifications Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Projects */}
            <div className="bg-surface rounded-card border border-subtle p-4 sm:p-4.5 shadow-card space-y-3">
              <div className="flex items-center gap-2 pb-2 border-b border-subtle">
                <FolderGit2 className="w-4 h-4 text-accent" />
                <h3 className="font-bold text-ink text-sm sm:text-base">Projects ({projects.length})</h3>
              </div>

              {projects.length > 0 ? (
                <div className="space-y-2.5">
                  {projects.map((proj) => {
                    const meta = proj.raw_metadata || {};
                    return (
                      <div key={proj.id} className="p-3 rounded-md bg-elevated/50 border border-subtle space-y-1">
                        <div className="flex items-center justify-between text-xs sm:text-sm">
                          <strong className="text-ink font-bold">{meta.project_name || proj.claim_text}</strong>
                          <span className="text-[11px] text-ink-secondary font-semibold">p.{proj.source_page}</span>
                        </div>
                        {meta.technologies && (
                          <span className="text-xs text-accent font-semibold block">
                            Tech: {Array.isArray(meta.technologies) ? meta.technologies.join(', ') : meta.technologies}
                          </span>
                        )}
                        {meta.description && (
                          <p className="text-xs text-ink-secondary leading-relaxed line-clamp-2">{meta.description}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-5 text-xs sm:text-sm text-ink-secondary italic">
                  No individual projects detected in resume.
                </div>
              )}
            </div>

            {/* Certifications */}
            <div className="bg-surface rounded-card border border-subtle p-4 sm:p-4.5 shadow-card space-y-3">
              <div className="flex items-center gap-2 pb-2 border-b border-subtle">
                <Award className="w-4 h-4 text-accent" />
                <h3 className="font-bold text-ink text-sm sm:text-base">Certifications ({certifications.length})</h3>
              </div>

              {certifications.length > 0 ? (
                <div className="space-y-2.5">
                  {certifications.map((cert) => {
                    const meta = cert.raw_metadata || {};
                    return (
                      <div key={cert.id} className="p-3 rounded-md bg-elevated/50 border border-subtle space-y-1">
                        <div className="flex items-center justify-between text-xs sm:text-sm">
                          <strong className="text-ink font-bold">{meta.certification_name || cert.claim_text}</strong>
                          <span className="text-[11px] text-ink-secondary font-semibold">p.{cert.source_page}</span>
                        </div>
                        {meta.issuing_organization && (
                          <span className="text-xs text-accent font-semibold block">
                            Issuer: {meta.issuing_organization}
                          </span>
                        )}
                        {meta.issue_date && (
                          <span className="text-xs text-ink-secondary block">Issued: {meta.issue_date}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-5 text-xs sm:text-sm text-ink-secondary italic">
                  No certifications detected in resume.
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* ── Fallback State: Structured Claims Not Yet Extracted ───── */
        <div className="space-y-5">
          <div className="bg-surface rounded-card border border-subtle p-4 sm:p-5 shadow-card space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-ink">Structured Claim Extraction Pending</h3>
                <p className="text-xs sm:text-sm text-ink-secondary mt-0.5 max-w-lg leading-relaxed">
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
          <div className="bg-surface rounded-card border border-subtle p-4 sm:p-5 shadow-card space-y-3">
            <div className="flex items-center justify-between pb-2.5 border-b border-subtle">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-accent" />
                <h3 className="font-bold text-ink text-base">
                  Verbatim Extracted Resume Text (PyMuPDF)
                </h3>
              </div>
              <span className="text-xs text-ink-secondary font-semibold">
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
                    className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                      selectedRawPage === pageNum
                        ? 'bg-accent text-surface shadow-xs'
                        : 'bg-elevated text-ink-secondary hover:text-ink border border-subtle'
                    }`}
                  >
                    Page {pageNum}
                  </button>
                ))}
              </div>
            )}

            <div className="bg-elevated/60 border border-subtle rounded-md p-4 max-h-[400px] overflow-y-auto font-mono text-xs sm:text-sm text-ink/90 whitespace-pre-wrap leading-relaxed select-text">
              {docStatus?.extracted_text_by_page?.[selectedRawPage] || (
                <span className="text-ink-secondary italic">
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
