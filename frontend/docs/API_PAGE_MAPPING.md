# ClearHire API-to-Page Detailed Mapping

> **Document Status:** Complete & Verified  
> **Backend Base URL:** `http://localhost:8000/api/v1`  
> **Source Endpoint Reference:** `frontend/docs/API_INVENTORY.md`  
> **Source Page Map Reference:** `frontend/docs/FRONTEND_PAGE_MAP.md`  
> **Date of Audit:** October 2026  

---

## 1. Page-to-API Interaction Specifications

This document defines the operational contract for each frontend page, detailing the exact API operations triggered, parameters sent, state expectations, and mock-readiness.

---

### P-02: Candidate & User Login (`/login`)
- **Role:** Public (Unauthenticated)
- **Purpose:** User authentication via email and password credentials, storing the returned JWT token, and querying user identity to direct them to their role-specific portal.
- **Required UI Components:** `LoginForm`, `AlertBanner`, `SubmitButton`, `ForgotPasswordLink`
- **Data Required:** None on entry.
- **API Endpoints & Methods:**
  1. `POST /api/v1/auth/login` (Method: `POST`, Payload: `{ "email": str, "password": str }`)
  2. `GET /api/v1/auth/me` (Method: `GET`, Header: `Authorization: Bearer <token>`)
- **User Actions:**
  - Enter credentials and submit.
  - On 200 response from login, store token in auth store (`localStorage` / in-memory).
  - Call `/api/v1/auth/me` to get role (`candidate`, `employer_admin`, `reviewer`, `system_auditor`).
  - Redirect to `/candidate/dashboard`, `/employer/dashboard`, `/reviewer/dashboard`, or `/auditor/verification`.
- **Expected Responses:**
  - Login: `TokenResponse` (`{ "access_token": "...", "token_type": "bearer", "expires_in": 3600 }`)
  - Profile: `UserResponse` (`{ "id": "...", "email": "...", "role": "candidate", "full_name": "..." }`)
- **Loading State:** Button spinner, disabled inputs.
- **Empty State:** Clean form with email & password inputs.
- **Error States:**
  - `401 Unauthorized`: "Invalid email or password" or "Account is inactive".
  - `422 Unprocessable Entity`: Validation failure on email format.
  - Network Error: "Unable to reach ClearHire authentication service".
- **Mockability:** High. Can be simulated with mock JWT and predefined user profiles.

---

### P-03: Candidate Registration (`/register`)
- **Role:** Public (Unauthenticated)
- **Purpose:** Public self-service candidate account creation.
- **Required UI Components:** `RegisterForm`, `PasswordStrengthMeter`, `SubmitButton`
- **Data Required:** None on entry.
- **API Endpoints & Methods:**
  1. `POST /api/v1/auth/register` (Method: `POST`, Payload: `{ "email": str, "password": str, "full_name": str }`)
  2. `POST /api/v1/auth/login` (Auto-login upon registration)
- **User Actions:** Fill in name, email, password; submit form; auto-authenticate and navigate to `/candidate/dashboard`.
- **Expected Response:** `UserResponse` (`{ "id": UUID, "email": str, "role": "candidate", ... }`).
- **Loading State:** Form inputs disabled with progress indicator.
- **Empty State:** Blank registration fields.
- **Error States:**
  - `409 Conflict`: "An account with this email already exists".
  - `422 Unprocessable`: Password shorter than 8 characters or invalid email.
- **Mockability:** High.

---

### C-01: Candidate Dashboard (`/candidate/dashboard`)
- **Role:** `candidate`
- **Purpose:** Welcome screen displaying active applications, screening statuses, and review feedback notifications.
- **Required UI Components:** `StatCards`, `RecentApplicationsList`, `StatusBadge`, `ActionRequiredCallout`, `UploadResumeCTA`
- **Data Required:** Authenticated user context, candidate's application list.
- **API Endpoints & Methods:**
  1. `GET /api/v1/auth/me`
  2. `GET /api/v1/applications` (Filtered automatically by backend to `candidate_id == current_user.id`)
- **User Actions:**
  - View application status (`submitted`, `screening`, `needs_review`, `reviewed`).
  - Click on an application to view evidence breakdown (`/candidate/applications/:id`).
  - Click "Browse Jobs" CTA (`/candidate/jobs`).
