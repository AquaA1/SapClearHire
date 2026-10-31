# ClearHire Frontend Page Map & Route Architecture

> **Document Status:** Complete & Verified  
> **Target Framework:** React 18+ / React Router v6+ with TypeScript  
> **Destination Path:** `frontend/src/`  
> **Date of Audit:** October 2026  

---

## 1. Page Architecture & Classification Strategy

To avoid architectural bloat and confusing deep-nesting, the ClearHire frontend classifies every user interface view into one of five distinct structural types:

1. **Full Page (Independent Route):** A primary destination with a dedicated URL and persistent navigation shell (e.g. `/employer/jobs`).
2. **Detail Page (Dynamic Route):** A resource-centric view parameterized by an entity identifier (e.g. `/reviewer/cases/:caseId`).
3. **Tab / Subview:** In-page contextual switching that shares state with a parent route (e.g. "Criteria Definition" tab inside Job Details).
4. **Modal / Dialog:** Contextual overlays for focused, transactional operations (e.g. Upload Resume, Clarification Contest, Decision Verdict).
5. **Shared Layout:** Structural wrappers providing authenticated header, sidebar navigation, tenant context, and breadcrumbs.

---

## 2. Page Inventory Summary

- **Total Independent Routable Pages:** `26`
- **Total MVP Priority 0 (P0) Pages:** `17`
- **Total Post-MVP / Core (P1) Pages:** `8`
- **Total Polish / Benchmark (P2) Pages:** `1`
- **Total Modal Dialogs:** `5`
- **Total Shared Layout Wrappers:** `5`

### Breakdown by Portal / Role
| Portal / Category | Role Permission | Total Routes | MVP (P0) | P1 / P2 | Primary Focus |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Public & Authentication** | Unauthenticated | 5 | 4 | 1 | Landing, Login, Candidate Registration, Error routes |
| **Candidate Portal** | `candidate` | 6 | 4 | 2 | Job discovery, resume upload, application tracking, evidence inspection, clarification submission |
| **Employer Portal** | `employer_admin` | 7 | 5 | 2 | Job creation, criteria weighting, candidate screening, evaluation trigger, team provisioning |
| **Reviewer Portal** | `reviewer`, `employer_admin` | 3 | 3 | 0 | Queue triage, evidence inspection, source quote verification, decision studio with mandatory rationale |
| **Auditor Portal** | `system_auditor`, `employer_admin`| 4 | 1 | 3 | Hash-chain verification report, event ledger, state delta inspector |
| **Simulation & Benchmark**| Cross-role / Admin | 1 | 0 | 1 | ATS keyword baseline vs ClearHire evidence matching comparison |
| **Total** | | **26** | **17** | **9** | |

---

## 3. Comprehensive Master Page Catalog

### 3.1 Public & Authentication Pages
| ID | Page Name | Route Path | Type | Role | Purpose | Required Components | Connected APIs | MVP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **P-01** | Landing Page | `/` | Full Page | Public | Product overview, value prop, entry points | HeroSection, FeatureGrid, EvidenceDemoPreview, PublicNavbar | None | P1 |
| **P-02** | Candidate Login | `/login` | Full Page | Public | Credential authentication & role redirection | LoginForm, AlertBanner, RoleSelectorGuide | `POST /auth/login`, `GET /auth/me` | **P0** |
| **P-03** | Candidate Registration | `/register` | Full Page | Public | First-party candidate account registration | RegisterForm, PasswordStrengthMeter, TermsNotice | `POST /auth/register`, `POST /auth/login` | **P0** |
| **P-04** | Access Denied | `/access-denied` | Full Page | Public / Auth | Displays 403 Forbidden message with role hint | ErrorState, NavigationActionButtons | None | **P0** |
| **P-05** | Not Found | `/*` | Full Page | Public | Displays 404 Route Not Found message | ErrorState, ReturnHomeButton | None | **P0** |

---

