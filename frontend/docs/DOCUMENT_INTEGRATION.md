# ClearHire — Document Upload & Text Extraction Integration Specification (Feature 3A)

**Integration Date**: November 1, 2026  
**Scope**: Candidate Resume Upload, Background Text Extraction, and Verbatim Page-by-Page Inspection  
**Backend Reference**: FastAPI Backend (Read-Only, `/home/vanilla/Desktop/hackathon/sap/backend`)  
**Frontend Implementation**: `src/services/api/documentService.ts`, `src/pages/candidate/CandidateJobDetailPage.tsx`

---

## 1. Actual Backend Document Endpoints

The backend provides five dedicated document endpoints under `/api/v1/documents`:

| Endpoint | HTTP Method | Expected Status | Authorized Roles | Description |
|---|---|---|---|---|
| `/api/v1/documents` | `POST` | `202 Accepted` | `CANDIDATE` (or any authenticated user) | Uploads PDF resume file as `multipart/form-data`, validates format/size, persists record with `processing_status="queued"`, and automatically schedules background text extraction. |
| `/api/v1/documents/{id}/status` | `GET` | `200 OK` | `CANDIDATE` (owner), `EMPLOYER_ADMIN`, `REVIEWER`, `SYSTEM_AUDITOR` | Polls document processing status, page count, and verbatim page-by-page extracted text (`extracted_text_by_page`). |
| `/api/v1/documents/{id}/retry` | `POST` | `202 Accepted` | `CANDIDATE` (owner), `EMPLOYER_ADMIN`, `REVIEWER` | Resets a failed document's status to `queued` and re-triggers background text extraction without requiring re-upload. |
| `/api/v1/documents/{id}/extract` | `POST` | `202 Accepted` | `CANDIDATE` (owner), `EMPLOYER_ADMIN`, `REVIEWER` | Triggers downstream AI structured evidence extraction (parsing skills & claim evidence). Rejects with `409 Conflict` if PDF text extraction is still queued/processing. |
| `/api/v1/documents/{id}/extraction-results` | `GET` | `200 OK` | `CANDIDATE` (owner), `EMPLOYER_ADMIN`, `REVIEWER`, `SYSTEM_AUDITOR` | Retrieves the latest structured AI evidence extraction run, including candidate skills and evidence items. |

> **Critical Architecture Note**: The backend has **no** `GET /api/v1/documents` list endpoint. Standalone documents uploaded by a candidate cannot be enumerated by the frontend until linked to an application record (`POST /api/v1/applications`).

---

## 2. Exact Request & Response Contracts

### 2.1 Upload Resume (`POST /api/v1/documents`)

- **Headers**:
  - `Authorization: Bearer <access_token>`
  - `Accept: application/json`
  - (Note: `Content-Type` is omitted in the API client call; the browser automatically supplies `multipart/form-data; boundary=...`)
- **Body**: `FormData` with field:
  - `file`: `UploadFile` (binary PDF content, filename)
- **Response Schema** (`DocumentUploadResponse`):
  ```json
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "alex_morgan_resume.pdf",
    "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "file_size_bytes": 1048576,
    "processing_status": "queued",
    "created_at": "2026-11-01T02:00:00.000000"
  }
  ```

---

### 2.2 Poll Document Status (`GET /api/v1/documents/{id}/status`)

- **Headers**: `Authorization: Bearer <access_token>`
- **Response Schema** (`DocumentStatusResponse`):
  ```json
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "alex_morgan_resume.pdf",
    "processing_status": "completed",
    "page_count": 2,
    "extracted_text_by_page": {
      "1": "Alex Morgan — Senior Cloud Platform Engineer\nOver 8 years experience building distributed microservices...",
      "2": "Education & Certifications\nB.S. in Computer Science\nAWS Certified Solutions Architect..."
    },
    "processing_error": null,
    "created_at": "2026-11-01T02:00:00.000000",
    "updated_at": "2026-11-01T02:00:01.500000"
  }
  ```