- **Expected Response:** `list[ApplicationResponse]`.
- **Loading State:** Skeleton cards and table placeholder shimmer.
- **Empty State:** "You haven't submitted any job applications yet. Browse open positions to get started." + "Browse Jobs" button.
- **Error States:** `401 Unauthorized` (Redirect to login), `500 Server Error`.
- **Mockability:** High. Mock applications with statuses `submitted`, `screening`, `needs_review`.

---

### C-02: Job Discovery (`/candidate/jobs`)
- **Role:** `candidate`
- **Purpose:** Search and browse active job requisitions available for application.
- **Required UI Components:** `SearchBar`, `DepartmentFilter`, `JobCardGrid`, `PaginationControls`
- **Data Required:** List of open jobs with criteria summaries.
- **API Endpoints & Methods:**
  1. `GET /api/v1/jobs?status=active&limit=50&offset=0`
- **User Actions:**
  - Search by title or department.
  - Click "View Details & Apply" on a job card -> navigates to `/candidate/jobs/:jobId`.
- **Expected Response:** `list[JobResponse]` (Includes criteria array per job).
- **Loading State:** Grid skeleton placeholders.
- **Empty State:** "No active job openings matching your search criteria."
- **Error States:** Network timeout / connection error banner.
- **Mockability:** High.

---

### C-03: Job Details & Application Submission (`/candidate/jobs/:jobId`)
- **Role:** `candidate`
- **Purpose:** Review detailed job description, required criteria, and submit an application with an uploaded PDF resume.
- **Required UI Components:** `JobHeader`, `CriteriaList`, `ApplyDrawerButton`, `FileUploadDropzone`, `ExtractionProgressBar`
- **Data Required:** Job details by ID, candidate profile.
- **API Endpoints & Methods:**
  1. `GET /api/v1/jobs/{id}`
  2. `POST /api/v1/documents` (Multipart: `file: PDF`) -> returns `document_id`
  3. `GET /api/v1/documents/{document_id}/status` (Poll every 1.5s until `processing_status == "completed"`)
  4. `POST /api/v1/applications` (Payload: `{ "job_id": jobId, "primary_document_id": document_id }`)
- **User Actions:**
  - Read criteria and required experience.
  - Click "Apply for Position" -> opens upload modal.
  - Drag and drop PDF resume -> triggers `POST /documents`.
  - Frontend polls `/documents/{document_id}/status` until status is `completed`.
  - Frontend triggers `POST /applications` linking `document_id` to `job_id`.
  - Navigates to `/candidate/applications/:applicationId`.
- **Expected Response:**
  - Job: `JobResponse`
  - Upload: `DocumentUploadResponse` (`{ "id": UUID, "processing_status": "queued", ... }`)
  - Status: `DocumentStatusResponse` (`{ "processing_status": "completed", "page_count": 2 }`)
  - Application: `ApplicationResponse` (`{ "id": UUID, "status": "submitted" }`)
- **Loading State:** Full page skeleton on initial load; modal upload progress bar during submission.
- **Empty State:** N/A (404 if invalid job ID).
- **Error States:**
  - `409 Conflict`: "You have already applied for this position."
  - `422 Unprocessable`: "Only PDF files under 10MB are permitted."
- **Mockability:** High.

---

### C-05: Application Evidence & Clarification View (`/candidate/applications/:applicationId`)
- **Role:** `candidate`
- **Purpose:** Full transparency view into how the candidate's resume claims were evaluated against job criteria, showing exact source quotes, page numbers, status (`supported`, `ambiguous`, `not_found`), and allowing the candidate to submit clarification for contested criteria.
- **Required UI Components:** `ApplicationMetaBar`, `CoverageSummaryBanner`, `CriterionEvidenceCard`, `SourceQuoteBox`, `ClarificationThread`, `SubmitClarificationModal`
- **Data Required:** Application details, linked Evaluation report.
- **API Endpoints & Methods:**
  1. `GET /api/v1/applications/{id}`
  2. `GET /api/v1/evaluations/{id}` (Evaluations associated with this application)
  3. `POST /api/v1/applications/{id}/clarifications` (Submit clarification contest)
- **User Actions:**
  - View factual evidence coverage: e.g. "4 of 5 Required Criteria Supported; 1 Ambiguous".
  - Inspect ambiguous criterion (e.g. "5+ Years Python Experience").
  - Click "Submit Clarification / Evidence" on the ambiguous criterion card.
  - Type explanation and optional document ID -> submit `POST /applications/:id/clarifications`.
  - Status updates to `CANDIDATE_CLARIFIED` and badge displays "Clarification Under Review".
