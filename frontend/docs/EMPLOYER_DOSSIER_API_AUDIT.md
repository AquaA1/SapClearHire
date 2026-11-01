# ClearHire — Employer Application Dossier API Audit
**Document Version:** 1.0.0  
**Audit Date:** 2026-11-01  
**Scope:** Investigation of backend FastAPI endpoints, database schemas, authorization barriers, and workflows for Employer Application Dossier (`/employer/applications`).  
**Backend Mode:** STRICTLY READ-ONLY (`/home/vanilla/Desktop/hackathon/sap/backend`).

---

## Executive Summary

This audit investigates the five core problems identified in the Employer Application Dossier:
1. **Resume Tab displays only primary document ID** — Missing real document metadata and page text.
2. **Employer cannot view or download original PDF** — Investigation into backend PDF file serving capabilities.
3. **Employer cannot see meaningful extracted candidate information** — Investigation into candidate profiles, skills, and evidence extraction endpoints.
4. **"Screen Evidence" button does not work** — Investigation into prerequisite pipeline dependencies (`ExtractionRun` vs `Document`), synchronous evaluation execution, and error handling.
5. **Incomplete employer review workflow** — Investigation into human review flagging (`/api/v1/review-flags`) and tenant isolation.

---

## 1. Document Storage & Retrieval Audit

### Endpoints Audited:
- `POST /api/v1/documents`
- `GET /api/v1/documents/{document_id}/status`
- `POST /api/v1/documents/{document_id}/retry`
- `POST /api/v1/documents/{document_id}/extract`
- `GET /api/v1/documents/{document_id}/extraction-results`

### Key Findings:

#### 1.1 What endpoints exist for fetching documents?
- `GET /api/v1/documents/{document_id}/status`: Retrieves processing status, page count, and page-by-page extracted text (`dict[str, str]`).
- `GET /api/v1/documents/{document_id}/extraction-results`: Retrieves the latest structured AI evidence extraction run, including candidate skills and structured evidence items.
- **Does `GET /api/v1/documents/{id}` exist?** **NO.** The FastAPI backend does not define a general document entity endpoint `GET /documents/{id}`. Only `/status` and `/extraction-results` subpaths exist.

#### 1.2 Does an endpoint return raw binary PDF bytes or a download URL?
> [!IMPORTANT]
> **CRITICAL ARCHITECTURAL FINDING: NO RAW PDF DOWNLOAD ENDPOINT EXISTS.**
> 
> The backend file storage service (`app.services.storage.LocalStorageService`) stores uploaded resume files on local disk at `storage/documents/{document_id}.pdf`. The database model `Document` records `file_path`, `file_name`, `file_hash`, and `file_size_bytes`.
> 
> However, **FastAPI router exposes NO route to stream, download, or statically serve these PDF files** (e.g., no `GET /api/v1/documents/{id}/file`, no `GET /api/v1/documents/{id}/download`, and no mounted static directory).
> 
> **Strict Compliance Action:**
> In accordance with the system constraints (*"If the backend does not support employer-authorized access to original documents, STOP and report the exact missing capability in your audit rather than creating fake endpoints or bypassing authorization"*):
> - We **do not invent** mock download routes.
> - We document that backend support for `GET /api/v1/documents/{id}/file` returning `application/pdf` with `verify_document_access` authorization is required for binary file downloads.
> - On the frontend, we provide an honest, professional UI:
>   - Display a clear informative badge/modal explaining that binary PDF file streaming is pending backend API exposure.
>   - Render the complete, verbatim extracted text page-by-page from `GET /api/v1/documents/{id}/status` so employers can inspect the entire resume content with page anchors.

#### 1.3 What document metadata is exposed by existing endpoints?
`GET /api/v1/documents/{document_id}/status` returns `DocumentStatusResponse`:
- `id`: UUID (document ID)
- `file_name`: String (original uploaded filename, e.g., `resume.pdf`)
- `processing_status`: Enum (`queued`, `processing`, `completed`, `failed`)
- `page_count`: Integer | null (number of pages in the PDF)
- `extracted_text_by_page`: Dictionary mapping page number string (e.g., `"1"`, `"2"`) to page text
- `processing_error`: Dictionary | null (error code and message if extraction failed)
- `created_at`: ISO datetime string (upload timestamp)
- `updated_at`: ISO datetime string

#### 1.4 How can an employer view candidate resume content with available endpoints?
Employers authorized under `verify_document_access` can call `GET /api/v1/documents/{document_id}/status`. The frontend can render a rich, paginated, searchable viewer displaying the exact text extracted per page.

---

## 2. Extracted Candidate Information Audit

### Endpoints Audited:
- `GET /api/v1/documents/{document_id}/extraction-results`
- `GET /api/v1/profiles/{id}/skills`

