# ClearHire — Critical Backend Integrity & AI Pipeline Repair Report

**Date**: 2026-11-01  
**Project**: ClearHire Hiring Evidence Transparency Platform  
**Status**: Resolved & Verified (All 190 Pytest Unit/Integration Tests Passed, Scenarios A-E Verified, Production Build Clean)  
**Database Audited**: `backend/clearhire_dev.db` (SQLite)  

---

## Executive Summary

During live application testing, three critical integrity issues were identified across backend, database queries, and frontend state flow:
1. **Issue 1**: The candidate application detail page was permanently stuck displaying *"Evidence Extraction In Progress"*, never transitioning to completed or failed states.
2. **Issue 2**: Duplicate job requisitions appeared automatically following job creation and page refresh.
3. **Issue 3**: Applications submitted by different candidate accounts exhibited cross-account visibility issues and missing profile metadata in employer dossiers.

A forensic database audit and end-to-end investigation revealed that the application data was intact in SQLite without data corruption or orphan records. The issues stemmed from:
- A frontend URL mismatch and missing reactive polling loop in `CandidateApplicationDetailPage.tsx`.
- Missing background orchestration between application submission, claim extraction, and evaluation.
- Unhandled background task exceptions causing Starlette response pipeline panics.
- Lack of submit-button debouncing and persistent in-memory client-side cache across user logout sessions.
- Incomplete ORM eager loading on `Application.candidate` and an ambiguous SQL join in employer application queries.

All root causes were resolved with zero loss of real data, zero database resets, and zero weakening of tenant security boundaries.

---

## 1. Actual Root Causes Identified

### Issue 1 — AI Pipeline Stuck in Progress

1. **Incorrect Frontend API Route & Application ID Lookup**:
   - `CandidateApplicationDetailPage.tsx` called `evaluationService.getEvaluation(appId)`, which hits `GET /api/v1/evaluations/{id}`. That backend endpoint expects an **Evaluation UUID**, not an **Application UUID**, resulting in an immediate HTTP 404 Not Found.
   - The correct endpoint for retrieving evaluations by application is `GET /api/v1/evaluations/application/{application_id}` (`evaluationService.getEvaluationByApplication(appId)`).
2. **Missing Reactive Polling & Error State Handling**:
   - The component executed an un-polled single-shot request on component mount. Upon receiving the 404 error, it silently set `evaluation = null` and rendered the static, unconditional placeholder: *"Evidence Extraction In Progress"*. It never polled or refreshed.
3. **Missing Automated Downstream Pipeline Execution**:
   - `submit_application` (`POST /api/v1/applications`) inserted an `Application` row with status `SUBMITTED`, but neither triggered structured AI claim extraction nor criteria evaluation in the background. As a result, candidate applications had no automated worker advancement.
4. **Unhandled Background Task Exception Bubbling**:
   - In `documents.py`, `background_tasks.add_task(extraction_service.extract_and_persist, ...)` executed directly. When upstream provider failures occurred, re-raising inside the background task after HTTP 202 was sent caused Starlette's ASGI handler to throw `RuntimeError: Caught handled exception, but response already started.`.
5. **Missing Dependency Import**:
   - `applications.py` and `workers/__init__.py` attempted to import `EvidenceEvaluationService`, which was named `EvaluationService` in `backend/app/services/evaluation.py`.

### Issue 2 — Jobs Created Automatically & Duplicate Postings

1. **Test Runner Artifact Pollution in Development Database**:
   - Forensic SQLite timestamps revealed 6 duplicate jobs named `"Senior Backend Engineer"` created in rapid succession by synthetic test employer accounts (`test_ai_pipeline_e2e.py`) executing directly against `clearhire_dev.db`.
2. **Frontend Double-Click & Rapid Re-Submission**:
   - In `EmployerJobsPage.tsx`, clicking "Create Job Requisition" did not lock the submission ref (`isSubmittingRef`), allowing rapid consecutive clicks to dispatch multiple identical `POST /api/v1/jobs` requests before network resolution.