- **Expected Responses:**
  - `ApplicationResponse`
  - `EvaluationResponse` (Contains `coverage`, `overall_status`, and `criteria_evaluations` array with `plain_language_explanation`, `source_excerpt`, `source_page`).
  - `CandidateClarificationResponse`
- **Loading State:** Shimmering evidence cards and coverage bar skeleton.
- **Empty State:** "Evaluation is currently in progress. Please check back shortly." (When evaluation has not yet been run).
- **Error States:**
  - `403 Forbidden`: Candidate attempting to access another candidate's application.
  - `404 Not Found`: Application does not exist.
- **Mockability:** High. Can use mock evaluations with grounded quotes from synthetic resumes.

---

### C-06: Candidate Skill & Profile Inventory (`/candidate/profile`)
- **Role:** `candidate`
- **Purpose:** View verified skill inventory extracted from candidate resumes across all submissions.
- **Required UI Components:** `SkillPillCloud`, `ConfidenceProgressBar`, `SourceExcerptTooltip`, `CategoryFilter`
- **Data Required:** Skills list for `current_user.id`.
- **API Endpoints & Methods:**
  1. `GET /api/v1/auth/me`
  2. `GET /api/v1/profiles/{current_user.id}/skills`
- **User Actions:** Browse extracted skills, filter by category (`programming_languages`, `frameworks`, `cloud`), verify source quote.
- **Expected Response:** `CandidateProfileSkillsResponse` (`{ "candidate_id": UUID, "total_skills": 12, "skills": [...] }`).
- **Loading State:** Tag cloud skeleton.
- **Empty State:** "No skills extracted yet. Upload a resume during an application to build your verified inventory."
- **Mockability:** High.

---

### E-01: Employer Dashboard (`/employer/dashboard`)
- **Role:** `employer_admin`
- **Purpose:** Executive overview of hiring pipeline: open requisitions, candidate screening status, and review escalations.
- **Required UI Components:** `PipelineStatCards`, `ActiveJobsTable`, `FlaggedEscalationsCard`, `QuickCreateJobButton`
- **Data Required:** Organization's jobs, applications, and review cases.
- **API Endpoints & Methods:**
  1. `GET /api/v1/jobs` (Organization isolated)
  2. `GET /api/v1/applications` (Organization isolated)
  3. `GET /api/v1/review-flags?status=pending`
- **User Actions:** View counts, click into job details, click into flagged review cases.
- **Expected Response:** `list[JobResponse]`, `list[ApplicationResponse]`, `list[ReviewFlagSummaryResponse]`.
- **Loading State:** Dashboard card skeletons.
- **Empty State:** "No active jobs or applicants found. Create your first job requisition to start screening."
- **Mockability:** High.

---

### E-02: Job Requisitions List (`/employer/jobs`)
- **Role:** `employer_admin`
- **Purpose:** Complete table of employer's job postings with criteria counts and status.
- **Required UI Components:** `RequisitionsTable`, `StatusFilterTabs`, `CreateRequisitionButton`, `PaginationBar`
- **Data Required:** Tenant jobs.
- **API Endpoints & Methods:**
  1. `GET /api/v1/jobs?limit=50&offset=0`
- **User Actions:** Filter by status (`active`, `draft`, `archived`), click job row -> `/employer/jobs/:jobId`, click "Create New Job" -> `/employer/jobs/new`.
- **Expected Response:** `list[JobResponse]`.
- **Loading State:** Table skeleton.
- **Empty State:** "No job requisitions found."
- **Mockability:** High.

---

### E-03: Create Job Requisition (`/employer/jobs/new`)
- **Role:** `employer_admin`, `reviewer`
- **Purpose:** Form to create a new requisition with explicit, versioned evaluation criteria and weights.
- **Required UI Components:** `JobDetailsFormSection`, `CriteriaBuilderTable`, `CategorySelector` (`required` vs `preferred`), `WeightSlider`, `SubmitButton`
- **Data Required:** None on entry.
- **API Endpoints & Methods:**
  1. `POST /api/v1/jobs` (Payload: `JobCreateRequest`)
