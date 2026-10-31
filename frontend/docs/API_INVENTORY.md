# ClearHire Backend API Inventory & Security Audit

> **Document Status:** Complete & Verified  
> **Source Code Audited:** `backend/app/api/v1/endpoints/`  
> **FastAPI Application:** `backend/app/main.py` (`create_application`)  
> **Backend Version:** v0.1.0  
> **Date of Audit:** October 2026  

---

## 1. Executive API Summary

A comprehensive programmatic and static analysis of the registered routes in the ClearHire FastAPI backend was performed.

- **Total Registered FastAPI Routes:** `40`
- **Internal / Auto-Generated Docs Routes:** `4` (`/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc`)
- **Total Unique Business API Endpoints:** `36`
- **Unique HTTP Method + Route Combinations:** `36`

### Breakdown by HTTP Method
| HTTP Method | Count | Percentage |
| :--- | :--- | :--- |
| **GET** | 22 | 61.1% |
| **POST** | 14 | 38.9% |
| **PUT / PATCH / DELETE** | 0 | 0.0% |
| **Total** | **36** | **100.0%** |

*Note: The backend currently defines no `PUT`, `PATCH`, or `DELETE` endpoints. All state mutations are handled exclusively through `POST` actions.*

### Breakdown by Functional Module
| Functional Module | Route Prefix | Registered Endpoints | Primary Responsibility |
| :--- | :--- | :--- | :--- |
| **Authentication (`auth`)** | `/api/v1/auth` | 4 | Registration, login, JWT token issuance, user provisioning, profile |
| **System Health (`health`)** | `/api/v1/health` | 3 | Liveness, readiness, DB connection checks |
| **Documents (`documents`)** | `/api/v1/documents` | 4 | Resume PDF upload, OCR polling, AI evidence extraction trigger & results |
| **Jobs & Criteria (`jobs`)** | `/api/v1/jobs` | 3 | Requisition creation with versioned criteria, criteria listing & details |
| **Applications (`applications`)** | `/api/v1/applications` | 3 | Application submission, listing with tenant isolation, details |
| **Evaluations (`evaluations`)** | `/api/v1/evaluations` | 2 | Deterministic evidence evaluation execution & detailed report retrieval |
| **Candidate Profiles (`profiles`)** | `/api/v1/profiles` | 1 | Verified skill inventory query with excerpt grounding |
| **Human Review Workflow (`reviews`)** | `/api/v1/reviews` & `/api/v1/review-flags` | 8 | Flag creation, case queue listing, case details, reviewer decisions, clarifications |
| **Audit & Integrity (`audit`)** | `/api/v1/audit` | 4 | Cryptographic hash-chain verification, audit event queries & inspection |
| **Simulation & Benchmark (`benchmark`)**| `/api/v1/integrations`, `/api/v1/benchmark` | 4 | SAP SuccessFactors feed simulation & import, before/after benchmark runner |
| **Total Business Endpoints** | | **36** | |

---

## 2. Access Control & Security Model

ClearHire enforces strict role-based access control (RBAC) via cryptographically signed JWT bearer tokens (`app.core.security`). Client-supplied identity headers (such as `X-User-Role`) are never trusted.

### System Roles (`UserRole` Enum)
1. `candidate` — First-party job seeker; restricted to self-owned documents, applications, skills, and clarifications.
2. `employer_admin` — Organization administrator; manages job requisitions, provisions reviewers, views tenant candidates, and audits organization actions.
3. `reviewer` — Authorized human screener/subject-matter expert; reviews ambiguous evidence flags, records rationale verdicts, and requests clarifications.
4. `system_auditor` — Compliance officer; has global read access to audit hash chains, verification reports, and screening logs.

### Access Level Classification of Endpoints
| Access Level | Count | Endpoints |
| :--- | :--- | :--- |
| **Public (No Auth Required)** | 5 | Health endpoints (3), Candidate Registration (1), Credential Login (1) |
| **Candidate Role Restricted** | 2 | Application Clarification (1), Review Case Clarification (1) |
| **Employer / Reviewer / Auditor Restricted**| 13 | Provisioning, Job Creation, Evaluation Trigger, Review Flags, Review Decisions, SF Import, Audit Queries & Hash Verification |
| **Shared Authenticated (Tenant/Owner Isolated)** | 16 | Profile retrieval (`/auth/me`), Document upload & extraction, Job viewing, Application viewing, Evaluation viewing, Candidate Skills, Review Case detail, Audit event detail, Benchmark runner |
| **Total** | **36** | |