3. **Client-Side Cache Bleed on Logout**:
   - `jobService.ts` cached the job list in memory. `authStore.logout()` previously cleared only authentication state (`token`, `user`), failing to invalidate the jobs cache (`jobService.invalidateCache()`). When logging in as another employer or refreshing, stale cached jobs persisted in UI state.

### Issue 3 — Candidate Application Visibility & Dossier Association

1. **Requisition Mismatch Across Different Employers**:
   - Because of the duplicate jobs created during automated runs, Candidate A applied to Requisition 1 (owned by Employer 1) and Candidate B applied to Requisition 2 (owned by Employer 2). When Employer 1 logged in, role-based isolation filtered out applications submitted to Employer 2's requisition.
2. **Ambiguous SQL Join on Requisition Creator**:
   - In `backend/app/api/v1/endpoints/applications.py`, `list_applications` joined `Application.job` and `Job.creator` with ambiguous table aliases, leading to filtering inconsistencies between `Job.employer_id` and `creator.employer_id`.
3. **Missing Candidate Eager Loading on Domain Models**:
   - In `ApplicationResponse`, `candidate_name` and `candidate_email` were not populated. In `ApplicationRepository.get_with_job`, `selectinload(Application.candidate)` was omitted, forcing frontend dossiers to fall back to generic identifiers (`App #021f56f3`).
4. **Missing Dependency in Candidate Applications List**:
   - `CandidateApplicationsPage.tsx` did not subscribe to `user?.id` in its `useEffect` dependency array, preventing clean re-fetching upon candidate logout/login.

---

## 2. Relevant Files & Functions Identified

| Component | File Path | Function / Method | Nature of Issue / Role |
| :--- | :--- | :--- | :--- |
| **Backend API** | `backend/app/api/v1/endpoints/applications.py` | `submit_application` | Missing background pipeline trigger; added `auto_evaluate` gating and pipeline dispatch |
| **Backend API** | `backend/app/api/v1/endpoints/applications.py` | `run_application_pipeline` | Background task orchestrating document readiness, claim extraction, and evaluation |
| **Backend API** | `backend/app/api/v1/endpoints/applications.py` | `list_applications`, `get_application` | Fixed ambiguous SQL alias on `Job.creator` and populated candidate metadata |
| **Backend API** | `backend/app/api/v1/endpoints/documents.py` | `trigger_ai_extraction` | Wrapped `extract_and_persist` in `_safe_extract` to prevent Starlette unhandled ASGI exceptions |
| **Backend API** | `backend/app/api/v1/endpoints/jobs.py` | `create_job` | Added duplicate window idempotency check (10-second deduplication) |
| **Backend Service**| `backend/app/services/evaluation.py` | `EvaluationService` | Exported `EvidenceEvaluationService = EvaluationService` alias |
| **Backend Repo** | `backend/app/repositories/domain.py` | `ApplicationRepository.get_with_job` | Added `selectinload(Application.candidate)` |
| **Backend Schema**| `backend/app/schemas/evaluation.py` | `ApplicationCreateRequest`, `ApplicationResponse` | Added `auto_evaluate: bool = False`, `candidate_name`, `candidate_email` |
| **Frontend Page** | `frontend/src/pages/candidate/CandidateApplicationDetailPage.tsx` | `loadApplicationData`, `checkEvaluationAndStatus` | Replaced `getEvaluation` with `getEvaluationByApplication`, added 2s polling loop, terminal error banner, and retry action |
| **Frontend Page** | `frontend/src/pages/candidate/CandidateApplicationsPage.tsx` | `useEffect` | Added `useAuthStore` and dependency on `user?.id` for clean re-fetching |
| **Frontend Page** | `frontend/src/pages/employer/EmployerJobsPage.tsx` | `handleCreateJob` | Added `isSubmittingRef` double-click lock and in-memory list deduplication by ID |
| **Frontend Store**| `frontend/src/stores/authStore.tsx` | `logout` | Added `jobService.invalidateCache()` upon logout |
| **Frontend Service**| `frontend/src/services/api/applicationService.ts` | `submitApplication` | Passed `auto_evaluate = true` by default for frontend candidate submissions |

---

## 3. Database Forensic Audit Findings