If processing failed, `processing_status` is `"failed"` and `processing_error` contains:
```json
{
  "code": "OCR_REQUIRED",
  "message": "Document contains no extractable digital text. It appears to be a scanned image and OCR is required.",
  "details": {
    "scanned_pages": 1,
    "ocr_required": true
  }
}
```

---

### 2.3 Retry Processing (`POST /api/v1/documents/{id}/retry`)

- **Headers**: `Authorization: Bearer <access_token>`
- **Response Schema** (`DocumentStatusResponse`):
  Returns updated `DocumentStatusResponse` with `processing_status: "queued"`, `processing_error: null`.

---

## 3. File Validation Rules

The backend strictly enforces the following validation checks in `validate_uploaded_pdf()` (`backend/app/utils/document.py:58-76`):

1. **File Extension**: Must end with `.pdf` (case-insensitive: `filename.lower().endswith(".pdf")`). Non-PDF files are rejected with `HTTP 422: Only PDF documents are supported (.pdf)`.
2. **File Size**: Maximum allowed file size is **15 MB** (`MAX_UPLOAD_SIZE_MB = 15`, `15 * 1024 * 1024 = 15,728,640 bytes`). Files exceeding 15 MB are rejected with `HTTP 422: File size exceeds maximum allowed limit of 15 MB`.
3. **Empty File**: Content length must be greater than 0 bytes. Empty files are rejected with `HTTP 422: Uploaded file is empty`.
4. **Magic Bytes**: Content must start with `%PDF-` signature bytes. Files with spoofed `.pdf` extensions are rejected with `HTTP 422: Uploaded file does not match valid PDF file format signature`.
5. **Page Limit**: Maximum pages processed is **30** (`MAX_PDF_PAGES = 30`). Files exceeding 30 pages fail background processing with `PAGE_LIMIT_EXCEEDED`.
6. **Encrypted / Password Protected**: Password-protected PDFs fail background processing with `PASSWORD_PROTECTED`.
7. **Scanned / Image-Only**: PDFs with 0 extractable digital characters fail background processing with `OCR_REQUIRED`.

The frontend `CandidateJobDetailPage.tsx` validates extension, MIME type, 15 MB size limit, and empty files before initiating network requests.

---

## 4. Upload & Background Extraction Lifecycle

```
[Candidate selects/drops PDF]
       │
       ▼ Client Validation (<=15MB, .pdf, non-empty)
[POST /api/v1/documents] ──(202 Accepted)──> Backend persists Document(status='queued')
       │                                            │
       │                                            ▼
       │                               [FastAPI BackgroundTasks: process_document_extraction]
       │                                            │
       │                                            ├── Lock concurrency check
       │                                            ├── status = 'processing'
       │                                            ├── extract_text_by_page()
       │                                            └── status = 'completed' | 'failed'
       ▼
[Frontend Polling Loop: GET /api/v1/documents/{id}/status]
       │
       ├── Status == 'queued' | 'processing' ──> Continue polling (1500ms interval, max 30 attempts)
       ├── Status == 'completed' ──> Stop polling, render Extracted Text Viewer grouped by page
       └── Status == 'failed' ──> Stop polling, render structured error with 'Retry Extraction' button
```

---

## 5. Polling Strategy & Safety Guards

1. **Interval**: Fixed interval of **1,500 ms** between status checks.
2. **Timeout Safety Cap**: Maximum **30 poll attempts** (45 seconds total duration). If a background worker hangs, polling automatically stops and offers a retry.
3. **Terminal State Detection**: Polling terminates immediately when `status === "completed"` or `status === "failed"`.
4. **Component Lifecycle Cleanup**: When navigating away from `/candidate/jobs/:jobId` or unmounting the component, the interval timer (`pollIntervalRef.current`) is cleared immediately.
5. **Duplicate Polling Prevention**: Single active interval ref; starting a new poll cancels any existing active timer.
6. **Error & Session Invalidation**: Network failures or `401 Unauthorized` responses clear the timer and trigger session refresh.

---

## 6. Extraction Results Viewer Specification