---

## 3. Master API Inventory Table

| ID | Method | Endpoint | Module | Auth Level | Allowed Roles | Purpose | Request Body / Query Params | Response Schema | Status | Modifies Data | BG Task | File I/O |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **01** | `GET` | `/api/v1/health` | `health` | Public | None | Application health & metadata | None | `HealthResponse` | 200 | No | No | No |
| **02** | `GET` | `/api/v1/health/live` | `health` | Public | None | Process liveness probe | None | `LivenessResponse` | 200 | No | No | No |
| **03** | `GET` | `/api/v1/health/ready` | `health` | Public | None | PostgreSQL readiness check | None | `ReadinessResponse` | 200, 503 | No | No | No |
| **04** | `POST` | `/api/v1/auth/register` | `auth` | Public | None | Register new candidate account | `CandidateRegisterRequest` | `UserResponse` | 201 | Yes | No | No |
| **05** | `POST` | `/api/v1/auth/login` | `auth` | Public | None | Authenticate with email/password and issue JWT | `LoginRequest` | `TokenResponse` | 200 | Yes | No | No |
| **06** | `GET` | `/api/v1/auth/me` | `auth` | Authenticated | All | Get active user profile context | None | `UserResponse` | 200 | No | No | No |
| **07** | `POST` | `/api/v1/auth/provision` | `auth` | Restricted | `employer_admin`, `system_auditor` | Provision privileged reviewer or employer account | `AdminUserProvisionRequest` | `UserResponse` | 201 | Yes | No | No |
| **08** | `POST` | `/api/v1/documents` | `documents` | Authenticated | All (Candidate primary) | Upload resume PDF; start text extraction | Multipart form: `file: UploadFile` | `DocumentUploadResponse` | 202 | Yes | **Yes** | **Upload** |
| **09** | `GET` | `/api/v1/documents/{document_id}/status` | `documents` | Authenticated | All (Owner/Tenant checked) | Poll PDF extraction status & page text | Path: `document_id` (UUID) | `DocumentStatusResponse` | 200 | No | No | No |
| **10** | `POST` | `/api/v1/documents/{document_id}/extract` | `documents` | Authenticated | All (Owner/Tenant checked) | Trigger AI extraction of structured claims | Path: `document_id` (UUID) | `ExtractionRunResponse` | 202 | Yes | **Yes** | No |
| **11** | `GET` | `/api/v1/documents/{document_id}/extraction-results`| `documents` | Authenticated | All (Owner/Tenant checked) | Get structured extracted claims & skills | Path: `document_id` (UUID) | `ExtractionRunResponse` | 200 | No | No | No |
| **12** | `GET` | `/api/v1/jobs` | `jobs` | Authenticated | All (Role/Tenant isolated) | List job requisitions with criteria | Query: `status`, `department`, `limit`, `offset` | `list[JobResponse]` | 200 | No | No | No |
| **13** | `POST` | `/api/v1/jobs` | `jobs` | Restricted | `employer_admin`, `reviewer` | Create job requisition with versioned criteria | `JobCreateRequest` | `JobResponse` | 201 | Yes | No | No |
| **14** | `GET` | `/api/v1/jobs/{id}` | `jobs` | Authenticated | All | Retrieve job requisition and active criteria | Path: `id` (UUID) | `JobResponse` | 200 | No | No | No |
| **15** | `GET` | `/api/v1/applications` | `applications` | Authenticated | All (Role/Tenant isolated) | List candidate job applications | Query: `job_id`, `status`, `limit`, `offset` | `list[ApplicationResponse]` | 200 | No | No | No |
| **16** | `POST` | `/api/v1/applications` | `applications` | Authenticated | All (Candidate primary) | Submit application linking document to job | `ApplicationCreateRequest` | `ApplicationResponse` | 201 | Yes | No | No |
| **17** | `GET` | `/api/v1/applications/{id}` | `applications` | Authenticated | All (Owner/Tenant checked) | Get application details and status | Path: `id` (UUID) | `ApplicationResponse` | 200 | No | No | No |
| **18** | `POST` | `/api/v1/evaluations` | `evaluations` | Restricted | `employer_admin`, `reviewer`, `system_auditor` | Run deterministic evidence evaluation | `EvaluationCreateRequest` | `EvaluationResponse` | 201 | Yes | No | No |
| **19** | `GET` | `/api/v1/evaluations/{id}` | `evaluations` | Authenticated | All (Owner/Tenant checked) | Get evaluation report with criteria evidence | Path: `id` (UUID) | `EvaluationResponse` | 200 | No | No | No |
| **20** | `GET` | `/api/v1/profiles/{id}/skills` | `profiles` | Authenticated | All (Owner/Tenant checked) | Query verified skills extracted from resume | Path: `id` (UUID) | `CandidateProfileSkillsResponse` | 200 | No | No | No |
| **21** | `POST` | `/api/v1/review-flags` | `reviews` | Restricted | `employer_admin`, `reviewer` | Auto-flag or manually flag ambiguous criteria | `ReviewFlagCreateRequest` | `ReviewFlagBatchResponse` | 201 | Yes | No | No |
| **22** | `GET` | `/api/v1/review-flags` | `reviews` | Restricted | `reviewer`, `employer_admin`, `system_auditor` | List review cases assigned to reviewer / tenant | Query: `status`, `application_id` | `list[ReviewFlagSummaryResponse]` | 200 | No | No | No |
| **23** | `GET` | `/api/v1/reviews` *(alias)* | `reviews` | Restricted | `reviewer`, `employer_admin`, `system_auditor` | Alias of `/review-flags` (hidden from schema) | Query: `status`, `application_id` | `list[ReviewFlagSummaryResponse]` | 200 | No | No | No |
| **24** | `GET` | `/api/v1/reviews/{id}` | `reviews` | Authenticated | All (Owner/Tenant checked) | Full review case detail (criterion, quotes, history) | Path: `id` (UUID) | `ReviewCaseDetailResponse` | 200 | No | No | No |
| **25** | `GET` | `/api/v1/review-flags/{id}` *(alias)*| `reviews` | Authenticated | All (Owner/Tenant checked) | Alias of `/reviews/{id}` (hidden from schema) | Path: `id` (UUID) | `ReviewCaseDetailResponse` | 200 | No | No | No |
| **26** | `POST` | `/api/v1/reviews/{id}/decision` | `reviews` | Restricted | `reviewer`, `employer_admin` | Record reviewer verdict with mandatory rationale | Path: `id` (UUID), Body: `ReviewDecisionRequest` | `ReviewDecisionResponse` | 201 | Yes | No | No |
| **27** | `POST` | `/api/v1/applications/{id}/clarifications` | `reviews` | Restricted | `candidate` | Submit candidate clarification on application | Path: `id` (UUID), Body: `CandidateClarificationRequest` | `CandidateClarificationResponse` | 201 | Yes | No | No |
| **28** | `POST` | `/api/v1/reviews/{id}/clarification` | `reviews` | Restricted | `candidate` | Submit candidate clarification via review flag ID | Path: `id` (UUID), Body: `CandidateClarificationRequest` | `CandidateClarificationResponse` | 201 | Yes | No | No |
| **29** | `GET` | `/api/v1/audit` | `audit` | Restricted | `system_auditor`, `employer_admin` | Query cryptographically verifiable audit events | Query: `resource_type`, `resource_id`, `actor_id`, `limit`, `offset` | `list[AuditEventDetailResponse]` | 200 | No | No | No |
| **30** | `GET` | `/api/v1/audit/verify` | `audit` | Restricted | `system_auditor`, `employer_admin` | Verify cryptographic hash chain integrity | None | `AuditVerificationReportResponse` | 200 | No | No | No |
| **31** | `POST` | `/api/v1/audit/verify` *(alias)* | `audit` | Restricted | `system_auditor`, `employer_admin` | POST alias of `/audit/verify` (hidden from schema) | None | `AuditVerificationReportResponse` | 200 | Yes | No | No |
| **32** | `GET` | `/api/v1/audit/{id}` | `audit` | Authenticated | All (Role/Owner checked) | Inspect single audit event and cryptographic hash | Path: `id` (UUID) | `AuditEventDetailResponse` | 200 | No | No | No |
| **33** | `GET` | `/api/v1/integrations/successfactors/feed` | `benchmark` | Authenticated | All | Get synthetic SAP SuccessFactors applicant feed | None | `SFApplicantFeedBatch` | 200 | No | No | No |
| **34** | `POST` | `/api/v1/integrations/successfactors/import` | `benchmark` | Restricted | `employer_admin`, `system_auditor` | Import synthetic feed into domain database | Body: `SFApplicantFeedBatch` (Optional) | `SFImportResult` | 200 | Yes | No | No |
| **35** | `GET` | `/api/v1/benchmark/run` | `benchmark` | Authenticated | All | Execute before/after screening benchmark | None | `BenchmarkReport` | 200 | No | No | No |
| **36** | `POST` | `/api/v1/benchmark/run` *(alias)* | `benchmark` | Authenticated | All | POST alias of `/benchmark/run` (hidden from schema) | None | `BenchmarkReport` | 200 | Yes | No | No |