A complete audit of `clearhire_dev.db` was conducted via direct SQLite inspection (documented in `frontend/docs/DATA_INTEGRITY_AUDIT.md`):

| Entity | Count | Audit Finding |
| :--- | :--- | :--- |
| **Users** | 25 | 13 Candidates, 12 Employers. 0 orphan users; valid roles and password hashes. |
| **Jobs** | 11 | 6 duplicate titles ("Senior Backend Engineer") created by automated test employer accounts. 0 missing criteria. |
| **Applications**| 13 | 13 applications cleanly bound to existing jobs, candidates, and primary documents. 0 orphan records. |
| **Documents** | 19 | 19 documents stored in `/storage/documents`. Zero missing binary files or corrupt hashes. |
| **Extraction Runs**| 11 | 9 completed, 2 failed runs. Terminal status preserved. |
| **Evaluations**| 9 | Versioned evaluation records with verbatim quotes and factual coverage counts intact. |

**Integrity Audit Verdict**: No records were corrupted, deleted, or orphaned. The database schema, foreign keys, and existing test records remain completely intact.

---

## 4. Changes Made

### A. Backend Architecture & API Enhancements

1. **`backend/app/services/evaluation.py`**:
   - Added module-level alias `EvidenceEvaluationService = EvaluationService` to ensure compatibility across worker queues and endpoint modules.
2. **`backend/app/schemas/evaluation.py`**:
   - Added `auto_evaluate: bool = Field(default=False)` to `ApplicationCreateRequest`. This maintains backward compatibility with legacy tests while allowing automated pipeline triggering when requested.
   - Added `candidate_name: str | None = None` and `candidate_email: str | None = None` to `ApplicationResponse`.
3. **`backend/app/repositories/domain.py`**:
   - Updated `ApplicationRepository.get_with_job` to include `selectinload(Application.candidate)`.
4. **`backend/app/api/v1/endpoints/applications.py`**:
   - Implemented `run_application_pipeline`:
     - Checks document processing status, waiting for PDF text extraction if in progress.
     - Automatically verifies or executes structured AI claim extraction (`AIExtractionService.extract_and_persist`).
     - Executes deterministic evidence screening (`EvidenceEvaluationService.evaluate_application`).
     - Logs failures cleanly without leaving tasks hung in un-terminal states.
   - Updated `submit_application` to trigger `run_application_pipeline` in `BackgroundTasks` when `request.auto_evaluate` is `True`.
   - Updated `list_applications` and `get_application` to populate `candidate_name` and `candidate_email`, and resolved join ambiguity on `Job.creator` using `aliased(User)`.
5. **`backend/app/api/v1/endpoints/documents.py`**:
   - Wrapped `extract_and_persist` within `_safe_extract` in `trigger_ai_extraction` to prevent Starlette unhandled ASGI response runtime errors.
   - Enhanced user record resolution in `upload_document` and `submit_application` to look up by email if ID is not yet saved, preventing SQLite UNIQUE constraint errors.
6. **`backend/app/api/v1/endpoints/jobs.py`**:
   - Added a 10-second idempotency window in `create_job`. If the same employer submits a job with identical `title` and `department` within 10 seconds, the existing job is returned instead of creating a duplicate.

### B. Frontend Reactive Data Flow & Error Resilience

1. **`frontend/src/pages/candidate/CandidateApplicationDetailPage.tsx`**:
   - Replaced broken `evaluationService.getEvaluation(appId)` with `evaluationService.getEvaluationByApplication(appId)`.
   - Added a 2-second polling interval (up to 30 attempts / 60 seconds) that tracks pipeline completion.
   - Added an explicit failure banner that renders if document extraction or claim extraction fails, displaying the error message and an interactive *"Retry Extraction Pipeline"* button.
   - Replaced static placeholder with an active spinner indicator (`Loader2`) and step progression.
2. **`frontend/src/pages/candidate/CandidateApplicationsPage.tsx`**:
   - Imported `useAuthStore` and added `[user?.id]` to the `useEffect` dependencies, ensuring applications list is re-fetched cleanly when switching candidate accounts.
3. **`frontend/src/pages/employer/EmployerJobsPage.tsx`**:
   - Added `isSubmittingRef = useRef(false)` submit lock to prevent rapid double-click API calls.
   - Deduplicated jobs state by ID.
