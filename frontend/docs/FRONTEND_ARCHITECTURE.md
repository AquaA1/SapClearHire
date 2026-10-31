# ClearHire Frontend Architecture & Component Blueprint

> **Document Status:** Complete & Verified  
> **Target Framework:** React 18+ (or React 19) with TypeScript 5+ & Vite  
> **Target Directory:** `frontend/` (Strict isolation)  
> **Date of Audit:** October 2026  

---

## 1. Architectural Philosophy & Principles

The ClearHire frontend is designed around three strict architectural tenets:

1. **Evidence-First Human Centricity:** The UI must visually ground every qualification claim in verifiable evidence quotes and page coordinates. Opaque scores or unexplainable percentages are strictly forbidden by product philosophy.
2. **Two-Layer UI-First / API-Later Development:** UI components, layouts, state machines, and interactions are constructed against verified TypeScript contracts with isolated mock adapters before live backend connection.
3. **Fail-Fast Production Integrity:** Mock data must be strictly quarantined to development environments. In production, API errors must produce clear, user-actionable feedback rather than silently falling back to mock fixtures.

---

## 2. Directory & Folder Structure

All frontend assets, code, configuration, and documentation must reside exclusively inside `frontend/`.

```
frontend/
├── docs/                               # Architecture, API inventories, roadmaps (Created)
│   ├── API_INVENTORY.md
│   ├── FRONTEND_PAGE_MAP.md
│   ├── API_PAGE_MAPPING.md
│   ├── FRONTEND_ARCHITECTURE.md
│   ├── INTEGRATION_GAPS.md
│   └── IMPLEMENTATION_ROADMAP.md
├── public/                             # Static brand assets, logos, favicon
├── src/
│   ├── assets/                         # SVG icons, CSS styles, typography
│   │   └── styles/
│   │       ├── tailwind.css            # Tailwind CSS directives
│   │       └── variables.css           # SAP Fiori-inspired color tokens
│   ├── components/                     # Reusable UI component library
│   │   ├── shell/                      # Header, Sidebar, UserMenu, Breadcrumbs
│   │   ├── presentation/               # DataTable, Pagination, StatCard, StatusBadge
│   │   ├── evidence/                   # EvidenceCard, SourceQuoteBox, CoverageBar
│   │   ├── forms/                      # FormField, CriteriaEditor, FileDropzone
│   │   └── feedback/                   # SkeletonLoader, AlertBanner, Toast, Modal
│   ├── contracts/                      # Pure TypeScript types mirroring backend schemas
│   │   ├── enums.ts                    # EvidenceStatus, VerificationState, UserRole
│   │   ├── auth.ts                     # User, Token, ProvisionRequest
│   │   ├── jobs.ts                     # Job, JobCriterion
│   │   ├── applications.ts             # Application, ApplicationStatus
│   │   ├── evaluations.ts              # Evaluation, CriterionEvidence, Coverage
│   │   ├── reviews.ts                  # ReviewFlag, ReviewCaseDetail, Decision
│   │   └── audit.ts                    # AuditEvent, HashVerificationReport
│   ├── services/                       # Centralized Data Access Layer
│   │   ├── api/                        # HTTP client & endpoint adapters
│   │   │   ├── client.ts               # Axios / Fetch client with JWT interceptor
│   │   │   ├── auth.api.ts
│   │   │   ├── jobs.api.ts
│   │   │   ├── applications.api.ts
│   │   │   ├── evaluations.api.ts
│   │   │   ├── reviews.api.ts
│   │   │   └── audit.api.ts
│   │   └── mock/                       # Development-Only Mock Adapters
│   │       ├── mockServer.ts           # Adapter switcher (API vs Mock)
│   │       ├── fixtures/               # Realistic ground-truth mock datasets
│   │       │   ├── mockUsers.ts
│   │       │   ├── mockJobs.ts
│   │       │   ├── mockApplications.ts
│   │       │   ├── mockEvaluations.ts
│   │       │   ├── mockReviews.ts
│   │       │   └── mockAudit.ts
│   │       └── mockApiHandlers.ts
│   ├── hooks/                          # Custom React & TanStack Query hooks
│   │   ├── queries/                    # useJobs, useApplication, useReviewCase
│   │   ├── mutations/                  # useUploadResume, useSubmitDecision
│   │   └── useAuth.ts                  # Auth context wrapper
│   ├── layouts/                        # Shell layout wrappers
│   │   ├── PublicLayout.tsx            # Clean unauthenticated wrapper
│   │   ├── CandidateLayout.tsx         # Candidate portal header & nav
│   │   ├── EmployerLayout.tsx          # Employer admin sidebar & shell
│   │   ├── ReviewerLayout.tsx          # Focused review queue workspace
│   │   └── AuditorLayout.tsx           # Compliance & audit workspace
│   ├── pages/                          # Routable page views
│   │   ├── public/                     # Landing, Login, Register, Error pages
│   │   ├── candidate/                  # Dashboard, Job Discovery, Evidence View
│   │   ├── employer/                   # Dashboard, Jobs, Job Create, Candidate Dossier
│   │   ├── reviewer/                   # Dashboard, Queue, Decision Studio
│   │   ├── auditor/                    # Verification Report, Event Ledger
│   │   └── benchmark/                  # ATS Comparison & SF Simulation
│   ├── router/                         # React Router route hierarchy & guards
│   │   ├── index.tsx                   # Route tree
│   │   └── ProtectedRoute.tsx          # Role-based route guard
│   ├── stores/                         # Zustand client stores
│   │   ├── authStore.ts                # Active user, JWT, role state
│   │   └── uiStore.ts                  # Modals, toasts, sidebar toggle
│   ├── App.tsx                         # Root app with QueryClientProvider
│   └── main.tsx                        # Vite entry point
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

---

## 3. Technology Stack Recommendations

| Layer | Recommended Technology | Justification |
| :--- | :--- | :--- |
| **Framework** | **React 18.3+** with **TypeScript** | Type-safe ecosystem; seamless contract synchronization with Pydantic. |
| **Build Tool** | **Vite** | Sub-second HMR, optimal bundle splitting, standard for modern React apps. |
| **Routing** | **React Router v6.24+** | Industry standard nested route definitions and declarative auth guards. |
| **Server State** | **TanStack Query v5** | Automated background polling (crucial for OCR & AI extraction), cache invalidation. |
| **Client State** | **Zustand** | Minimalist, zero-boilerplate state for auth session, active tenant, and UI dialogs. |
| **HTTP Client** | **Axios** | Native interceptors for JWT injection, 401 refresh/redirect, uniform error mapping. |
| **Styling** | **Tailwind CSS** + **Lucide React** | High-velocity design system, enterprise SAP Fiori-inspired color palette. |
| **Validation** | **Zod** | Client-side form validation mirroring backend Pydantic field constraints. |

---

## 4. Reusable Component Inventory

### 4.1 Application Shell Components
| Component Name | File Path | Props / Responsibilities | Reused In |
| :--- | :--- | :--- | :--- |
| `AppHeader` | `components/shell/AppHeader.tsx` | Brand logo, active portal title, notifications bell, user menu | All authenticated layouts |
| `PortalSidebar` | `components/shell/PortalSidebar.tsx` | Role-filtered nav links, active route highlight, collapse toggle | Employer, Reviewer, Auditor layouts |
| `UserMenu` | `components/shell/UserMenu.tsx` | User name, role badge, email, tenant name, logout trigger | AppHeader |
| `RoleBadge` | `components/shell/RoleBadge.tsx` | Visual pill tag for `Candidate`, `Employer Admin`, `Reviewer`, `Auditor` | AppHeader, Tables, User profile |
| `Breadcrumbs` | `components/shell/Breadcrumbs.tsx` | Hierarchical route trail (e.g. Jobs > Senior Backend Eng > Applicants) | All detail pages |

### 4.2 Evidence & Transparency Interface Components
| Component Name | File Path | Props / Responsibilities | Reused In |
| :--- | :--- | :--- | :--- |
| `CoverageSummaryBar` | `components/evidence/CoverageSummaryBar.tsx` | Visual breakdown: total criteria, supported (green), ambiguous (yellow), not found (gray) | Candidate Evidence View, Employer Dossier |
| `CriterionEvidenceCard`| `components/evidence/CriterionEvidenceCard.tsx` | Criterion requirement, status tag, confidence score, excerpt callout | Candidate Evidence View, Reviewer Studio, Employer Dossier |
| `SourceExcerptBox` | `components/evidence/SourceExcerptBox.tsx` | Grounded resume text snippet with highlighted keyword matches and Page # tag | CriterionEvidenceCard, Reviewer Studio |
| `VerificationStateBadge`| `components/evidence/VerificationStateBadge.tsx`| Displays `UNVERIFIED`, `CANDIDATE_CLARIFIED`, `HUMAN_VERIFIED`, `HUMAN_REJECTED` | Review Queue, Evidence Cards, Applications |
| `ClarificationThread` | `components/evidence/ClarificationThread.tsx` | Timeline of candidate explanations, timestamp, supplementary document links | Reviewer Decision Studio, Candidate Evidence View |
| `DecisionAuditHistory` | `components/evidence/DecisionAuditHistory.tsx` | List of reviewer verdicts, reviewer ID, timestamp, and mandatory rationale text | Reviewer Decision Studio, Employer Dossier |

### 4.3 Data Presentation Components
| Component Name | File Path | Props / Responsibilities | Reused In |
| :--- | :--- | :--- | :--- |
| `DataTable` | `components/presentation/DataTable.tsx` | Generic sortable table with headers, loading states, empty state | Job list, Application list, Review queue, Audit ledger |
| `Pagination` | `components/presentation/Pagination.tsx` | Current page, total records, limit selector, next/previous buttons | All table pages |
| `StatCard` | `components/presentation/StatCard.tsx` | Metric title, numerical count, status icon, trend indicator | All role dashboards |
| `StatusBadge` | `components/presentation/StatusBadge.tsx` | Color-coded status for jobs (`active`, `draft`), applications (`submitted`, `screening`, `reviewed`), and flags | Across all portals |
| `EmptyState` | `components/presentation/EmptyState.tsx` | Illustrative icon, title, descriptive hint, primary action CTA | All tables & lists when zero items match |

### 4.4 Form & Input Components
| Component Name | File Path | Props / Responsibilities | Reused In |
| :--- | :--- | :--- | :--- |
| `FormField` | `components/forms/FormField.tsx` | Label, error message display, required asterisk, description tooltip | Login, Register, Job Create, Review Decision |
| `CriteriaEditor` | `components/forms/CriteriaEditor.tsx` | Dynamic array input for criteria names, category (`required`/`preferred`), weight slider | Create Job Requisition (`E-03`) |
| `FileDropzone` | `components/forms/FileDropzone.tsx` | Drag-and-drop PDF resume uploader with file type and 10MB size validation | Job Apply Modal, Resume Upload |
| `ReviewDecisionForm` | `components/forms/ReviewDecisionForm.tsx` | Verdict selector (`accepted`, `rejected`, `requested_clarification`) + mandatory rationale text area | Reviewer Decision Studio (`R-03`) |

### 4.5 Feedback & Dialog Components
| Component Name | File Path | Props / Responsibilities | Reused In |
| :--- | :--- | :--- | :--- |
| `SkeletonLoader` | `components/feedback/SkeletonLoader.tsx` | Pulse-animated placeholder blocks for text, cards, and tables | Loading states across all pages |
| `AlertBanner` | `components/feedback/AlertBanner.tsx` | Info, warning, success, or error alert banner with dismiss action | Form errors, banner notifications |
| `ConfirmDialog` | `components/feedback/ConfirmDialog.tsx` | Destructive or consequential action confirmation modal | Delete/Archive actions, Decision submit |
| `ToastContainer` | `components/feedback/ToastContainer.tsx` | Floating toast notifications for asynchronous actions | Global feedback |

---

## 5. TypeScript Data Contracts (Synchronized with Backend Schemas)

```typescript
// frontend/src/contracts/enums.ts

