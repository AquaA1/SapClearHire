# ClearHire — Employer Resume Access: Backend & Frontend Implementation Report

**Document Version:** 1.0.0  
**Implementation Date:** 2026-11-01  
**Scope:** Authenticated backend PDF retrieval endpoint, tenant-isolated document access, frontend PDF streaming & OCR viewer, and extracted candidate profile integration in Employer Application Dossier (`/employer/applications`).  
**Status:** FULLY IMPLEMENTED & VERIFIED.

---

## 1. Summary of Changes

To resolve the limitation where employers could only see a document ID without access to the actual resume PDF or structured extracted profile, we implemented:
1. **Backend Authenticated PDF Streaming Endpoint**: `GET /api/v1/documents/{document_id}/file` with strict multi-tenant authorization (`verify_document_access`), directory traversal containment, and safe `Content-Disposition`.
2. **Frontend Binary Blob Streaming**: Extended `ApiClient` with `getBlob()` and `DocumentService` with `getDocumentFile()` to fetch authenticated binary PDF files as in-memory Blobs with automatic Bearer token injection and 401 interception.
3. **Dual-Mode Resume Viewer (`ResumePdfViewer.tsx`)**:
   - Original Rendered PDF View: Embedded iframe utilizing native browser PDF controls (page navigation, zoom, search, print).
   - "Open in New Tab" and "Download PDF" actions.
   - Extracted Text (OCR) View: Tabbed page-by-page text navigation, real-time keyword search with match counter, and copy-to-clipboard.
   - Robust error handling for 401 (expired session), 403 (unauthorized org), 404 (missing file), and extraction failures.
   - Strict ephemeral Blob URL lifecycle management (`URL.revokeObjectURL`) — zero persistence in `localStorage` or `sessionStorage`.
4. **Extracted Candidate Profile (`CandidateExtractedProfile.tsx`)**:
   - Structured presentation of work experience, education, categorized skills inventory, projects, and certifications.
   - Grounded citations for every claim with exact source page badges and verbatim quote excerpts.
   - Prominent mandatory warning banner labeling all claims as AI-extracted and unverified by human review.
   - Fallback raw page text viewer with on-demand "Run Claim Extraction" trigger if structured claims have not yet been generated.
5. **Dossier Integration (`EmployerApplicationDetailPage.tsx`)**:
   - Integrated `CandidateExtractedProfile` into the `DETAILS` tab.
   - Integrated `ResumePdfViewer` into the `RESUME` tab.
   - Preserved `EVIDENCE` and `HIRING PIPELINE` tabs.

---

## 2. Modified & Created Files

### Backend Files:
- **`backend/app/api/v1/endpoints/documents.py`** (MODIFIED):
  - Added imports: `Query`, `FileResponse`, `Path`, `LocalStorageService`.
  - Implemented `GET /api/v1/documents/{document_id}/file` with tenant authorization via `verify_document_access`.

### Frontend Files:
- **`frontend/src/contracts/models.ts`** (MODIFIED):
  - Updated `DocumentStatusResponse` with optional `file_hash`, `file_size_bytes`, `mime_type`.
  - Added `ProfileSkillItem` and `CandidateProfileSkillsResponse` interfaces.
- **`frontend/src/services/api/client.ts`** (MODIFIED):
  - Added `getBlob(path, options)` method supporting binary responses, Bearer auth, Content-Disposition filename extraction, and 401 error interception.
- **`frontend/src/services/api/documentService.ts`** (MODIFIED):
  - Added `getDocumentFile(documentId, disposition)` returning authenticated PDF `Blob`, `filename`, and `contentType`.
- **`frontend/src/services/api/profileService.ts`** (NEW):
  - Created service calling `GET /api/v1/profiles/{id}/skills`.
- **`frontend/src/components/dossier/ResumePdfViewer.tsx`** (NEW):
  - Full-featured resume component supporting PDF preview, Open in New Tab, Download, and OCR text fallback.
- **`frontend/src/components/dossier/CandidateExtractedProfile.tsx`** (NEW):
  - Structured profile component rendering extracted work experience, education, skills, projects, and certifications with page references.
- **`frontend/src/pages/employer/EmployerApplicationDetailPage.tsx`** (MODIFIED):
  - Mounted `CandidateExtractedProfile` in `DETAILS` tab and `ResumePdfViewer` in `RESUME` tab.
- **`scratch/test_employer_resume_access.py`** (NEW):
  - Automated security and integration test suite.

---

## 3. Endpoint Documentation

### `GET /api/v1/documents/{document_id}/file`

Retrieves the original uploaded PDF resume for an authorized user.

- **URL:** `/api/v1/documents/{document_id}/file`
- **Method:** `GET`
- **Authentication:** Required (`Authorization: Bearer <token>`)
- **Query Parameters:**
  - `disposition` (string, optional, default: `"inline"`):
    - `"inline"`: Sets `Content-Disposition: inline; filename="{safe_filename}"` for browser rendering.
    - `"attachment"`: Sets `Content-Disposition: attachment; filename="{safe_filename}"` for direct file download.
    - Validation: Regex pattern `^(inline|attachment)$`. Invalid values return `422 Unprocessable Entity`.