### Key Findings:

#### 2.1 What candidate information does the backend store from resume extraction?
When AI extraction runs via `AIExtractionService`:
1. **Candidate Skills** (`CandidateSkill`):
   - `id`: UUID
   - `skill_name`: String (e.g., `"Python"`, `"PostgreSQL"`)
   - `category`: String | null (e.g., `"Languages"`, `"Frameworks"`, `"Databases"`)
   - `confidence`: Float (`0.0` to `1.0`, strictly 0.0 if source grounding fails)
   - `source_page`: Integer (original PDF page number)
   - `source_excerpt`: String (verbatim source quote from resume text)
2. **Evidence Items** (`EvidenceItem`):
   - `id`: UUID
   - `claim_text`: String (e.g., `"Role: Senior Backend Engineer at Acme Corp"`)
   - `source_page`: Integer
   - `source_excerpt`: String (grounded quote)
   - `confidence`: Float
   - `grounding_verified`: Boolean
   - `raw_metadata`: JSON dictionary containing typed candidate claims:
     - `item_type: "experience"`: `job_title`, `company`, `start_date`, `end_date`, `is_current`, `responsibilities`, `date_conflict`
     - `item_type: "education"`: `degree`, `institution`, `field_of_study`, `graduation_year`
     - `item_type: "project"`: `project_name`, `technologies`, `description`
     - `item_type: "certification"`: `certification_name`, `issuing_organization`, `issue_date`
     - `item_type: "skill"`: `skill_name`, `category`, `years_of_experience`
3. **Candidate Skill Inventory** (`GET /api/v1/profiles/{id}/skills`):
   - Deduplicated skills for the candidate across resumes, keeping the highest confidence version with source quotes and pages.

#### 2.2 What authorization is required for employers to access this extracted data?
- In `verify_document_access` (`backend/app/api/v1/endpoints/documents.py`):
  `EMPLOYER_ADMIN` and `REVIEWER` have read access if and only if the document is the `primary_document_id` of an `Application` linked to a `Job` created by the employer (`job.employer_id == current_user.id`) or within the same organization (`job.creator.employer_id == current_user.employer_id`).
- In `get_candidate_skills` (`backend/app/api/v1/endpoints/profiles.py`):
  Employers and reviewers have access if the candidate has applied to any job requisition owned by the employer or organization.

---

## 3. Evidence Screening Audit ("Screen Evidence" Button)

### Endpoints Audited:
- `POST /api/v1/evaluations`
- `GET /api/v1/evaluations/{id}`
- `POST /api/v1/documents/{document_id}/extract`

### Key Findings:

#### 3.1 Why did "Screen Evidence" appear not to work previously?
Two critical bugs in the previous frontend implementation caused the failure:
1. **Missing Prerequisite Extraction**:
   `POST /api/v1/evaluations` requires an `ExtractionRun` in `COMPLETED` status on `application.primary_document_id`. If `POST /documents/{id}/extract` was never triggered, the backend rejects the request with HTTP 422:
   ```json
   {"error": {"code": "VALIDATION_ERROR", "message": "Application document ... has not completed evidence extraction."}}
   ```
   The previous frontend code called `evaluationService.evaluateApplication(activeApp.id)` directly without checking or initiating document extraction first.
2. **Incorrect Evaluation Retrieval by ID**:
   On page load and application selection, the previous frontend called:
   `await evaluationService.getEvaluation(current.id);`
   `current.id` is the **Application ID**, but `GET /api/v1/evaluations/{id}` strictly expects an **Evaluation ID**. This always failed with HTTP 404, which silently set `evaluation` to `null`.
3. **Silent Error Swallowing**:
   The previous `handleTriggerEvaluation` caught errors with `console.error` and displayed no UI feedback, progress indicators, or error alerts.

#### 3.2 Evaluation Execution Properties:
- **Endpoint**: `POST /api/v1/evaluations`
- **Request Body**: `{ "application_id": "<uuid>" }`
- **Roles Authorized**: `EMPLOYER_ADMIN`, `REVIEWER`, `SYSTEM_AUDITOR`.
- **Execution Mode**: **Synchronous**. It evaluates all active job criteria deterministically, records versioned `Evaluation` and `CriterionEvidence` records, logs append-only audit events, updates `application.status = "screening"`, and returns HTTP 201 `EvaluationResponse`.
- **Response Format**:
  - `id`: UUID (Evaluation ID)
  - `application_id`: UUID
  - `version`: Integer
  - `overall_status`: Enum (`supported`, `ambiguous`, `not_found`)
  - `coverage`: `EvidenceCoverageSummary` (`total_criteria`, `supported_count`, `not_found_count`, `ambiguous_count`, `required_total`, `required_supported_count`, `preferred_total`, `preferred_supported_count`)
  - `criteria_evaluations`: List of `CriterionEvaluationItem` (`criterion_id`, `criterion_name`, `category`, `status`, `confidence`, `plain_language_explanation`, `source_excerpt`, `source_page`, `evidence_item_id`, `verification_state`)