When extraction completes, `CandidateJobDetailPage.tsx` renders the **Extracted Resume Content** viewer:

1. **Metadata Summary Cards**:
   - `Filename`: Original file name returned by server.
   - `Total Pages`: `page_count` returned by backend.
   - `Extracted Characters`: Sum of verbatim extracted characters across all pages.
   - `Lifecycle Status`: `COMPLETED`.
2. **Clear Transparency Notice**:
   Explicitly notes: *"This viewer displays raw textual excerpts extracted directly from your PDF document by page. Candidate qualification evaluation, evidence grounding, and criteria matching will occur upon application submission."*
3. **Original Page Boundary Tabs**:
   Horizontal tabs labeled `Page 1`, `Page 2`, `Page 3`, etc., matching the exact string keys of `extracted_text_by_page`.
4. **Verbatim Text Formatting**:
   Rendered in a scrollable container (`max-h-[360px] overflow-y-auto font-mono text-xs text-ink/90 whitespace-pre-wrap select-text`), preventing page blowouts while preserving original indentation and formatting.
5. **Upload Replacement**:
   Candidates can click "Upload Different Resume" to clear current state and select another document.

---

## 7. Ownership, Security & Tenant Isolation

- **Document Ownership**: The backend assigns `doc.candidate_id = current_user.id` upon upload.
- **Cross-Candidate Isolation**:
  In `verify_document_access()` (`backend/app/api/v1/endpoints/documents.py:30-82`):
  ```python
  if current_user.role == UserRole.CANDIDATE:
      if doc.candidate_id != uuid.UUID(current_user.id):
          raise AuthorizationError("You are not authorized to access this document")
  ```
  If Candidate A attempts to poll `GET /api/v1/documents/{id_of_candidate_b}/status`, the backend immediately raises `AuthorizationError` (`HTTP 403 Forbidden`).
- **No Client-Side Candidate ID Injection**: The frontend never transmits or accepts an arbitrary candidate ID. All ownership is derived from the JWT session subject.
- **No Local Storage Leakage**: Resume text is never persisted in `localStorage`. Storage paths on the server are never exposed.

---

## 8. Known Backend Limitations & Orphan-Document Handling

1. **No Standalone Document Listing Endpoint**:
   The backend lacks `GET /api/v1/documents`. If a candidate uploads a document but refreshes the browser before submitting an application, there is no endpoint to list previously uploaded standalone documents.
   *Resolution*: The frontend maintains an honest "No Resume on File" state on the dashboard until an application is created (Feature 3B).
2. **Orphan Documents**:
   Documents uploaded without creating an application remain in `storage/` and the database with `candidate_id` set, but are not attached to an application. Feature 3B will connect the uploaded document ID to `POST /api/v1/applications`.

---

## 9. Automated Verification Suite & Test Results

The integration was verified by running an automated end-to-end test suite (`scratch/test_document_integration.py`) using `backend/.venv/bin/python3` against an in-memory SQLite database and ASGI test client:

| Test Scenario | Description | Backend Response | Verdict |
|---|---|---|---|
| **Test A: Valid Upload** | Upload authentic sample PDF with Python experience text. | `HTTP 202 Accepted`, real document UUID, `processing_status="queued"`. | **PASS** |
| **Test B: Extraction & Polling** | Poll `GET /api/v1/documents/{id}/status` until terminal state. | Transitions to `processing_status="completed"`, `page_count=1`, `extracted_text_by_page={"1": "..."}`. | **PASS** |
| **Test C1: Non-PDF File** | Upload file with `.txt` extension. | Rejected with `HTTP 422 Unprocessable Entity`: `"Only PDF documents are supported (.pdf)"`. | **PASS** |
| **Test C2: Empty File** | Upload 0-byte file. | Rejected with `HTTP 422 Unprocessable Entity`: `"Uploaded file is empty"`. | **PASS** |
| **Test C3: File Exceeding 15 MB** | Upload 16 MB mock PDF buffer. | Rejected with `HTTP 422 Unprocessable Entity`: `"File size exceeds maximum allowed limit of 15 MB"`. | **PASS** |
| **Test C4: Spoofed Magic Bytes** | Upload `.pdf` file without `%PDF-` header. | Rejected with `HTTP 422 Unprocessable Entity`: `"Uploaded file does not match valid PDF file format signature"`. | **PASS** |
| **Test D1: Unauthorized Upload** | Upload attempt without JWT Authorization header. | Rejected with `HTTP 401 Unauthorized`. | **PASS** |
| **Test D2: Cross-Candidate Access** | Candidate B attempts to poll Candidate A's document status. | Rejected with `HTTP 403 Forbidden`: `"You are not authorized to access this document"`. | **PASS** |
| **Test E: Retry Processing** | Request `POST /api/v1/documents/{id}/retry` on document. | Returns `HTTP 202 Accepted` with `processing_status="queued"` and schedules re-extraction. | **PASS** |