- **Response Headers:**
  - `Content-Type: application/pdf`
  - `Content-Disposition: inline; filename="{safe_filename}"` (or `attachment`)
  - `Cache-Control: private, no-cache, no-store, must-revalidate`
  - `Pragma: no-cache`
  - `Expires: 0`
- **Status Codes:**
  - `200 OK`: Binary PDF stream.
  - `401 Unauthorized`: Missing, invalid, or expired Bearer token.
  - `403 Forbidden`: User is not authorized to access this document.
  - `404 Not Found`: Document ID does not exist in database, or the physical file is missing from disk storage.
  - `422 Unprocessable Entity`: Malformed document ID or invalid disposition parameter.

---

## 4. Authorization Rules

The endpoint enforces multi-tenant boundary checks through `verify_document_access(doc, current_user, db, write_access=False)`:

1. **Candidate Access**:
   - `current_user.role == UserRole.CANDIDATE`
   - Allowed **only** if `doc.candidate_id == current_user.id`.
   - Candidate A cannot access Candidate B's documents (returns `403 Forbidden`).
2. **Employer Access**:
   - `current_user.role in (UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER)`
   - Allowed **only** if the document is linked as `primary_document_id` to an `Application` for a `Job` requisition created by the employer (`app.job.employer_id == current_user.id`) or belonging to the employer's organization (`app.job.creator.employer_id == current_user.employer_id`).
   - Cross-organization access is strictly rejected (returns `403 Forbidden`).
3. **Auditor Access**:
   - `current_user.role == UserRole.SYSTEM_AUDITOR`
   - Allowed read access for compliance verification.
4. **Path Traversal Defense**:
   - `document_id` is strictly typed as a standard `uuid.UUID`.
   - File path is resolved via `LocalStorageService.get_file_path(document_id)` and checked against `storage.documents_dir.resolve()` using `path.is_relative_to(...)`.
   - Arbitrary client paths are rejected by FastAPI routing before reaching service logic.

---

## 5. Automated Test Results

### Suite 1: Security & Integration Verification (`scratch/test_employer_resume_access.py`)
Executed against live backend via Python 3.12:

| # | Test Scenario | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| 1 | Authorized Employer (Org A) retrieves Candidate A's PDF | HTTP 200, Content-Type: `application/pdf`, `%PDF-` bytes | HTTP 200, valid PDF stream | **PASS** |
| 2 | Disposition parameter toggling (`inline` vs `attachment`) | Content-Disposition matches requested type | Correct headers verified | **PASS** |
| 3 | Cross-Tenant Employer (Org B) retrieves Candidate A's PDF | HTTP 403 Forbidden | HTTP 403 Forbidden | **PASS** |
| 4 | Candidate A retrieves Candidate B's confidential PDF | HTTP 403 Forbidden | HTTP 403 Forbidden | **PASS** |
| 5 | Candidate B retrieves Candidate B's own PDF | HTTP 200 OK | HTTP 200 OK | **PASS** |
| 6 | Non-existent document UUID retrieval | HTTP 404 Not Found | HTTP 404 Not Found | **PASS** |
| 7 | Malformed document ID (`not-a-valid-uuid`) | HTTP 422 Unprocessable Entity | HTTP 422 Unprocessable Entity | **PASS** |
| 8 | Path traversal attempt (`../../../etc/passwd/file`) | HTTP 404/422 Rejected | Blocked cleanly | **PASS** |
| 9 | Byte-for-byte SHA-256 integrity match | Received SHA-256 matches stored DB hash | Hashes match 100% | **PASS** |
| 10 | Verbatim extracted text verification | Page 1 text matches DB records | Text matches verbatim | **PASS** |
| 11 | Unauthenticated request (no Bearer token) | HTTP 401 Unauthorized | HTTP 401 Unauthorized | **PASS** |
| 12 | Invalid / expired Bearer token | HTTP 401 Unauthorized | HTTP 401 Unauthorized | **PASS** |
| 13 | Storage path concealment | Zero server filesystem paths exposed in response | No paths exposed | **PASS** |

### Suite 2: Full Backend Pytest Regression
- **Command:** `pytest -v`
- **Result:** `190 passed in 26.08s`
- **Regressions:** Zero.

### Suite 3: Frontend TypeScript Check & Production Build
- **Type Check:** `npx tsc --noEmit` -> **0 errors**
- **Production Build:** `npm run build` (`tsc && vite build`) -> **Success (built in 2.39s)**
- **Storage Persistence Audit:** Zero occurrences of `localStorage` or `sessionStorage` storing PDF bytes.

---

## 6. Remaining Limitations & Next Steps

1. **Evidence Screening Workflow**:
   - As instructed by scope boundaries, evidence screening ("Screen Evidence" button) and reviewer triage modal remain to be integrated in the subsequent milestone.
2. **Additional Document Attachments**:
   - The current implementation targets the application's `primary_document_id` (resume). If supplementary clarification documents are submitted via `correction_requests`, they can reuse `GET /api/v1/documents/{id}/file` seamlessly.