#### 3.3 The Required Screening Pipeline:
To execute screening reliably:
1. Check if extraction results already exist via `GET /documents/{doc_id}/extraction-results`.
2. If 404 or incomplete, trigger `POST /documents/{doc_id}/extract`.
3. Poll `GET /documents/{doc_id}/extraction-results` with progress updates ("Extracting document text and claims...") until `status === 'completed'`.
4. Call `POST /api/v1/evaluations` with `{ application_id }`.
5. Update application status to `screening` and render coverage summary and per-criterion cards.

---

## 4. Human Review Triage Audit ("Triage to Reviewer" Button)

### Endpoints Audited:
- `POST /api/v1/review-flags`
- `GET /api/v1/review-flags`

### Key Findings:

#### 4.1 Triage Endpoint & Parameters:
- **Endpoint**: `POST /api/v1/review-flags`
- **Request Body**: `ReviewFlagCreateRequest`:
  - `application_id`: UUID (required)
  - `criterion_evidence_id`: UUID | null (optional: specific criterion evidence to flag; if omitted, backend auto-flags ambiguous and missing required criteria)
  - `flag_preferred`: Boolean (default `false`; if `true`, also flags preferred criteria)
  - `reason`: String | null (optional explanatory reason)
  - `priority`: String (`"normal"`, `"high"`, `"urgent"`, default `"normal"`)
  - `assigned_to_user_id`: UUID | null (optional assignee)
- **Roles Authorized**: `EMPLOYER_ADMIN`, `REVIEWER`.
- **Preconditions**: Application must have at least one `Evaluation`. If no evaluation exists, raises HTTP 422: `"Application {application_id} has no evaluations to flag. Run evaluation first."`
- **Behavior & Status Transition**:
  - Sets `application.status = "needs_review"`.
  - Creates `ReviewFlag` records for identified criteria.
  - Logs `REVIEW_FLAG_RAISED` audit events.
  - Returns `ReviewFlagBatchResponse` with `total_flagged` and `flags` array.

---

## 5. Summary Matrix of Backend Endpoints & Access

| Operational Goal | Backend Endpoint | HTTP Method | Authorized Roles | Notes / Preconditions |
|---|---|---|---|---|
| Document Status & Page Text | `/api/v1/documents/{id}/status` | GET | Candidate, Employer, Reviewer | Authorized if applicant to employer job |
| Raw PDF Binary Download | **NONE** | - | - | **Missing backend endpoint** |
| Trigger AI Extraction | `/api/v1/documents/{id}/extract` | POST | Candidate, Employer, Reviewer | Prerequisite for evaluation |
| Extraction Results & Claims | `/api/v1/documents/{id}/extraction-results` | GET | Candidate, Employer, Reviewer | Returns skills & evidence_items with quotes |
| Candidate Profile Skills | `/api/v1/profiles/{id}/skills` | GET | Candidate, Employer, Reviewer | Deduplicated candidate skill inventory |
| Evaluate Application | `/api/v1/evaluations` | POST | Employer, Reviewer, Auditor | Requires completed ExtractionRun |
| Get Evaluation Report | `/api/v1/evaluations/{id}` | GET | Candidate, Employer, Reviewer | Requires Evaluation ID |
| Create Review Flags (Triage) | `/api/v1/review-flags` | POST | Employer, Reviewer | Requires existing Evaluation |
| List Review Flags | `/api/v1/review-flags` | GET | Reviewer, Employer, Auditor | Use `?application_id=` for tenant safety |

---

## Conclusion & Architecture Roadmap

1. **Phase 2 (Resume Tab)**: Build a rich `ResumeDocumentViewer` with full metadata, page-by-page text tabs, search/filter, and honest modal explaining the missing binary PDF endpoint (`GET /api/v1/documents/{id}/file`).
2. **Phase 3 (Details Tab)**: Build a structured `CandidateExtractedProfile` rendering work experience, education, skills, projects, and certifications with exact page numbers and excerpts from `extraction-results` and `profiles/{id}/skills`.
3. **Phase 4 (Screen Evidence)**: Wire a multi-stage deterministic screening pipeline (`extract` -> poll -> `evaluations`) with live progress indicators and error feedback.
4. **Phase 5 (Triage Modal)**: Build `TriageReviewModal` allowing priority selection, reason text, flag preferred toggle, submitting to `POST /api/v1/review-flags`, and updating application status to `needs_review`.