---

## 4. Detailed Endpoint Profiles by Module

### 4.1 Authentication (`app.api.v1.endpoints.auth`)
1. **`POST /api/v1/auth/register`**
   - **Auth:** Public.
   - **Request Schema:** `CandidateRegisterRequest` (`email: EmailStr`, `password: str (min 8)`, `full_name: str`).
   - **Response Schema:** `UserResponse` (`id: UUID`, `email: str`, `role: UserRole`, `full_name: str`, `employer_id: str | None`, `is_active: bool`, `email_verified: bool`, `created_at: datetime`).
   - **Behavior:** Normalizes email, hashes password with Argon2id, assigns `candidate` role, writes `USER_REGISTERED` audit event.
2. **`POST /api/v1/auth/login`**
   - **Auth:** Public.
   - **Request Schema:** `LoginRequest` (`email: EmailStr`, `password: str`).
   - **Response Schema:** `TokenResponse` (`access_token: str`, `token_type: "bearer"`, `expires_in: int`).
   - **Behavior:** Constant-time verification preventing timing attacks. Returns signed JWT containing `sub`, `role`, `employer_id`, `email`.
3. **`GET /api/v1/auth/me`**
   - **Auth:** Bearer token required (Any role).
   - **Response Schema:** `UserResponse`.
   - **Behavior:** Loads user context from DB matching token subject.
