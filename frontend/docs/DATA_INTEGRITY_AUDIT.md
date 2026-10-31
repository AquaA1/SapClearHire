# ClearHire — Global Mock Data Elimination & Data Integrity Audit Report

**Audit Date**: November 1, 2026  
**Scope**: Full Authenticated ClearHire Frontend (`frontend/src`)  
**Backend Reference**: FastAPI Backend (Read-Only, `/home/vanilla/Desktop/hackathon/sap/backend`)

---

## 1. Executive Summary

This audit and remediation initiative eliminated all fabricated mock data (`mockService`, hardcoded names such as "Elena Rostova", fake PDF filenames, artificial application IDs like `app-001`, and synthetic reviewer cases) across the entire authenticated ClearHire application. 

All authenticated dashboards, application dossiers, and review triage pages are now directly connected to real backend FastAPI endpoints via dedicated API client services (`applicationService`, `jobService`, `reviewService`, `evaluationService`, `auditService`). Where no backend database records exist for a user or tenant, the interface renders honest, branded empty and in-progress states rather than inventing demonstration data.

---

## 2. Audited Pages & Remediations Register

| # | Page Component | File Path | Removed Mock Elements | Real Backend API Integration | Honest Empty State Behavior |
|---|----------------|-----------|------------------------|------------------------------|-----------------------------|
| 1 | **Top Navigation** | `src/components/shell/TopNavbar.tsx` | Hardcoded static date `"Friday, 31 Oct"` | Dynamic Intl date formatter; current user auth store session | Uniform single-row `h-16` flex layout; consistent vertical alignment across all viewports |
| 2 | **Candidate Dashboard** | `src/pages/candidate/CandidateDashboardPage.tsx` | `mockService` imports; fake resume `"Elena_Rostova_Resume_2026.pdf"`; fabricated review cases; fake audit events | `GET /api/v1/applications`<br>`GET /api/v1/jobs?status=active` | "No resume on file yet" card; "No submitted applications yet" table row; "No ledger events yet" timeline |
| 3 | **Candidate Applications** | `src/pages/candidate/CandidateApplicationsPage.tsx` | `mockService.listApplications()` | `GET /api/v1/applications`<br>`GET /api/v1/jobs` (for job metadata enrichment) | "No submitted applications yet" with direct CTA to browse open requisitions |
| 4 | **Candidate Application Detail** | `src/pages/candidate/CandidateApplicationDetailPage.tsx` | Fallback to fake `'app-001'`; `mockService['applications'][0]` fallback; mock clarification submission | `GET /api/v1/applications/{id}`<br>`GET /api/v1/evaluations/{id}`<br>`POST /api/v1/applications/{id}/clarifications` | "Application Not Found" on invalid ID; "Screening Evaluation In Progress" if evaluation record is not yet generated |
| 5 | **Employer Dashboard** | `src/pages/employer/EmployerDashboardPage.tsx` | `mockService` calls; hardcoded `/employer/applications/app-001` links; fabricated applicant names | `GET /api/v1/jobs`<br>`GET /api/v1/applications`<br>`GET /api/v1/review-flags`<br>`GET /api/v1/audit` | "No candidate applications submitted yet" table row; "No requisitions created" roster card |
| 6 | **Employer Application Detail** | `src/pages/employer/EmployerApplicationDetailPage.tsx` | `mockService` calls; fake notes from "Sarah Jenkins" and "Marcus Vance" dated 31 Oct 2026 | `GET /api/v1/applications`<br>`GET /api/v1/evaluations/{id}`<br>`POST /api/v1/evaluations`<br>`POST /api/v1/review-flags` | "No Candidate Applications Submitted" empty state with return to requisitions CTA; interactive notes session |
| 7 | **Reviewer Queue** | `src/pages/reviewer/ReviewerQueuePage.tsx` | `mockService.listReviewCases()` | `GET /api/v1/review-flags` | "Review Queue Empty: No candidate criteria flags currently require adjudication" empty table row |
| 8 | **Review Decision Studio** | `src/pages/reviewer/ReviewCaseDetailPage.tsx` | `mockService.getReviewCase()` with fallback to `'flag-001'`; mock decision recording | `GET /api/v1/reviews/{id}`<br>`POST /api/v1/reviews/{id}/decision` | "Review Case Not Located" error card with return to queue CTA; real decision submission requiring ≥25 chars rationale |
| 9 | **Employer Requisitions** | `src/pages/employer/EmployerJobsPage.tsx` | Hardcoded links navigating to `/employer/applications/app-001` | `GET /api/v1/jobs`<br>`POST /api/v1/jobs` | Dynamic navigation to `/employer/applications` |
| 10 | **Sidebar Navigation** | `src/components/shell/Sidebar.tsx` | Hardcoded links to `/reviewer/case/flag-001` and `/employer/applications/app-001` | Role-based navigation routes | Clean links to `/reviewer/queue` and `/employer/applications` |
| 11 | **Registration Page** | `src/pages/public/RegisterPage.tsx` | Placeholder `"e.g. Elena Rostova"` | `POST /api/v1/auth/register/candidate` | Neutral placeholder `"e.g. Alex Morgan"` |

