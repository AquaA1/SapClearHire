# ClearHire — Complete Development Data Reset Report

## 1. Environment & Target Database Verification

- **Environment Setting**: `ENVIRONMENT=development` in `backend/.env`.
- **Database Engine**: SQLite (Async via `sqlite+aiosqlite`).
- **Target Database Path**: `/home/vanilla/Desktop/hackathon/sap/backend/clearhire_dev.db`.
- **Process Verification**: Active running process `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` (PID 54864) operating in `/home/vanilla/Desktop/hackathon/sap/backend`.
- **Safety Classification**: Positively confirmed as a single-node local development database. Not a production or shared database.

---

## 2. Backup Location & Integrity

Prior to executing any modifications, an offline, page-by-page database backup was generated via SQLite backup protocol and verified:

- **Backup File**: `/home/vanilla/Desktop/hackathon/sap/backend/backups/clearhire_dev_backup_20261101_183155.db`
- **Backup Size**: 892,928 bytes
- **Integrity Check**: 100% identical table counts and schemas matching pre-cleanup state.

---

## 3. Original Database & User Counts

### User Account Counts (100% Preserved)
- **Total User Accounts**: **59**
  - **Candidates**: 39
  - **Employer Admins**: 20
- **Alembic Schema Version**: 1 (intact)

### Original Recruitment Record Counts (Pre-Cleanup)
- `jobs`: 20
- `job_criteria`: 57
- `applications`: 36
- `documents`: 47
- `extraction_runs`: 24
- `candidate_skills`: 99
- `evidence_items`: 143
- `evaluations`: 16
- `criterion_evidence`: 54
- `review_flags`: 4
- `review_decisions`: 6
- `correction_requests`: 1
- `audit_events`: 117 (72 recruitment/application-tied, 45 user/security-tied)

---

## 4. Deletions Executed by Category

All deletions were performed in an atomic SQLite transaction with foreign key enforcement (`PRAGMA foreign_keys = ON;`) in strict leaf-to-root order:

| Category | Table | Records Deleted | Order / Dependency Rationale |
|---|---|:---:|---|
| **Human Review** | `review_decisions` | 6 | Child of applications & criterion evidence |
| **Human Review** | `review_flags` | 4 | Child of applications & criterion evidence |
| **Clarifications** | `correction_requests` | 1 | Child of applications & criterion evidence |
| **AI Evidence** | `criterion_evidence` | 54 | Child of evaluations & job criteria |
| **Evaluations** | `evaluations` | 16 | Child of applications & extraction runs |
| **Applications** | `applications` | 36 | Child of jobs & documents |
| **Job Criteria** | `job_criteria` | 57 | Child of jobs |
| **Jobs** | `jobs` | 20 | Recruitment requisitions |
| **Extracted Skills**| `candidate_skills` | 99 | Child of extraction runs |
| **Evidence Items** | `evidence_items` | 143 | Child of documents & extraction runs |
| **Extractions** | `extraction_runs` | 24 | Child of documents |
| **Documents** | `documents` | 47 | Uploaded resume document metadata |
| **Audit Events** | `audit_events` | 72 | Recruitment, document, and review events |
| **TOTAL** | — | **579** | **All recruitment test records removed** |

---

## 5. Storage Files Deleted

- **Document Storage Directory**: `/home/vanilla/Desktop/hackathon/sap/backend/storage/documents/`
- **PDF Resume Files Deleted**: **798** files (`find ... -type f -name "*.pdf" -delete`).
- **Files Preserved**: `storage/.gitkeep`, configuration files, environment files, source code, and database backups.
- **Orphaned Resume Files Remaining**: **0**.

---

## 6. User Accounts Preserved

Every user account in ClearHire has been preserved with zero modifications to user IDs, email addresses, roles, full names, organization identifiers, or argon2id password hashes:

- **Key Administrative Accounts**:
  - `admin@gmail.com` (`ba5704f0-44aa-463f-aab5-c3e9199873f7`, Employer Admin, `clearhire-demo`)
  - `employer.admin@clearhire.dev` (`ca5cb765-82de-429d-ae17-152c9e7fc142`, Employer Admin, `tenant-apex`)
  - `emp1_5c8432@orga.com` (`5c8432f1-82dc-4e39-a888-f9e7e6d22b81`, Employer Admin)
  - `emp2_51cb91@orgb.com` (`51cb91ef-4daa-4750-a5cd-cdcb48af79b9`, Employer Admin)