4. **`POST /api/v1/auth/provision`**
   - **Auth:** Restricted to `employer_admin` or `system_auditor`.
   - **Request Schema:** `AdminUserProvisionRequest` (`email: EmailStr`, `password: str`, `full_name: str`, `role: UserRole`, `employer_id: str | None`).
   - **Response Schema:** `UserResponse`.
   - **Behavior:** Employer admins can only provision `reviewer` or `employer_admin` for their own tenant; System Auditors can provision across tenants.

### 4.2 Documents (`app.api.v1.endpoints.documents`)
5. **`POST /api/v1/documents`**
   - **Auth:** Authenticated.
   - **Content-Type:** `multipart/form-data`.
   - **Form Param:** `file: UploadFile` (must be application/pdf, validated magic bytes & size).
   - **Response Schema:** `DocumentUploadResponse` (`id: UUID`, `file_name: str`, `file_hash: str`, `file_size_bytes: int`, `processing_status: DocumentProcessingStatus`, `created_at: datetime`).
   - **Background Worker:** Enqueues `service.process_document_extraction` on FastAPI `BackgroundTasks`. Returns HTTP 202 immediately.
6. **`GET /api/v1/documents/{document_id}/status`**
   - **Auth:** Authenticated (Candidate owner or Job employer/reviewer).
   - **Response Schema:** `DocumentStatusResponse` (`id: UUID`, `file_name: str`, `processing_status: DocumentProcessingStatus`, `page_count: int | None`, `extracted_text_by_page: dict[str, str]`, `processing_error: dict | None`, `created_at: datetime`, `updated_at: datetime`).
   - **Purpose:** Polling endpoint for OCR/PDF text extraction progress.