---

## 3. Backend Endpoint Mapping & Tenant Boundaries

The backend API contracts and authorization boundaries discovered and enforced:

| Endpoint | HTTP Method | Authorized Roles | Tenant Isolation Enforcement |
|----------|-------------|------------------|------------------------------|
| `/api/v1/applications` | GET | `CANDIDATE`, `EMPLOYER_ADMIN`, `REVIEWER`, `SYSTEM_AUDITOR` | Candidates see only their own applications; employers and reviewers see only applications linked to their organization's job requisitions. |
| `/api/v1/applications/{id}` | GET | `CANDIDATE`, `EMPLOYER_ADMIN`, `REVIEWER`, `SYSTEM_AUDITOR` | Explicit ownership check. Throws 403 if unauthorized. |
| `/api/v1/evaluations/{id}` | GET | `CANDIDATE`, `EMPLOYER_ADMIN`, `REVIEWER`, `SYSTEM_AUDITOR` | Candidates can only inspect evaluations of their own applications. |
| `/api/v1/evaluations` | POST | `EMPLOYER_ADMIN`, `REVIEWER`, `SYSTEM_AUDITOR` | Triggers deterministic evaluation for an application. Candidates forbidden (403). |
| `/api/v1/review-flags` | GET | `EMPLOYER_ADMIN`, `REVIEWER`, `SYSTEM_AUDITOR` | Reviewers see assigned flags; employers see org flags. **Candidates are strictly forbidden (403)**. Candidate Dashboard derives pending review actions from `application.status === 'needs_review'`. |
| `/api/v1/reviews/{id}` | GET | `EMPLOYER_ADMIN`, `REVIEWER`, `SYSTEM_AUDITOR` | Returns full review case detail package (criterion, verbatim quotes, candidate clarifications, decisions). |
| `/api/v1/reviews/{id}/decision` | POST | `EMPLOYER_ADMIN`, `REVIEWER` | Records authorized human verdict with mandatory non-empty rationale (minimum 25 characters). |
| `/api/v1/applications/{id}/clarifications` | POST | `CANDIDATE` | Allows candidates to submit contest explanations for an ungrounded or ambiguous criterion. |
| `/api/v1/audit` | GET | `EMPLOYER_ADMIN`, `SYSTEM_AUDITOR` | Query cryptographic audit trail. **Candidates are strictly forbidden (403)**. |
| `/api/v1/audit/verify` | GET | `EMPLOYER_ADMIN`, `SYSTEM_AUDITOR` | Verifies SHA-256 hash continuity across the entire event chain. |

---

## 4. Dashboard Metric Derivations (100% Real Database Queries)

No dashboard statistics are fabricated. All metrics are calculated deterministically from active backend responses:

### Candidate Dashboard
- **Total Submitted Applications**: `applications.length`
- **Applications in Screening**: `applications.filter(a => a.status === 'submitted' || a.status === 'screening' || a.status === 'needs_review').length`
- **Actions Required**: `applications.filter(a => a.status === 'needs_review').length`
- **Primary Resume**: Derived from `applications[0].primary_document_id` if present; otherwise honest empty state.
- **Evidence Ledger**: Derived from candidate's real application lifecycle timestamps (`submitted_at`, `created_at`).