### 3.2 Candidate Portal (`role: candidate`)
| ID | Page Name | Route Path | Type | Role | Purpose | Required Components | Connected APIs | MVP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **C-01** | Candidate Dashboard | `/candidate/dashboard` | Full Page | `candidate` | Overview of active applications, status indicators, action items | StatCards, RecentApplicationsList, ActionItemBadge, QuickApplyBanner | `GET /applications`, `GET /auth/me` | **P0** |
| **C-02** | Job Discovery | `/candidate/jobs` | Full Page | `candidate` | Search active job openings | SearchFilterBar, JobCardGrid, DepartmentFilter, Pagination | `GET /jobs` (status=active) | **P0** |
| **C-03** | Job Details & Apply | `/candidate/jobs/:jobId` | Detail Page | `candidate` | View job description, criteria, and apply | JobHeader, CriteriaList, ApplyDrawerButton, RequirementsAccordion | `GET /jobs/:id`, `POST /documents`, `POST /applications` | **P0** |
| **C-04** | My Applications | `/candidate/applications` | Full Page | `candidate` | Complete list of candidate's submitted applications | ApplicationsTable, StatusBadge, ApplicationRowActions | `GET /applications` | P1 |
| **C-05** | Application Evidence View | `/candidate/applications/:applicationId` | Detail Page | `candidate` | Inspect criterion evaluation, grounding quotes, and contest evidence | EvaluationCoverageCard, CriterionEvidenceCard, SourceExcerptBox, ClarifyButton | `GET /applications/:id`, `GET /evaluations/:id`, `POST /applications/:id/clarifications` | **P0** |
| **C-06** | Skill & Profile Inventory | `/candidate/profile` | Full Page | `candidate` | View verified skill inventory extracted from resumes | SkillTagCloud, ConfidenceIndicator, SourcePageRef, ProfileSummary | `GET /profiles/:id/skills`, `GET /auth/me` | P1 |

#### Candidate Modals & Subviews
- **`M-C1` Resume Upload & Extraction Modal:** Handles drag-and-drop PDF upload, progress bar, OCR polling (`POST /documents`, `GET /documents/:id/status`, `POST /documents/:id/extract`).
- **`M-C2` Clarification Submission Modal:** Allows candidate to submit an explanatory statement and supplementary PDF against an ambiguous/missing criterion (`POST /applications/:id/clarifications`).

---

### 3.3 Employer Portal (`role: employer_admin`)
| ID | Page Name | Route Path | Type | Role | Purpose | Required Components | Connected APIs | MVP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **E-01** | Employer Dashboard | `/employer/dashboard` | Full Page | `employer_admin` | Requisition metrics, pending screenings, review flags count | MetricCards, PendingScreeningsTable, FlaggedCasesWidget, QuickActions | `GET /jobs`, `GET /applications`, `GET /review-flags` | **P0** |
| **E-02** | Job Requisitions List | `/employer/jobs` | Full Page | `employer_admin` | Manage organization job requisitions | DataTable, StatusFilter, CreateJobButton, RequisitionRowActions | `GET /jobs` | **P0** |
| **E-03** | Create Job Requisition | `/employer/jobs/new` | Full Page | `employer_admin` | Create requisition with versioned criteria & weights | MultiStepForm, CriteriaBuilderTable, WeightSlider, PreviewCard | `POST /jobs` | **P0** |
| **E-04** | Job Requisition Details | `/employer/jobs/:jobId` | Detail Page | `employer_admin` | View job criteria versions and applicants | CriteriaTable, VersionBadge, ApplicantsSubTable, JobMetaHeader | `GET /jobs/:id`, `GET /applications?job_id=:id` | **P0** |
| **E-05** | Applicants Management | `/employer/applications` | Full Page | `employer_admin` | Organization-wide candidate applications list | ApplicantsFilterTable, StatusFilter, JobSelectorDropdown, BulkEvaluateButton | `GET /applications`, `GET /jobs` | P1 |
| **E-06** | Candidate Evidence Dossier | `/employer/applications/:applicationId` | Detail Page | `employer_admin` | Detailed evidence dossier, coverage breakdown, trigger evaluation, auto-flagging | EvidenceDossier, CoverageBreakdown, TriggerEvalButton, AutoFlagButton, ClarificationHistory | `GET /applications/:id`, `GET /evaluations/:id`, `POST /evaluations`, `POST /review-flags` | **P0** |
| **E-07** | Team & User Provisioning | `/employer/team` | Full Page | `employer_admin` | Provision reviewer and employer admin accounts | TeamTable, ProvisionUserModal, RoleBadge, TenantNotice | `POST /auth/provision` | P1 |

#### Employer Modals & Subviews
- **`M-E1` Manual Review Flag Dialog:** Raise a targeted human review flag on a specific criterion (`POST /review-flags`).
- **`M-E2` User Provisioning Modal:** Form for employer admin to invite reviewers to their tenant (`POST /auth/provision`).

---

### 3.4 Reviewer Portal (`role: reviewer`, `employer_admin`)
| ID | Page Name | Route Path | Type | Role | Purpose | Required Components | Connected APIs | MVP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **R-01** | Reviewer Dashboard | `/reviewer/dashboard` | Full Page | `reviewer` | Assigned review workload, priority breakdown, recent decisions | WorkloadStats, UrgencyAlert, AssignedCasesSummary, DecisionAuditTimeline | `GET /review-flags`, `GET /auth/me` | **P0** |
| **R-02** | Review Cases Queue | `/reviewer/queue` | Full Page | `reviewer` | Assigned and unassigned review cases triage | QueueFilterTable, PriorityBadge, CriterionNameColumn, StatusFilterTabs | `GET /review-flags` (status filter) | **P0** |
| **R-03** | Evidence Inspection & Decision Studio | `/reviewer/cases/:caseId` | Detail Page | `reviewer` | Side-by-side evidence inspection, candidate clarifications, decision rationale entry | SplitEvidenceViewer, SourceQuoteCard, PageCoordsBox, ClarificationThread, DecisionFormPanel | `GET /reviews/:id`, `POST /reviews/:id/decision` | **P0** |