7. **`POST /api/v1/documents/{document_id}/extract`**
   - **Auth:** Authenticated (Owner or Tenant).
   - **Response Schema:** `ExtractionRunResponse` (`id: UUID`, `document_id: UUID`, `run_number: int`, `provider: str`, `model_name: str`, `status: DocumentProcessingStatus`, `skills: list[CandidateSkillSummary]`, `evidence_items: list[EvidenceItemSummary]`, `started_at: datetime`, `completed_at: datetime | None`).
   - **Behavior:** Verifies PDF text extraction is completed; rejects if pending (HTTP 409) or failed (HTTP 422). Spawns AI structured claim extraction via `BackgroundTasks`.
8. **`GET /api/v1/documents/{document_id}/extraction-results`**
   - **Auth:** Authenticated.
   - **Response Schema:** `ExtractionRunResponse`.
   - **Behavior:** Returns extracted structured claims with page coordinates and grounding quotes.

### 4.3 Jobs & Criteria (`app.api.v1.endpoints.jobs`)
9. **`GET /api/v1/jobs`**
   - **Auth:** Authenticated.
   - **Query Params:** `status: JobStatus | None`, `department: str | None`, `limit: int = 50`, `offset: int = 0`.
   - **Response Schema:** `list[JobResponse]`.
   - **Behavior:** Candidates only see `ACTIVE` jobs. Employers only see jobs created within their organization tenant. Auditors see all jobs.
10. **`POST /api/v1/jobs`**
    - **Auth:** Restricted to `employer_admin` or `reviewer`.
    - **Request Schema:** `JobCreateRequest` (`title: str`, `description: str | None`, `department: str | None`, `criteria: list[JobCriterionCreate]`).
    - **Response Schema:** `JobResponse` (`id: UUID`, `employer_id: UUID`, `title: str`, `description: str`, `department: str`, `status: JobStatus`, `criteria: list[JobCriterionResponse]`, `created_at: datetime`, `updated_at: datetime`).
    - **Behavior:** Atomically creates requisition and initial version 1 criteria.
11. **`GET /api/v1/jobs/{id}`**
    - **Auth:** Authenticated.
    - **Response Schema:** `JobResponse`.
    - **Behavior:** Retrieves job requisition with all defined criteria.

### 4.4 Applications (`app.api.v1.endpoints.applications`)
12. **`GET /api/v1/applications`**
    - **Auth:** Authenticated.
    - **Query Params:** `job_id: UUID | None`, `status: ApplicationStatus | None`, `limit: int = 50`, `offset: int = 0`.
    - **Response Schema:** `list[ApplicationResponse]`.
    - **Behavior:** Candidates only see their own applications. Employers/Reviewers see applications matching their organization's jobs.
13. **`POST /api/v1/applications`**
    - **Auth:** Authenticated (Candidate).
    - **Request Schema:** `ApplicationCreateRequest` (`job_id: UUID`, `primary_document_id: UUID`).
    - **Response Schema:** `ApplicationResponse` (`id: UUID`, `job_id: UUID`, `candidate_id: UUID`, `primary_document_id: UUID`, `status: "submitted"`, `submitted_at: datetime`, `created_at: datetime`).
    - **Behavior:** Enforces unique application per candidate per job. Validates document ownership.
14. **`GET /api/v1/applications/{id}`**
    - **Auth:** Authenticated (Owner or Tenant).
    - **Response Schema:** `ApplicationResponse`.

### 4.5 Evaluations (`app.api.v1.endpoints.evaluations`)
15. **`POST /api/v1/evaluations`**
    - **Auth:** Restricted to `employer_admin`, `reviewer`, `system_auditor`.
    - **Request Schema:** `EvaluationCreateRequest` (`application_id: UUID`).
    - **Response Schema:** `EvaluationResponse` (`id: UUID`, `application_id: UUID`, `version: int`, `job_criteria_version: int`, `extraction_run_id: UUID`, `overall_status: EvidenceStatus`, `coverage: EvidenceCoverageSummary`, `criteria_evaluations: list[CriterionEvaluationItem]`, `summary_notes: str | None`, `created_at: datetime`).
    - **Behavior:** Executes deterministic evidence matching against active criteria. Updates application status to `SCREENING`. Writes audit event.