### Employer Dashboard
- **Total Applicants**: `applications.length`
- **Active Jobs**: `jobs.filter(j => j.status === 'active' || !j.status).length`
- **Resolved Human Determinations**: `flags.filter(f => f.status === 'resolved').length`
- **Pending Review Triage**: `flags.filter(f => f.status === 'pending' || f.status === 'under_review').length`
- **Recent Screenings Table**: Rendered directly from `applications.slice(0, 5)`.

### Reviewer Queue
- **Pending Cases**: `flags.filter(f => f.status === ReviewFlagStatus.PENDING).length`
- **Under Review**: `flags.filter(f => f.status === ReviewFlagStatus.UNDER_REVIEW).length`
- **Signed Off / Resolved**: `flags.filter(f => f.status === ReviewFlagStatus.RESOLVED).length`

---

## 5. Verification Results

- **TypeScript Compilation**: `npx tsc --noEmit` passed with 0 errors.
- **Vite Production Build**: `npm run build` succeeded cleanly in 2.11s with 0 warnings.
- **Zero Mock Imports**: Verified across all files in `frontend/src/pages/` and `frontend/src/components/`.

---

## 6. Multi-Tenant Review Queue Isolation Audit & Vulnerability Report

### 6.1 Vulnerability Discovery & Root Cause Analysis

A security audit of the backend review flag query endpoints revealed a severe multi-tenant data leakage vulnerability in `GET /api/v1/review-flags`:

- **Location**: `backend/app/services/review.py:239-263` and `backend/app/repositories/domain.py:394-420`
- **Root Cause**:
  In `ReviewWorkflowService.get_assigned_review_cases()`, when `current_user.role == UserRole.REVIEWER`, `filter_user_id` is set to `current_user.id`. However, when `current_user.role == UserRole.EMPLOYER_ADMIN`, `filter_user_id` is set to `None`.
  The repository method `ReviewFlagRepository.get_assigned_flags(user_id=None, status=status, application_id=application_id)` executes:
  ```python
  query = select(ReviewFlag).options(...)
  if user_id is not None:
      query = query.where(ReviewFlag.assigned_to_user_id == user_id)
  if status is not None:
      query = query.where(ReviewFlag.status == status)
  if application_id is not None:
      query = query.where(ReviewFlag.application_id == application_id)
  ```
  When an `EMPLOYER_ADMIN` requests `GET /api/v1/review-flags` without passing `application_id`, the query executes **without any tenant or organization filter** (no join or check on `Application.job.employer_id` or `Job.creator.employer_id`).
  Consequently, **all review flags across every employer and organization in the entire database are serialized and returned in the HTTP response**.

---

### 6.2 Empirical Verification: The 6 Tenant-Isolation Questions

An automated multi-tenant test suite was executed against an isolated in-memory test database (`scratch/test_tenant_isolation_evidence.py`), creating two distinct competing organizations:
- **Tenant A**: Apex Corp (Employer: `employer@apexcorp.com`, Org: `tenant-apex`, Candidate: Alice Apex, Requisition: *Apex Senior Backend Engineer*)
- **Tenant B**: Beta LLC (Employer: `employer@betallc.com`, Org: `tenant-beta`, Candidate: Bob Beta, Requisition: *Beta Lead Data Scientist*)

The empirical findings for each of the 6 verification questions:

| # | Verification Question | Backend Status | Finding & Hard Evidence |
|---|-----------------------|----------------|--------------------------|
| **1** | **Does the employer API response contain review flags belonging to other organizations?** | **VULNERABLE (LEAK CONFIRMED)** | **YES.** When Employer A queried `GET /api/v1/review-flags` without `application_id`, the response returned all 4 flags in the database, including Tenant B's flag `07dda76d-d669-49aa-96a8-8eb6ee2c0441`.<br>```Returned flag IDs: ['c1e2a5ea...', '07dda76d...', '5b493538...', '8077329a...']```<br>Contains Tenant B flag? `True`. |
| **2** | **Does the frontend receive those records before filtering?** | **CONFIRMED** | **YES.** The raw HTTP response body delivered over the wire directly contains Tenant B's JSON object. The previous frontend relied solely on client-side filtering (`flags.filter(f => myAppIds.has(f.application_id))`), meaning competitor records were already transferred over the network before JavaScript filtered them from the DOM. |
| **3** | **Can an employer inspect another organization's candidate metadata through browser network responses?** | **CONFIRMED EXPOSURE** | **YES.** By opening the browser DevTools Network tab, an Employer Admin can inspect the HTTP response and read competitor candidate names, candidate IDs, job titles, and flagged reasons:<br>```json
{
  "flag_id": "07dda76d-d669-49aa-96a8-8eb6ee2c0441",
  "candidate_id": "9be91b03-79ae-496d-87c1-3e2f36d60ca3",
  "candidate_name": "candidate.bob",
  "job_title": "Beta Lead Data Scientist",
  "criterion_name": "PyTorch ML",
  "reason": "Beta ambiguous roadmap ownership",
  "priority": "urgent"
}
``` |
| **4** | **Does `GET /api/v1/reviews/{id}` correctly reject another organization's review case?** | **PROTECTED (SECURE)** | **YES.** `ReviewWorkflowService.get_review_case_detail()` strictly checks `is_creator` or `org_matches`. When Employer A attempts to access Tenant B's case detail (`GET /api/v1/reviews/{flag_b_id}`), the backend immediately rejects with **HTTP 403 Forbidden** (`"You are not authorized to view review cases for this job requisition."`). |
| **5** | **Are review decisions restricted to organization-owned cases?** | **PROTECTED (SECURE)** | **YES.** `ReviewWorkflowService.record_reviewer_decision()` strictly enforces `is_creator` or `org_matches`. When Employer A attempts `POST /api/v1/reviews/{flag_b_id}/decision`, the backend rejects with **HTTP 403 Forbidden** (`"You are not authorized to record decisions for this job requisition."`). When Employer A acts on its own case, the request succeeds with **HTTP 201 Created**. |
| **6** | **Are employer review queue counts derived only from authorized records?** | **REMEDIATED** | **YES (Post-Remediation).** Unscoped queries were eliminated. The frontend now queries review flags strictly scoped per authorized organization application (`GET /api/v1/review-flags?application_id={app.id}`). In scoped queries, Tenant B records leaked = `False`. Review queue counts are derived exclusively from authorized records. |

---

### 6.3 Frontend Remediations Implemented

Because the backend codebase is strictly READ-ONLY during this phase, comprehensive defense-in-depth protections were implemented directly at the frontend network and application layers:

1. **Network Guard in `reviewService.ts`**:
   `reviewService.listReviewFlags()` now inspects the caller's JWT token payload. If the active user has role `EMPLOYER_ADMIN` and `params?.application_id` is missing, the service immediately halts the unscoped query, logs a security alert, and returns `[]`. This eliminates any possibility of an unscoped HTTP request leaking competitor records across the wire.
2. **Application-Scoped Retrieval in `EmployerDashboardPage.tsx`**:
   Replaced the global `reviewService.listReviewFlags()` call. The dashboard now queries review flags strictly scoped to the employer's verified application IDs (`reviewService.listReviewFlags({ application_id: app.id })`). If the employer has no applications, 0 review flag requests are transmitted.
3. **Application-Scoped Retrieval & Security Banner in `EmployerReviewQueuePage.tsx`**:
   The Employer Review Queue now retrieves flags strictly per organization application ID. A prominent security status badge is displayed:
   `Tenant-Isolated Review Triage Active: Review cases are strictly scoped per authorized application ID (GET /api/v1/review-flags?application_id=...) to prevent cross-organization candidate data exposure.`
4. **Preserved Reviewer Role Isolation**:
   Reviewer routes (`/reviewer/queue`, `/reviewer/case/:caseId`) remain strictly guarded for `REVIEWER` and `SYSTEM_AUDITOR` roles. The backend already enforces `assigned_to_user_id` filtering for the Reviewer role.

---

### 6.4 Recommended Permanent Backend Fix

When backend modifications are permitted, `ReviewFlagRepository.get_assigned_flags` in `backend/app/repositories/domain.py` must be updated to join `Application` and `Job` and enforce organization filtering:
```python
if user_id is None and application_id is None and current_user.role == UserRole.EMPLOYER_ADMIN:
    query = (
        query.join(ReviewFlag.application)
        .join(Application.job)
        .join(Job.creator)
        .where(
            or_(
                Job.employer_id == uuid.UUID(current_user.id),
                User.employer_id == current_user.employer_id,
            )
        )
    )
```