export enum UserRole {
  CANDIDATE = "candidate",
  EMPLOYER_ADMIN = "employer_admin",
  REVIEWER = "reviewer",
  SYSTEM_AUDITOR = "system_auditor",
}

export enum EvidenceStatus {
  SUPPORTED = "supported",
  NOT_FOUND = "not_found",
  AMBIGUOUS = "ambiguous",
}

export enum VerificationState {
  UNVERIFIED = "unverified",
  CANDIDATE_CLARIFIED = "candidate_clarified",
  HUMAN_VERIFIED = "human_verified",
  HUMAN_REJECTED = "human_rejected",
}

export enum ReviewDecisionType {
  ACCEPTED = "accepted",
  REJECTED = "rejected",
  REQUESTED_CLARIFICATION = "requested_clarification",
}

export enum DocumentProcessingStatus {
  QUEUED = "queued",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
}

export enum JobStatus {
  DRAFT = "draft",
  ACTIVE = "active",
  ARCHIVED = "archived",
}

export enum CriterionCategory {
  REQUIRED = "required",
  PREFERRED = "preferred",
}

export enum ApplicationStatus {
  SUBMITTED = "submitted",
  SCREENING = "screening",
  NEEDS_REVIEW = "needs_review",
  REVIEWED = "reviewed",
}