- **User Actions:** Fill in title, department, description; add criteria rows (e.g. "PostgreSQL Optimization", category="required", weight=1.0); submit -> redirects to `/employer/jobs/:id`.
- **Expected Response:** `JobResponse` with created criteria.
- **Loading State:** Form button in pending state.
- **Error States:** `422 Unprocessable` (Criteria name missing, invalid weight).
- **Mockability:** High.

---

### E-04: Job Requisition Details (`/employer/jobs/:jobId`)
- **Role:** `employer_admin`, `reviewer`
- **Purpose:** View criteria versions, weighting, and applicants for a specific job requisition.
- **Required UI Components:** `JobHeaderDetails`, `CriteriaVersionCard`, `ApplicantsTable`, `ApplicantStatusBadge`, `EvaluateAllCTA`
- **Data Required:** Job with criteria, applications for `jobId`.
- **API Endpoints & Methods:**
  1. `GET /api/v1/jobs/{id}`
  2. `GET /api/v1/applications?job_id={id}`
- **User Actions:**
  - Inspect active criteria version.
  - Click on an applicant -> navigates to `/employer/applications/:applicationId`.
- **Expected Responses:** `JobResponse`, `list[ApplicationResponse]`.
- **Loading State:** Header and table skeleton.
- **Empty State (Applicants):** "No candidate applications received for this job requisition yet."
- **Mockability:** High.

---

### E-06: Candidate Evidence Dossier (`/employer/applications/:applicationId`)
- **Role:** `employer_admin`, `reviewer`
- **Purpose:** Deep evidence inspection for a specific candidate application: view AI evaluation coverage, source quotes, trigger deterministic AI evaluation if un-evaluated, and auto-flag ambiguous criteria for human review.
- **Required UI Components:**
  - `CandidateHeaderSummary`
  - `CoverageOverviewCard` (Supported / Ambiguous / Not Found counts)
  - `TriggerEvaluationButton` (Shown if status is `submitted`)
  - `AutoFlagReviewButton` (Shown if evaluation exists)
  - `CriterionEvidenceAccordion`
  - `SourceQuoteExcerptViewer`
- **Data Required:** Application details, Evaluation report.
- **API Endpoints & Methods:**
  1. `GET /api/v1/applications/{id}`
  2. `GET /api/v1/evaluations/{id}`
  3. `POST /api/v1/evaluations` (Payload: `{ "application_id": id }` to trigger evaluation)
  4. `POST /api/v1/review-flags` (Payload: `{ "application_id": id, "flag_preferred": false }` to auto-flag)
- **User Actions:**
  - If unevaluated, click "Run Evidence Evaluation" -> calls `POST /evaluations`, refreshes page with report.
  - If ambiguous criteria exist, click "Auto-Flag for Review" -> calls `POST /review-flags`, pushes cases to Reviewer Queue.
  - Review source excerpts, page coordinates, and confidence scores.
- **Expected Responses:** `ApplicationResponse`, `EvaluationResponse`, `ReviewFlagBatchResponse`.
- **Loading State:** Evaluation matrix skeleton shimmer.
- **Empty State:** "This application has not been evaluated yet. Click 'Run Evidence Evaluation' to start matching claims against job criteria."
- **Mockability:** High.

---

### R-01: Reviewer Dashboard (`/reviewer/dashboard`)
- **Role:** `reviewer`, `employer_admin`
- **Purpose:** Operational dashboard for human reviewers displaying assigned review queue workload, urgency, and recent verdicts.
- **Required UI Components:** `QueueUrgencyStats`, `AssignedCasesTable`, `QuickTriageButton`, `RecentVerdictsFeed`
- **Data Required:** Review flags assigned to reviewer.
- **API Endpoints & Methods:**
  1. `GET /api/v1/review-flags?status=pending`
  2. `GET /api/v1/auth/me`
- **User Actions:** Inspect pending flags count, click "Open Review Queue" -> `/reviewer/queue`.
- **Expected Response:** `list[ReviewFlagSummaryResponse]`.
- **Loading State:** Stats card skeletons.
- **Empty State:** "All caught up! No pending review cases in your queue."
- **Mockability:** High.

---

### R-02: Review Cases Queue (`/reviewer/queue`)
- **Role:** `reviewer`, `employer_admin`, `system_auditor`
- **Purpose:** Triage table of flagged ambiguous evidence cases awaiting human determination.
- **Required UI Components:** `CaseFilterTabs` (`pending`, `under_review`, `resolved`), `ReviewQueueTable`, `PriorityIndicator`, `ReasonColumn`, `CandidateNameColumn`
- **Data Required:** Review flags list.
- **API Endpoints & Methods:**
  1. `GET /api/v1/review-flags?status={filter}`
