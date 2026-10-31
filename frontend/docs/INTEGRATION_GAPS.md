# ClearHire Backend Gaps, Integration Risks & Mitigation Plan

> **Document Status:** Complete & Verified  
> **Source Code Audited:** `backend/app/`  
> **Date of Audit:** October 2026  

---

## 1. Executive Gap Analysis

The ClearHire backend provides robust implementations for core deterministic evidence matching, cryptographic audit chains, and human review decisions. However, because the backend was originally architected from an API-first perspective, several critical user-facing interaction flows lack corresponding endpoints or require complex sequential client-side orchestration.

This document classifies every discovered integration gap, assigns an industry-standard severity rating, and details both the **recommended backend resolution** and the **frontend mitigation workaround**.

---

## 2. Gaps & Integration Risks Catalog

### GAP-01: No Document Download or In-Browser PDF Preview Endpoint
- **Severity:** `CRITICAL`
- **Functional Impact:** The core value proposition of ClearHire is source evidence grounding. In the Reviewer Studio (`/reviewer/cases/:id`) and Candidate Evidence Dossier (`/employer/applications/:id`), users need to see the original PDF resume alongside the highlighted excerpt. Currently, `POST /api/v1/documents` accepts a PDF upload and stores it on disk, but there is **no endpoint to download or stream the PDF bytes** (`GET /api/v1/documents/{id}/file` or `/download`).
- **Missing API Operation:** `GET /api/v1/documents/{document_id}/download` (or `GET /api/v1/documents/{document_id}/view`) returning `application/pdf`.
- **Recommended Backend Resolution:** Add a streaming endpoint in `app.api.v1.endpoints.documents` that verifies user access using `verify_document_access` and streams the stored PDF file using FastAPI's `FileResponse`.
- **Frontend Mitigation Workaround:** The frontend can render the extracted text per page using the dictionary from `GET /api/v1/documents/{document_id}/status` (`extracted_text_by_page: dict[str, str]`). While not rendering original PDF typography, it provides full textual source grounding until the file stream endpoint is added.

---

### GAP-02: Missing Candidate Document Library Endpoint
- **Severity:** `CRITICAL`
- **Functional Impact:** When a candidate returns to apply for a second job, they have no way to view their previously uploaded resumes or select an existing resume. `POST /api/v1/documents` returns `DocumentUploadResponse`, but there is **no `GET /api/v1/documents`** endpoint to list uploaded documents for the active candidate.
- **Missing API Operation:** `GET /api/v1/documents` returning `list[DocumentUploadResponse]`.
- **Recommended Backend Resolution:** Add `GET /api/v1/documents` filtered by `candidate_id == current_user.id`.
- **Frontend Mitigation Workaround:**
  1. Frontend can query `GET /api/v1/applications` and extract `primary_document_id` values from existing applications.
  2. Cache previously uploaded document metadata in client storage (`localStorage` / Zustand) during active sessions.
  3. Require candidate to re-upload their resume when applying for a new job if not cached.

---

### GAP-03: No Job Requisition Editing or Status Lifecycle Transitions
- **Severity:** `HIGH`
- **Functional Impact:** Employers can create job requisitions (`POST /api/v1/jobs`), but there is no mechanism to edit the job description, update criteria weights, or change the status from `ACTIVE` to `DRAFT` or `ARCHIVED`. Once created, a requisition is permanent and immutable.
- **Missing API Operations:**
  - `PATCH /api/v1/jobs/{id}` (Update title, description, status)
  - `POST /api/v1/jobs/{id}/criteria` (Add new criterion version)
  - `DELETE /api/v1/jobs/{id}` (Soft delete or archive)
- **Recommended Backend Resolution:** Implement `PATCH /api/v1/jobs/{id}` accepting partial updates and updating the `status` enum (`draft`, `active`, `archived`).
- **Frontend Mitigation Workaround:** Display job requisitions in the Employer Portal with read-only badges. Disable "Edit Job" or "Archive Job" actions in the UI with a tooltip: *"Requisition updates disabled in Phase 1; all active requisitions are permanent."*

---

### GAP-04: Multi-Step Sequential Application & Evaluation Orchestration
- **Severity:** `HIGH`
- **Functional Impact:** Submitting an application and obtaining screening results requires the frontend to coordinate a complex chain of 5 sequential asynchronous calls across 4 different routers:
  1. `POST /api/v1/documents` (Upload PDF) -> returns `document_id`
  2. Poll `GET /api/v1/documents/{document_id}/status` until status is `completed`
  3. `POST /api/v1/documents/{document_id}/extract` -> trigger AI structured claims extraction
  4. Poll `GET /api/v1/documents/{document_id}/extraction-results`
  5. `POST /api/v1/applications` with `{job_id, primary_document_id}`
  6. *(Employer/Reviewer role)* `POST /api/v1/evaluations` with `{application_id}`
- **Risk:** Network drops or browser closure during this 5-step sequence leaves orphan documents without applications, or applications without evaluations.
- **Recommended Backend Resolution:** Create an orchestrated atomic endpoint: `POST /api/v1/applications/apply` that accepts multipart form data (`file` + `job_id`), stores the document, registers the application, and schedules background extraction & evaluation automatically.
- **Frontend Mitigation Workaround:** Construct a dedicated `useApplicationSubmission` state machine in the frontend that coordinates these steps with clear progress step indicators ("1/3 Uploading Resume", "2/3 Extracting Skills", "3/3 Registering Application") and persists intermediate IDs in session storage.