#### Reviewer Modals & Subviews
- **`M-R1` Request Clarification Dialog:** Prompt reviewer for specific clarification questions sent back to the candidate (`POST /reviews/:id/decision` with decision=`requested_clarification`).

---

### 3.5 Auditor Portal (`role: system_auditor`, `employer_admin`)
| ID | Page Name | Route Path | Type | Role | Purpose | Required Components | Connected APIs | MVP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A-01** | Audit Dashboard | `/auditor/dashboard` | Full Page | `system_auditor` | High-level audit metrics, event throughput, chain health indicator | ChainHealthCard, EventThroughputChart, QuickVerifyButton, RecentEventsFeed | `GET /audit`, `GET /audit/verify` | P1 |
| **A-02** | Audit Ledger & Explorer | `/auditor/events` | Full Page | `system_auditor` | Paginated immutable audit ledger with multi-attribute filtering | AuditDataTable, ResourceFilter, ActorFilter, HashBadge, DateRangePicker | `GET /audit` | P1 |
| **A-03** | Audit Event Inspector | `/auditor/events/:eventId` | Detail Page | `system_auditor` | Deep inspection of single event payload, diff, previous hash link | JSONStateDiffViewer, HashVerificationBadge, CanonicalPayloadView, MetaGrid | `GET /audit/:id` | P1 |
| **A-04** | Cryptographic Hash-Chain Verification Report | `/auditor/verification` | Full Page | `system_auditor` | Formal cryptographic audit report proving zero tampering | HashChainVerificationCard, BrokenLinkAlert, SequenceGauge, LegalDisclaimerCard | `GET /audit/verify` | **P0** |

---

### 3.6 Simulation & Benchmark Portal (Demonstration)
| ID | Page Name | Route Path | Type | Role | Purpose | Required Components | Connected APIs | MVP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **B-01** | Benchmark & Integration Explorer | `/benchmark` | Full Page | Cross-role / Admin | Interactive before/after screening benchmark and SuccessFactors feed simulator | BenchmarkMetricsGrid, ComparisonTable, FailureModeChart, SFFeedViewer, ImportButton | `GET /benchmark/run`, `POST /benchmark/run`, `GET /integrations/successfactors/feed`, `POST /integrations/successfactors/import` | P1 |

---

## 4. Minimum Viable Product (MVP) Scope Definition

The ClearHire platform cannot deliver on its core value proposition ("guaranteeing candidate evidence is never silently missed") without a functioning end-to-end evidence transparency loop:
1. Candidate finds job -> uploads resume -> applies.
2. Employer inspects job -> triggers deterministic evidence evaluation -> reviews factual coverage.
3. Ambiguous/missing criteria are auto-flagged into the Reviewer Queue.
4. Reviewer examines source excerpt & page coordinate -> records decision with mandatory rationale.
5. Candidate views verified criterion or submits clarification.
6. System Auditor runs cryptographic hash-chain verification to prove audit integrity.

### The 17 Mandatory MVP Pages
1. `/login` (Public)
2. `/register` (Public)
3. `/access-denied` (Public/System)
4. `/*` (Not Found / System)
5. `/candidate/dashboard` (Candidate)
6. `/candidate/jobs` (Candidate)
7. `/candidate/jobs/:jobId` (Candidate)
8. `/candidate/applications/:applicationId` (Candidate)
9. `/employer/dashboard` (Employer)
10. `/employer/jobs` (Employer)
11. `/employer/jobs/new` (Employer)
12. `/employer/jobs/:jobId` (Employer)
13. `/employer/applications/:applicationId` (Employer)
14. `/reviewer/dashboard` (Reviewer)
15. `/reviewer/queue` (Reviewer)
16. `/reviewer/cases/:caseId` (Reviewer)
17. `/auditor/verification` (Auditor)

### Deferred Pages (Post-MVP P1/P2)
- `/` (Marketing Landing Page — P1)
- `/candidate/applications` (Standalone application table; dashboard provides links — P1)
- `/candidate/profile` (Extracted skill summary; evidence view already provides claims — P1)
- `/employer/applications` (Standalone candidate table; job detail already lists applicants — P1)
- `/employer/team` (User provisioning; admin CLI/script can handle initially — P1)
- `/auditor/dashboard` & `/auditor/events` (Auditor ledger; `/auditor/verification` provides core proof — P1)
- `/auditor/events/:eventId` (Event inspector — P1)
- `/benchmark` (Synthetic benchmark comparison — P1)