- **User Actions:** Filter by status, sort by priority, click a case row -> navigates to `/reviewer/cases/:caseId`.
- **Expected Response:** `list[ReviewFlagSummaryResponse]`.
- **Loading State:** Queue table skeleton.
- **Empty State:** "No review cases match the selected status."
- **Mockability:** High.

---

### R-03: Evidence Inspection & Decision Studio (`/reviewer/cases/:caseId`)
- **Role:** `reviewer`, `employer_admin`
- **Purpose:** Core human-in-the-loop review studio. Side-by-side view of the job criterion requirement against candidate resume quotes, previous candidate clarifications, and reviewer decision form requiring mandatory explanatory rationale.
- **Required UI Components:**
  - `CaseHeader` (Flag ID, Candidate Name, Job Title, Priority)
  - `CriterionBenchmarkPanel` (Name, Category, Weight, Requirement Description)
  - `EvidenceGroundingPanel` (AI Status, Confidence Score, AI Reasoning, Source Excerpt, Page Number)
  - `ClarificationHistoryThread` (Candidate statements, additional document attachments)
  - `ReviewDecisionForm` (Radio buttons: `accepted`, `rejected`, `requested_clarification`; Mandatory `rationale` text area; Submit Button)
  - `DecisionAuditHistory` (Prior reviewer verdicts)
- **Data Required:** Review case detail package.
- **API Endpoints & Methods:**
  1. `GET /api/v1/reviews/{id}`
  2. `POST /api/v1/reviews/{id}/decision` (Payload: `{ "decision": "accepted" | "rejected" | "requested_clarification", "mandatory_rationale": "..." }`)
- **User Actions:**
  - Read evidence quote and compare with criterion.
  - Review candidate clarification statements if present.
  - Select verdict (`accepted` -> verifies evidence; `rejected` -> rejects evidence; `requested_clarification` -> sends back to candidate).
  - Type mandatory explanatory rationale (cannot be empty or whitespace).
  - Click "Submit Decision" -> commits decision, transitions flag to `resolved`, updates audit log.
  - Navigates back to queue or displays success confirmation.
- **Expected Responses:**
  - Detail: `ReviewCaseDetailResponse`
  - Decision: `ReviewDecisionResponse` (`{ "id": UUID, "decision": "accepted", "new_verification_state": "human_verified", "flag_status": "resolved", ... }`)
- **Loading State:** Two-column split layout skeleton.
- **Empty State:** N/A (404 if invalid ID).
- **Error States:**
  - `422 Unprocessable`: "Mandatory rationale cannot be empty."
  - `403 Forbidden`: Reviewer not assigned or authorized.
- **Mockability:** High.

---

### A-04: Cryptographic Hash-Chain Verification Report (`/auditor/verification`)
- **Role:** `system_auditor`, `employer_admin`
- **Purpose:** Formal audit report proving cryptographic continuity and tamper-evidence across all platform events (candidate actions, AI extractions, reviewer verdicts).
- **Required UI Components:**
  - `ChainIntegrityBanner` (Valid / Invalid status badge)
  - `VerificationMetricsGrid` (Total Events, Verified Events, Head Hash)
  - `DiscrepancyAlert` (Shown only if `is_valid == false`: broken sequence number, broken event ID)
  - `VerifyChainCTAButton` ("Re-Verify Hash Chain")
  - `LegalComplianceNotice`
- **Data Required:** Hash-chain verification report.
- **API Endpoints & Methods:**
  1. `GET /api/v1/audit/verify`
- **User Actions:** View verification report; click "Re-Verify Now" to re-execute cryptographic hash check.
- **Expected Response:** `AuditVerificationReportResponse` (`{ "is_valid": true, "total_events": 142, "verified_events": 142, "chain_head_hash": "a3f...", "tamper_evidence_disclaimer": "..." }`).
- **Loading State:** Circular cryptographic computation spinner / progress shimmer.
- **Error States:** Displays broken link card if chain is broken.
- **Mockability:** High.

---