---

### GAP-05: No Final Application Decision or Hiring Status Updates
- **Severity:** `HIGH`
- **Functional Impact:** An employer can evaluate candidate evidence and reviewers can resolve flags, but there is no endpoint to mark an applicant as `HIRED`, `REJECTED`, or `INTERVIEW_SCHEDULED`. The `ApplicationStatus` enum only contains `SUBMITTED`, `SCREENING`, `NEEDS_REVIEW`, `REVIEWED`.
- **Missing API Operation:** `PATCH /api/v1/applications/{id}/status` or `POST /api/v1/applications/{id}/decision`.
- **Recommended Backend Resolution:** Add a status transition endpoint for employer admins to finalize applicant dispositions after review is complete.
- **Frontend Mitigation Workaround:** The frontend reflects `ApplicationStatus.REVIEWED` as the terminal state in Phase 1, indicating: *"Human Review Completed — Evidence Verified"*.

---

### GAP-06: Limited Review Flag Queue Filtering
- **Severity:** `MEDIUM`
- **Functional Impact:** `GET /api/v1/review-flags` only supports `status` and `application_id` query parameters. It does NOT support filtering by `priority` (e.g. `urgent` vs `normal`), `job_id`, `created_date`, or `assigned_to_user_id`. In a large organization, reviewers would be forced to page through cases for all jobs.
- **Recommended Backend Resolution:** Add `priority`, `job_id`, and `assigned_to` query parameters to `list_review_cases` in `app/api/v1/endpoints/reviews.py`.
- **Frontend Mitigation Workaround:** The frontend loads the reviewer's case batch and performs client-side filtering and sorting for `priority` and `job_title` using TanStack Table.

---

### GAP-07: Clarification Workflow Lacks Automated Re-Evaluation
- **Severity:** `MEDIUM`
- **Functional Impact:** When a candidate submits clarification statements or supplementary documents via `POST /applications/{id}/clarifications`, the backend updates `verification_state` to `CANDIDATE_CLARIFIED` and sets the review flag to `PENDING`. However, it does not re-trigger AI evaluation or parse the newly attached document. The human reviewer must read the raw candidate text and manually make a verdict.
- **Recommended Backend Resolution:** Feature enhancement in Phase 2 to allow AI re-evaluation of supplementary clarification claims.
- **Frontend Mitigation Workaround:** The Reviewer Studio (`/reviewer/cases/:caseId`) renders candidate clarification text directly in a dedicated `ClarificationHistoryThread` component, enabling the reviewer to read candidate arguments directly before submitting a verdict.

---

### GAP-08: Inconsistent Response Structure for Status Enums
- **Severity:** `LOW`
- **Functional Impact:** In `JobResponse`, the `status` field is typed as `JobStatus` (enum object returning `"active"`), whereas in `ApplicationResponse`, `status` is serialized as a raw `str` (`status=app.status.value`). Similarly, `ReviewCaseDetailResponse` mixes enum types and strings.
- **Frontend Mitigation Workaround:** Standardize all TypeScript contracts to accept string values matching the enum definitions (e.g. `status: ApplicationStatus | string`).

---

### GAP-09: Synthetic Feed & Benchmark Disclaimers
- **Severity:** `LOW`
- **Functional Impact:** `/integrations/successfactors/feed` and `/benchmark/run` return synthetic/simulated data. If displayed without clear visual cues, users or stakeholders might mistake them for live SAP SuccessFactors integrations.
- **Frontend Mitigation Workaround:** All benchmark and SuccessFactors views must prominently render an SAP Fiori-style `SimulationDisclaimerBanner` explicitly citing: *"SIMULATION MODE: Synthetic ground-truth data for benchmark demonstration only."*

---

## 3. Risk Summary Matrix

| Gap ID | Title | Severity | Impact Area | Frontend Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **GAP-01** | Missing Document Download Endpoint | `CRITICAL` | Reviewer & Employer portals | Render `extracted_text_by_page` text box |
| **GAP-02** | Missing Candidate Document Library | `CRITICAL` | Candidate application flow | Cache active document ID; re-upload fallback |
| **GAP-03** | No Job Edit / Archive Endpoints | `HIGH` | Employer job management | Display read-only status; disable edit buttons |
| **GAP-04** | Sequential 5-Step Application Flow | `HIGH` | Application submission | Client-side async state machine with progress steps |
| **GAP-05** | No Application Hiring Decision Endpoint | `HIGH` | Employer applicant pipeline | Treat `REVIEWED` as terminal status |
| **GAP-06** | Limited Review Flag Filtering | `MEDIUM` | Reviewer queue triage | Client-side table filtering & sorting |
| **GAP-07** | Clarification Lacks Auto Re-Eval | `MEDIUM` | Review decision studio | Render raw text in ClarificationThread |
| **GAP-08** | Inconsistent Enum Serialization | `LOW` | TypeScript contract typing | Relax TypeScript types to `Enum \| string` |
| **GAP-09** | Synthetic Integration Ambiguity | `LOW` | Benchmark & SF screens | Mandatory prominent simulation banners |