export enum ReviewFlagStatus {
  PENDING = "pending",
  UNDER_REVIEW = "under_review",
  RESOLVED = "resolved",
  DISMISSED = "dismissed",
}

export enum CorrectionRequestStatus {
  SUBMITTED = "submitted",
  UNDER_REVIEW = "under_review",
  ACCEPTED = "accepted",
  REJECTED = "rejected",
}
```

```typescript
// frontend/src/contracts/models.ts

export interface User {
  id: string;
  email: string;
  role: UserRole;
  full_name: string;
  employer_id: string | null;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
}

export interface JobCriterion {
  id: string;
  job_id: string;
  version: number;
  name: string;
  description: string | null;
  category: CriterionCategory | string;
  weight: number;
  is_active: boolean;
  created_at: string;
}

export interface Job {
  id: string;
  employer_id: string;
  title: string;
  description: string | null;
  department: string | null;
  status: JobStatus;
  criteria: JobCriterion[];
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: string;
  job_id: string;
  candidate_id: string;
  primary_document_id: string;
  status: ApplicationStatus;
  submitted_at: string;
  created_at: string;
}

export interface CriterionEvaluationItem {
  criterion_id: string;
  criterion_name: string;
  category: string;
  status: EvidenceStatus;
  confidence: number;
  plain_language_explanation: string;
  source_excerpt: string | null;
  source_page: number | null;
  evidence_item_id: string | null;
}