---

## 10. Final Verification Results (Feature 3A)

- **TypeScript Compilation**: `npx tsc --noEmit` passed with 0 errors.
- **Production Build**: `npm run build` succeeded cleanly in 2.32s with 0 warnings.
- **Design System Fidelity**: Full adherence to charcoal and mint styling, Manrope typography, crisp badge indicators, zero mock data.

---

## 11. Feature 3B: Candidate Application Submission & Document Linking

**Integration Date**: November 1, 2026  
**Scope**: Linking verified PDF resume to open job requisition, duplicate application prevention, application detail dossier, and candidate dashboard metrics reflection.  
**Frontend Implementation**: `src/pages/candidate/CandidateJobDetailPage.tsx`, `src/pages/candidate/CandidateApplicationDetailPage.tsx`, `src/pages/candidate/CandidateDashboardPage.tsx`, `src/services/api/applicationService.ts`.

### 11.1 Real Backend Application Endpoints

| Endpoint | HTTP Method | Expected Status | Authorized Roles | Description |
|---|---|---|---|---|
| `/api/v1/applications` | `POST` | `201 Created` | `CANDIDATE` | Creates a new application linking `job_id` and `primary_document_id`. Validates ownership, job existence, and enforces duplicate prevention (`409 Conflict`). |
| `/api/v1/applications` | `GET` | `200 OK` | `CANDIDATE`, `EMPLOYER_ADMIN`, `REVIEWER`, `SYSTEM_AUDITOR` | Lists applications. For `CANDIDATE`, returns only applications owned by `current_user.id`. Can be filtered by `?job_id=<uuid>`. |
| `/api/v1/applications/{id}` | `GET` | `200 OK` | `CANDIDATE` (owner), `EMPLOYER_ADMIN`, `REVIEWER`, `SYSTEM_AUDITOR` | Retrieves single application details. Returns `403 Forbidden` if another candidate attempts access. |

### 11.2 Request & Response Contracts

#### Application Submission (`POST /api/v1/applications`)

- **Headers**:
  - `Authorization: Bearer <access_token>`
  - `Content-Type: application/json`
- **Request Body** (`ApplicationCreateRequest`):
  ```json
  {
    "job_id": "89b7245b-7c70-4d43-8f0a-31b017b62a67",
    "primary_document_id": "550e8400-e29b-41d4-a716-446655440000"
  }
  ```
- **Response Schema** (`ApplicationResponse` — `201 Created`):
  ```json
  {
    "id": "c1f7a4b2-3e5f-4a7b-9c8d-1e2f3a4b5c6d",
    "job_id": "89b7245b-7c70-4d43-8f0a-31b017b62a67",
    "candidate_id": "a9e634bc-0428-4032-9cb4-5690bfaee3a8",
    "primary_document_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "submitted",
    "submitted_at": "2026-11-01T02:15:00.000000",
    "created_at": "2026-11-01T02:15:00.000000"
  }
  ```

### 11.3 Pre-Submission Gating & Client Validation

In `CandidateJobDetailPage.tsx`, submission is strictly gated by the following rules:

1. **Extraction Completion Gating**: The user cannot submit an application while document extraction is idle, uploading, processing, or failed (`uploadState !== 'completed'`).
2. **Document Presence**: A valid `documentId` returned from `POST /api/v1/documents` must be loaded.
3. **Candidate Declaration Confirmation**: The candidate must actively check the confirmation checkbox declaring that the uploaded resume accurately reflects their credentials.
4. **Loading States**: During submission (`isSubmittingApp === true`), the submit button is disabled and renders an inline spinner to prevent double submissions.

### 11.4 Duplicate Submission Prevention

1. **Initial Mount Guard**: When the candidate loads `/candidate/jobs/:jobId`, the page immediately invokes `applicationService.listApplications({ job_id: jobId })`.
2. **Submitted Application Banner**: If an existing application is returned, the upload dropzone and submit form are replaced with an **"Application Already Submitted"** banner displaying the submission date, current status badge, and an **"Inspect Application Dossier"** button routing to `/candidate/applications/:id`.
3. **Backend `409 Conflict` Catch**: If a concurrent duplicate submission attempt occurs, the backend database `UniqueConstraint("job_id", "candidate_id")` raises `ConflictError` (`409 Conflict`), which the frontend catches and renders as an inline alert: *"An application for this requisition has already been submitted by your account."*

### 11.5 Honest Evaluation Decoupling

Per backend architecture, `POST /api/v1/applications` does **not** automatically execute qualification evaluations. Evaluations are triggered downstream via `POST /api/v1/evaluations`.
Accordingly:
- `CandidateApplicationDetailPage.tsx` handles newly submitted applications with `evaluation === null` by rendering an honest **"Evidence Extraction In Progress"** notice.
- No synthetic evaluation percentages or fabricated citations are displayed.
- The linked document's genuine filename, page count, and document ID are loaded via `documentService.getDocumentStatus(application.primary_document_id)`.

### 11.6 Tenant Isolation & Document Ownership Integrity

- **Cross-Candidate Document Injection Prevention**: The backend verifies `doc.candidate_id == current_user.id`. If Candidate B attempts to submit an application using Candidate A's `document_id`, the backend rejects the request with `HTTP 403 Forbidden: You do not own this document`.
- **Cross-Candidate Application Privacy**: If Candidate B attempts `GET /api/v1/applications/{application_of_candidate_a}`, the backend enforces `app.candidate_id == current_user.id` and rejects with `HTTP 403 Forbidden: You are not authorized to view this application`.

### 11.7 Resume Persistence Across Refreshes (Browser Recovery Engine)

Because the backend does not expose a standalone document listing endpoint (`GET /api/v1/documents`), uploaded resumes awaiting submission exist as unlinked documents on the server. The frontend implements a secure, durable browser-refresh recovery engine:

1. **Storage Utility (`pendingDocumentStore.ts`)**:
   - Versioned storage key: `clearhire_pending_documents_v1`.
   - Keyed strictly by composite candidate and job identifiers: `${candidateId}:${jobId}`.
   - **Zero Privacy Leakage**: Stores **only** minimal reference metadata (`documentId`, `candidateId`, `jobId`, `fileName`, `savedAt`). **Never stores PDF binary data, extracted text, JWT tokens, or sensitive resume contents.**
   - Automatic 7-day TTL expiration pruning.
2. **Page Load Restoration Lifecycle**:
   - On mount of `/candidate/jobs/:jobId`, checks if an application is already submitted. If so, removes any pending reference.
   - If not applied, checks `pendingDocumentStore.getPendingDocument(user.id, jobId)`.
   - If a reference exists, queries the authentic backend endpoint: `GET /api/v1/documents/{id}/status`.
   - If `completed`: renders extracted text viewer freshly from backend response.
   - If `processing` or `queued`: resumes live status polling.
   - If `failed`: renders backend error and retry options.
   - If backend returns `404 Not Found` or `403 Forbidden`: immediately discards the stale reference and renders a clean upload state with an informative notice.
3. **Submission Cleanup**:
   - Only after `applicationService.submitApplication(jobId, documentId)` returns `201 Created` does the frontend remove the pending document reference from browser storage.