### A-02: Audit Ledger & Explorer (`/auditor/events`)
- **Role:** `system_auditor`, `employer_admin`
- **Purpose:** Searchable, filterable audit log of every state transition in ClearHire.
- **Required UI Components:** `AuditFilterBar` (`resource_type`, `actor_id`, `resource_id`), `AuditDataTable`, `HashBadge`, `PayloadDrawer`
- **Data Required:** Audit events list.
- **API Endpoints & Methods:**
  1. `GET /api/v1/audit?resource_type={type}&limit=50&offset=0`
- **User Actions:** Filter by resource type (`job`, `application`, `review_decision`, `user`), inspect SHA256 event hash and previous hash.
- **Expected Response:** `list[AuditEventDetailResponse]`.
- **Loading State:** Table shimmer.
- **Empty State:** "No audit events matching criteria."
- **Mockability:** High.

---

### B-01: Benchmark & Simulation Explorer (`/benchmark`)
- **Role:** Cross-Role / Admin / Demonstration
- **Purpose:** Demonstrates ClearHire's core differentiation by executing a reproducible before/after benchmark comparing traditional literal-keyword screening against ClearHire evidence matching on a ground-truth dataset. Also simulates SAP SuccessFactors feed preview & import.
- **Required UI Components:**
  - `BenchmarkMetricsComparisonCard` (Baseline Accuracy vs ClearHire Accuracy, F1, False Negatives)
  - `PerCriterionComparisonTable`
  - `FailureModeBreakdownChart`
  - `SFFeedSimulationSection` (View synthetic feed JSON, Import Feed button)
- **Data Required:** Benchmark report and synthetic feed.
- **API Endpoints & Methods:**
  1. `GET /api/v1/benchmark/run`
  2. `GET /api/v1/integrations/successfactors/feed`
  3. `POST /api/v1/integrations/successfactors/import`
- **User Actions:** Click "Run Benchmark" -> recomputes before/after metrics; click "Import SuccessFactors Feed" -> ingests sample applicants into live database.
- **Expected Responses:** `BenchmarkReport`, `SFApplicantFeedBatch`, `SFImportResult`.
- **Loading State:** Benchmark execution progress bar.
- **Mockability:** High.

---

## 2. Cross-Cutting API Classification

### Endpoints Used Across Multiple Pages
- `GET /api/v1/auth/me`: Invoked on application boot, navigation shell, profile view, and role checking.
- `GET /api/v1/jobs`: Used by Candidate Job Discovery (`C-02`), Employer Dashboard (`E-01`), and Employer Requisitions List (`E-02`).
- `GET /api/v1/applications`: Used by Candidate Dashboard (`C-01`), Candidate Applications (`C-04`), Employer Dashboard (`E-01`), and Employer Applicants (`E-05`).
- `GET /api/v1/review-flags`: Used by Employer Dashboard (`E-01`), Reviewer Dashboard (`R-01`), and Review Queue (`R-02`).

### Endpoints Without Dedicated Full Pages (Modal / Background Only)
- `POST /api/v1/documents`: Document upload triggered inside Apply Modal (`M-C1`).
- `GET /api/v1/documents/{id}/status`: Polled asynchronously during upload processing.
- `POST /api/v1/documents/{id}/extract`: Triggered in background during resume processing.
- `POST /api/v1/evaluations`: Triggered via button click in Employer Application Dossier (`E-06`).
- `POST /api/v1/review-flags`: Triggered via "Auto-Flag" button in Employer Application Dossier (`E-06`).
- `POST /api/v1/applications/{id}/clarifications`: Submitted via Clarification Modal (`M-C2`).
- `POST /api/v1/reviews/{id}/decision`: Submitted via Reviewer Studio decision form (`R-03`).
- `POST /api/v1/auth/provision`: Submitted via Team Provisioning Modal (`M-E2`).

### Endpoints With No Obvious Production Frontend Consumer
- `GET /api/v1/health`, `GET /api/v1/health/live`, `GET /api/v1/health/ready`: System infrastructure probes (consumed by Kubernetes / Docker Compose health checks, not regular UI pages).
- `GET /api/v1/reviews` & `GET /api/v1/review-flags/{id}`: Redundant route aliases hidden from OpenAPI schema. Frontend uses canonical `/review-flags` and `/reviews/{id}`.
- `POST /api/v1/audit/verify` & `POST /api/v1/benchmark/run`: Redundant POST aliases hidden from OpenAPI schema. Frontend uses GET variants.
- `POST /api/v1/reviews/{id}/clarification`: Redundant alias for candidate clarification (frontend standardizes on `/applications/{id}/clarifications`).