export interface EvidenceCoverageSummary {
  total_criteria: number;
  supported_count: number;
  not_found_count: number;
  ambiguous_count: number;
  required_total: number;
  required_supported_count: number;
  preferred_total: number;
  preferred_supported_count: number;
}

export interface Evaluation {
  id: string;
  application_id: string;
  version: number;
  job_criteria_version: number;
  extraction_run_id: string;
  overall_status: EvidenceStatus;
  coverage: EvidenceCoverageSummary;
  criteria_evaluations: CriterionEvaluationItem[];
  summary_notes: string | null;
  created_at: string;
}

export interface ReviewFlagSummary {
  id: string;
  application_id: string;
  criterion_name: string | null;
  criterion_category: string | null;
  candidate_id: string;
  candidate_name: string | null;
  job_title: string | null;
  ai_status: EvidenceStatus | null;
  verification_state: VerificationState | null;
  flag_type: string;
  status: ReviewFlagStatus;
  priority: string;
  reason: string;
  created_at: string;
}

export interface ReviewCaseDetail {
  flag_id: string;
  flag_status: ReviewFlagStatus;
  priority: string;
  reason: string;
  assigned_to_user_id: string | null;
  application_id: string;
  application_status: ApplicationStatus;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  job_id: string;
  job_title: string;
  criterion_id: string;
  criterion_name: string;
  criterion_category: string;
  criterion_description: string | null;
  criterion_version: number;
  criterion_weight: number;
  criterion_evidence_id: string;
  ai_status: EvidenceStatus;
  ai_confidence: number;
  ai_reasoning: string | null;
  verification_state: VerificationState;
  source_excerpt: string | null;
  source_page: number | null;
  evidence_item_id: string | null;
  claim_text: string | null;
  clarifications: CandidateClarificationItem[];
  decisions: ReviewDecisionItem[];
  created_at: string;
  resolved_at: string | null;
}

export interface CandidateClarificationItem {
  id: string;
  candidate_statement: string;
  additional_document_id: string | null;
  status: CorrectionRequestStatus;
  created_at: string;
}

export interface ReviewDecisionItem {
  id: string;
  reviewer_id: string;
  decision: ReviewDecisionType;
  mandatory_rationale: string;
  previous_verification_state: string;
  new_verification_state: string;
  created_at: string;
}

export interface AuditVerificationReport {
  is_valid: boolean;
  total_events: number;
  verified_events: number;
  chain_head_hash: string | null;
  discrepancy_type: string | null;
  error: string | null;
  broken_event_id: string | null;
  broken_sequence_number: number | null;
  tamper_evidence_disclaimer: string;
}
```

---

## 6. Frontend-First Development Strategy

To allow rapid visual development without depending on live backend instances, ClearHire implements a decoupled two-layer strategy:

### Layer 1: UI & Contract Implementation
- Pages, layouts, and components are constructed against the pure TypeScript contracts defined above.
- Data fetching hooks (`useQuery`, `useMutation`) consume a centralized API service interface (`IJobService`, `IReviewService`).
- In development mode (`VITE_USE_MOCK=true`), the service interfaces point to **Mock Service Adapters** that return deterministic synthetic datasets with simulated network delays (250–500ms).
- Mock data includes realistic edge cases:
  - Candidates with 100% supported criteria.
  - Candidates with ambiguous claims (e.g. "Python listed in skills section without chronological role context").
  - Candidates contesting decisions with candidate clarification threads.
  - Broken audit hash-chain scenarios for compliance UI testing.
- Loading skeletons, empty states, and validation errors are fully built and verified in this layer.

### Layer 2: API Integration & Live Wiring
- Once the UI is finalized, switching `VITE_USE_MOCK=false` replaces the mock adapter with the live Axios HTTP client.
- Because both adapters implement identical TypeScript contracts, **zero component rewriting or markup refactoring is required**.
- Real authentication, JWT storage, multipart file streaming, and background polling hooks connect directly to `http://localhost:8000/api/v1`.

### Strict Mock Isolation Rules
1. Mock data is quarantined strictly in `src/services/mock/fixtures/`.
2. Hardcoding mock objects or test candidate names directly inside UI component files is strictly prohibited.
3. No silent fallback in production: If an API request fails in production, the application must throw a structured error and display `AlertBanner` or an error boundary. It must **NEVER** silently load mock data.