4. **`frontend/src/stores/authStore.tsx`**:
   - Added `jobService.invalidateCache()` to `logout()` to purge in-memory jobs cache across user sessions.
5. **`frontend/src/services/api/applicationService.ts`**:
   - Set `auto_evaluate = true` by default in `submitApplication` so candidates submitting via the UI receive automated downstream extraction and screening.

---

## 5. Verification & Test Execution Results

### A. End-to-End Integrity Verification (`scratch/test_backend_integrity_repair.py`)

All 5 core real-world application scenarios were executed end-to-end against the running application:

| Scenario | Scope | Expected Behavior | Actual Result |
| :--- | :--- | :--- | :--- |
| **Scenario A** | Candidate A Visibility | Candidate A logs in, uploads PDF, applies to Job 1, checks application list. | **PASSED**: Application submitted and immediately visible in Candidate A's application list. |
| **Scenario B** | Candidate B Isolation | Candidate B applies to Job 1; checks list; attempts GET on App A. | **PASSED**: Candidate B sees only their application. Candidate A's application is not visible in list. Direct GET `/applications/{app_a_id}` returned **403 Forbidden**. |
| **Scenario C** | Job Deduplication | Employer creates Job 1; sends rapid duplicate POST; refreshes job list. | **PASSED**: Duplicate POST returned existing job (idempotent). List contains exactly 1 instance of the job. |
| **Scenario D** | End-to-End AI Pipeline | Real PDF resume upload, application submitted with `auto_evaluate=True`, polling evaluation, page refresh. | **PASSED**: Background pipeline completed extraction and criteria evaluation. Refresh reloaded persisted evaluation without re-running or hanging. |
| **Scenario E** | Failure Resilience & Retry | Upstream LLM provider failure simulated (503 Service Unavailable). | **PASSED**: Extraction run transitioned to terminal `FAILED` status with error message (did not hang in processing). Retry successfully completed new extraction with skills and evidence items. |

### B. Backend Regression Suite (`pytest`)

```
============================= 190 passed in 51.73s =============================
```
- **Total Tests**: 190
- **Passed**: 190 (100%)
- **Failed**: 0
- **Regressions Detected**: 0

### C. Frontend Compilation & Type Verification

```bash
$ npm run build
> clearhire-frontend@1.0.0 build
> tsc && vite build

vite v5.4.21 building for production...
✓ 1975 modules transformed.
dist/index.html                          1.25 kB │ gzip:  0.65 kB
dist/assets/index-DDEXnz1M.css          36.06 kB │ gzip:  7.39 kB
dist/assets/vendor-icons-CXRB51f5.js    23.65 kB │ gzip:  4.67 kB
dist/assets/vendor-framer-C4xtxWwR.js  112.41 kB │ gzip: 37.12 kB
dist/assets/vendor-react-Cj2b8xJs.js   206.33 kB │ gzip: 67.31 kB
dist/assets/index-5fHyKuu2.js          216.91 kB │ gzip: 45.40 kB
✓ built in 5.41s
```
- **TypeScript Errors**: 0
- **Build Status**: Succeeded

---

## 6. Recommendations & Future Considerations

1. **Distributed Task Queue for High-Scale Deployments**:
   - The current setup uses FastAPI's `BackgroundTasks` and `LocalAsyncWorker` (in-memory async worker), which is optimal for development and single-instance deployments. For multi-worker Kubernetes production clusters, transitioning `BaseBackgroundWorker` to Redis/RQ or Celery with persistence will ensure task survivability across server pod terminations.
2. **WebSocket / Server-Sent Events (SSE) for Real-Time Dossier Updates**:
   - The frontend currently uses a 2-second polling loop with a 60-second cutoff. Adding SSE or WebSockets for document processing updates would eliminate polling overhead and provide instantaneous UI state transitions.
3. **Database Audit Archival**:
   - The forensic audit script and test scripts (`scratch/test_backend_integrity_repair.py`, `frontend/docs/DATA_INTEGRITY_AUDIT.md`) should be retained as regression fixtures for all future sprint milestones.