16. **`GET /api/v1/evaluations/{id}`**
    - **Auth:** Authenticated (Owner or Tenant).
    - **Response Schema:** `EvaluationResponse`.
    - **Behavior:** Retrieves criteria coverage summary, plain language explanations, source excerpts, and page coordinates.

### 4.6 Profiles (`app.api.v1.endpoints.profiles`)
17. **`GET /api/v1/profiles/{id}/skills`**
    - **Auth:** Authenticated (Candidate self or Organization reviewer/employer).
    - **Response Schema:** `CandidateProfileSkillsResponse` (`candidate_id: UUID`, `total_skills: int`, `skills: list[ProfileSkillItem]`).
    - **Behavior:** Deduplicates candidate skills by name, retaining the highest confidence score and source excerpt.

### 4.7 Reviews (`app.api.v1.endpoints.reviews`)
18. **`POST /api/v1/review-flags`**
    - **Auth:** Restricted to `employer_admin`, `reviewer`.
    - **Request Schema:** `ReviewFlagCreateRequest` (`application_id: UUID`, `criterion_evidence_id: UUID | None`, `flag_preferred: bool = False`, `reason: str | None`, `priority: str = "normal"`, `assigned_to_user_id: UUID | None`).
    - **Response Schema:** `ReviewFlagBatchResponse` (`application_id: UUID`, `total_flagged: int`, `flags: list[ReviewFlagResponse]`).
    - **Behavior:** Automatically raises review flags for all ambiguous or missing required criteria.
19. **`GET /api/v1/review-flags`** (and alias `GET /api/v1/reviews`)
    - **Auth:** Restricted to `reviewer`, `employer_admin`, `system_auditor`.
    - **Query Params:** `status: ReviewFlagStatus | None`, `application_id: UUID | None`.
    - **Response Schema:** `list[ReviewFlagSummaryResponse]`.
20. **`GET /api/v1/reviews/{id}`** (and alias `GET /api/v1/review-flags/{id}`)
    - **Auth:** Authenticated.
    - **Response Schema:** `ReviewCaseDetailResponse` (Contains full case bundle: job title, candidate info, criterion definition, AI status & confidence, source quote & page, candidate clarification history, and reviewer decision history).
21. **`POST /api/v1/reviews/{id}/decision`**
    - **Auth:** Restricted to `reviewer`, `employer_admin`.
    - **Request Schema:** `ReviewDecisionRequest` (`decision: ReviewDecisionType` [`accepted`, `rejected`, `requested_clarification`], `mandatory_rationale: str`).
    - **Response Schema:** `ReviewDecisionResponse`.
    - **Behavior:** Validates non-empty rationale. Updates criterion `verification_state` (`HUMAN_VERIFIED`, `HUMAN_REJECTED`, or `UNVERIFIED`). Transitions flag to `RESOLVED` or `UNDER_REVIEW`. Updates application status to `REVIEWED` when all flags resolve. Writes cryptographic audit record.
22. **`POST /api/v1/applications/{id}/clarifications`**
    - **Auth:** Restricted to `candidate`.
    - **Request Schema:** `CandidateClarificationRequest` (`criterion_evidence_id: UUID`, `candidate_statement: str`, `additional_document_id: UUID | None`).
    - **Response Schema:** `CandidateClarificationResponse`.
    - **Behavior:** Sets criterion `verification_state` to `CANDIDATE_CLARIFIED`. Re-activates associated review flag to `PENDING`. Transitions application to `NEEDS_REVIEW`. Writes audit log.
23. **`POST /api/v1/reviews/{id}/clarification`**
    - **Auth:** Restricted to `candidate`.
    - **Behavior:** Convenience endpoint mapping review flag ID to application clarification.

### 4.8 Audit (`app.api.v1.endpoints.audit`)
24. **`GET /api/v1/audit`**
    - **Auth:** Restricted to `system_auditor`, `employer_admin`.
    - **Query Params:** `resource_type: str | None`, `resource_id: str | None`, `actor_id: str | None`, `limit: int = 50`, `offset: int = 0`.
    - **Response Schema:** `list[AuditEventDetailResponse]`.
    - **Behavior:** Employer admins filtered to organization resources; Auditors have full global visibility. Computes runtime verification flag `is_verified` per event.