- **Key Candidate Accounts**:
  - `try@gmail.com` (`6f5a0394-cd41-4f83-a6a5-16345b5703d3`, Candidate)
  - `anish@gmail.com` (`02a10f94-345f-4ded-8490-608e913c394b`, Candidate)
  - `riya@gmail.com` (Candidate)
  - `alex.morgan@test.com` (`06e86919-7a3e-4313-a898-fdec9cc0a02e`, Candidate)
  - `cand_a_160da3@example.com` (Candidate)
  - `cand_b_e7ea43@example.com` (Candidate)
- **Total Preserved Users**: **59** accounts.

---

## 7. Final Database Counts

Verified directly against `/home/vanilla/Desktop/hackathon/sap/backend/clearhire_dev.db`:

| Table Name | Final Record Count | Status |
|---|:---:|---|
| `users` | **59** | Preserved (39 Candidates, 20 Employer Admins) |
| `alembic_version` | **1** | Preserved (Schema migrations intact) |
| `audit_events` | **49** | Preserved (45 original user login/registration security events re-chained + 4 post-cleanup verification login events) |
| `jobs` | **0** | Clean |
| `job_criteria` | **0** | Clean |
| `applications` | **0** | Clean |
| `documents` | **0** | Clean |
| `extraction_runs` | **0** | Clean |
| `candidate_skills` | **0** | Clean |
| `evidence_items` | **0** | Clean |
| `evaluations` | **0** | Clean |
| `criterion_evidence` | **0** | Clean |
| `review_flags` | **0** | Clean |
| `review_decisions` | **0** | Clean |
| `correction_requests`| **0** | Clean |

---

## 8. Authentication & Cryptographic Verification

1. **Candidate Login**:
   - `alex.morgan@test.com` logged in successfully via `/api/v1/auth/login` (HTTP 200).
   - Valid JWT access token generated.
   - `/api/v1/auth/me` retrieved user profile matching candidate ID `06e86919-7a3e-4313-a898-fdec9cc0a02e`.
2. **Employer Admin Login**:
   - `employer.admin@clearhire.dev` logged in successfully via `/api/v1/auth/login` (HTTP 200).
   - Valid JWT access token generated.
   - `/api/v1/auth/me` retrieved employer admin profile matching ID `ca5cb765-82de-429d-ae17-152c9e7fc142`.
3. **Empty Queue & Requisition Verification**:
   - `GET /api/v1/jobs` returned `[]` (count: 0).
   - `GET /api/v1/review-flags` returned `[]` (count: 0).
   - `GET /api/v1/applications` returned `[]` (count: 0).
4. **Audit Cryptographic Hash Chain Integrity**:
   - Executed `AuditVerificationService.verify_chain(db)`.
   - Result: `is_valid=True`, `discrepancy_type=None`, `error=None`.
   - Monotonic sequence numbers and SHA-256 hashes verified continuously from `GENESIS_PREVIOUS_HASH`.

---

## 9. Isolated Test Results

1. **Backend Pytest Suite**:
   - Ran against isolated in-memory test database:
     ```
     ============================= 192 passed in 52.43s =============================
     ```
   - Confirmed `clearhire_dev.db` was untouched by test execution.
   - Confirmed `storage/documents` remained empty (0 files).
2. **Frontend Type Check & Production Build**:
   - `npx tsc --noEmit` exited with 0 errors.
   - `npm run build` completed in 2.24s.

---

## 10. Records Intentionally Retained

1. **`users` (59 records)**: Preserved to allow all developers, candidates, and employer administrators to authenticate without requiring account recreation.
2. **`alembic_version` (1 record)**: Preserved to ensure database schema and migration tracking remain fully synchronized.
3. **`audit_events` (user security events)**: Retained account-level audit events (`USER_LOGGED_IN`, `USER_REGISTERED`, `ADMIN_BOOTSTRAPPED`) and re-computed their cryptographic chain to preserve non-repudiation and security history without referencing deleted applications or resumes.