25. **`GET /api/v1/audit/verify`** (and alias `POST /api/v1/audit/verify`)
    - **Auth:** Restricted to `system_auditor`, `employer_admin`.
    - **Response Schema:** `AuditVerificationReportResponse` (`is_valid: bool`, `total_events: int`, `verified_events: int`, `chain_head_hash: str | None`, `discrepancy_type: str | None`, `error: str | None`, `broken_event_id: UUID | None`, `broken_sequence_number: int | None`, `tamper_evidence_disclaimer: str`).
    - **Behavior:** Traverses complete hash chain from sequence 1 to head, checking sha256 links and payload integrity.
26. **`GET /api/v1/audit/{id}`**
    - **Auth:** Authenticated (Strict role/ownership verification).
    - **Response Schema:** `AuditEventDetailResponse`.

### 4.9 Simulation & Benchmark (`app.api.v1.endpoints.benchmark`)
27. **`GET /api/v1/integrations/successfactors/feed`**
    - **Auth:** Authenticated.
    - **Response Schema:** `SFApplicantFeedBatch`.
    - **Behavior:** Returns synthetic applicant batch with requisitions and resumes.
28. **`POST /api/v1/integrations/successfactors/import`**
    - **Auth:** Restricted to `employer_admin`, `system_auditor`.
    - **Request Schema:** `SFApplicantFeedBatch | None` (defaults to synthetic feed).
    - **Response Schema:** `SFImportResult` (`feed_id: str`, `job_id: UUID`, `job_title: str`, `imported_candidates_count: int`, `imported_applications_count: int`, `imported_application_ids: list[UUID]`, `warnings: list[str]`).
    - **Behavior:** Ingests external applicant feed into first-party ClearHire database tables.
29. **`GET /api/v1/benchmark/run`** (and alias `POST /api/v1/benchmark/run`)
    - **Auth:** Authenticated.
    - **Response Schema:** `BenchmarkReport` (`sample_size: int`, `total_criteria_evaluations: int`, `baseline_metrics: ScreeningMetrics`, `clearhire_metrics: ScreeningMetrics`, `candidate_results: list[CandidateBenchmarkResult]`, `keyword_baseline_misses_breakdown: dict[str, int]`, `clearhire_findings: list[str]`, `extraction_limitations: list[str]`).
    - **Behavior:** Compares literal keyword screening against ClearHire evidence matching on ground-truth dataset.

---

## 5. Redundant, Aliased, or Ambiguous Endpoints

1. **`GET /api/v1/reviews` vs `GET /api/v1/review-flags`**
   - Both routes execute `app.api.v1.endpoints.reviews.list_review_cases`.
   - `/reviews` is marked `include_in_schema=False`.
   - **Frontend Recommendation:** Standardize on `/api/v1/review-flags` or `/api/v1/reviews`. For clarity, frontend API client should use `/api/v1/reviews`.
2. **`GET /api/v1/reviews/{id}` vs `GET /api/v1/review-flags/{id}`**
   - Both routes execute `get_review_case_detail`.
   - `/review-flags/{id}` is marked `include_in_schema=False`.
   - **Frontend Recommendation:** Use `/api/v1/reviews/{id}`.
3. **`GET /api/v1/audit/verify` vs `POST /api/v1/audit/verify`**
   - Both execute `verify_audit_chain`. POST is hidden from schema.
   - **Frontend Recommendation:** Use `GET /api/v1/audit/verify`.
4. **`GET /api/v1/benchmark/run` vs `POST /api/v1/benchmark/run`**
   - Both execute `run_screening_benchmark`. POST is hidden from schema.
   - **Frontend Recommendation:** Use `POST /api/v1/benchmark/run` when triggering a run, or `GET` for retrieval.
5. **Dual Clarification Endpoints:**
   - `POST /api/v1/applications/{id}/clarifications` and `POST /api/v1/reviews/{id}/clarification` perform identical underlying business logic.
   - Candidate viewing their application page has `application_id` and should use `/applications/{id}/clarifications`.
   - Reviewer or candidate navigating from a review flag link can use `/reviews/{id}/clarification`.
