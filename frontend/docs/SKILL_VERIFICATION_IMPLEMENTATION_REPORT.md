# ClearHire — Skill Verification & Candidate Decision Synchronization Implementation Report

## Executive Summary

This report documents the forensic investigation, architectural remediation, and automated end-to-end verification of skill verification states and candidate decision synchronization in ClearHire.

Prior to this implementation:
1. AI-extracted skills with valid source excerpts and high confidence were displayed as "Not Verified" / "UNVERIFIED" across the candidate and employer interfaces due to missing schema fields and ambiguous UI badge logic.
2. When reviewers/employers adjudicated an application or skill, decisions could not be recorded against supported criteria (since they lacked review flags), and recorded decisions never propagated to the candidate dossier view.

Both issues have been resolved. The complete verification lifecycle—from AI claim extraction with verbatim grounding to human adjudication, cryptographic audit logging, and bi-directional candidate synchronization—is now operational and covered by a 15-step end-to-end integration test suite and 191 passing backend tests.

---

## 1. Root Causes

### 1.1 Root Cause of Problem 1: Unverified AI Skills
- **Schema Decoupling**: The backend database model `CriterionEvidence` maintained two distinct status tracking fields:
  - `ai_status`: An `EvidenceStatus` enum (`SUPPORTED`, `NOT_FOUND`, `AMBIGUOUS`) indicating AI verbatim grounding.
  - `verification_state`: A `VerificationState` enum (`UNVERIFIED`, `CANDIDATE_CLARIFIED`, `HUMAN_VERIFIED`, `HUMAN_REJECTED`) indicating human review.
- However, the serialized Pydantic schema `CriterionEvaluationItem` in `backend/app/schemas/evaluation.py` previously omitted `verification_state`, `criterion_evidence_id`, `human_decision`, and `decision_rationale`.
- Consequently, the frontend `CriterionEvidenceCard.tsx` defaulted to rendering `'unverified'`, displaying "Not Verified" even when the resume excerpt provided exact verbatim grounding.

### 1.2 Root Cause of Problem 2: Decision Desynchronization
- **Strict ReviewFlag Dependency**: The reviewer decision endpoint `/api/v1/reviews/{id}/decision` previously looked up `{id}` exclusively in the `review_flags` table. But because `SUPPORTED` criteria are not automatically flagged, reviewers had no valid `{id}` to approve supported skills directly.
- **Evaluation Service Eager-Loading Gap**: `EvaluationRepository` and `EvaluationService.build_evaluation_response` did not eager-load `review_decisions` or attach the latest active `ReviewDecision` onto the evaluation response.
- **Client Unawareness**: The candidate UI had no fields to display human adjudication or reviewer explanations, and did not provide on-demand synchronization capabilities.

---

## 2. Actual Database Relationships Used

No database schema migration was necessary because the underlying SQLAlchemy models already contained all required relationships and columns:

```
+-----------------------------------------------------------------------------------+
| JobCriterion (Criteria Definitions)                                              |
|   id: UUID (PK), job_id: UUID (FK -> jobs.id), name, category, weight...          |
+-----------------------------------------------------------------------------------+
                                         │ 1
                                         │
                                         ▼ N
+-----------------------------------------------------------------------------------+
| CriterionEvidence (Application Evaluation Line Items)                             |
|   id: UUID (PK)                                                                   |
|   evaluation_id: UUID (FK -> evaluations.id)                                      |
|   job_criterion_id: UUID (FK -> job_criteria.id)                                 |
|   evidence_item_id: UUID (FK -> evidence_items.id, Nullable)                      |
|   ai_status: EvidenceStatus ('supported', 'ambiguous', 'not_found')               |
|   ai_confidence: Float                                                            |
|   verification_state: VerificationState ('unverified', 'candidate_clarified',      |
|                                         'human_verified', 'human_rejected')       |
|   source_excerpt: Text (Verbatim Grounded Citation)                              |
|   source_page: Integer (1-Indexed Page Number)                                    |
+-----------------------------------------------------------------------------------+
             │ 1                                                │ 1
             │                                                  │
             ▼ 0..N                                             ▼ 0..N
+--------------------------------------+   +----------------------------------------+
| ReviewFlag (Review Queue Items)      |   | ReviewDecision (Human Determinations)   |
|   id: UUID (PK)                      |   |   id: UUID (PK)                        |
|   application_id: UUID (FK)          |   |   application_id: UUID (FK)            |
|   criterion_evidence_id: UUID (FK)   |   |   criterion_evidence_id: UUID (FK)     |
|   status: ReviewFlagStatus           |   |   reviewer_id: UUID (FK -> users.id)   |
|   priority: String                   |   |   decision: ReviewDecisionType         |
|   reason: Text                       |   |     ('accepted', 'rejected', etc.)     |
+--------------------------------------+   |   mandatory_rationale: Text            |
                                           |   is_active: Boolean                   |
                                           |   created_at: DateTime                 |
                                           +----------------------------------------+
```

Each human adjudication creates an immutable `ReviewDecision` row and an append-only `AuditEvent` record (`action="REVIEW_DECISION_RECORDED"`), deactivates prior decisions on that evidence line, and directly updates `CriterionEvidence.verification_state`.

---

## 3. Endpoints Utilized & Enhanced

### 3.1 Reviewer Decision Recording
- **Endpoint**: `POST /api/v1/reviews/{id}/decision`
- **Controller**: `app.api.v1.endpoints.reviews.record_review_decision`
- **Service**: `app.services.review.ReviewWorkflowService.record_reviewer_decision`
- **Dual ID Resolution**: The endpoint accepts either a `ReviewFlag.id` (for flagged items in reviewer queues) OR a `CriterionEvidence.id` (for direct employer adjudication of criteria on the application dossier).
- **Mandatory Rationale Enforcement**: Requires non-empty rationale (minimum 25 characters recommended in UI).
- **Audit Logging**: Logs immutable `REVIEW_DECISION_RECORDED` event with `actor_id`, `actor_role`, `prior_state`, `new_state`, and `details`.
- **Idempotency Guard**: Re-submitting an identical determination returns the active decision without generating duplicate database records.

### 3.2 Candidate Retrieval & Synchronization
- **Endpoint**: `GET /api/v1/evaluations/application/{application_id}`
- **Controller**: `app.api.v1.endpoints.evaluations.get_evaluation_by_application`
- **Service**: `app.services.evaluation.EvaluationService.get_evaluation_by_application`
- **Sanitized Transparency**: `build_evaluation_response` eager-loads `CriterionEvidence.review_decisions`, extracts the latest active decision, and strips confidential internal notes (e.g. `[Internal Notes: ...]`) from `decision_rationale` before serialization.
- **Candidate Submission**: `POST /api/v1/applications/{id}/clarifications` allows candidates to submit clarification statements against unverified or rejected criteria, updating `verification_state` to `candidate_clarified`.

---

## 4. Files Modified

| File | Subsystem | Modifications |
| :--- | :--- | :--- |
| `backend/app/schemas/evaluation.py` | Backend Schemas | Added `criterion_evidence_id`, `verification_state`, `human_decision`, `decision_rationale`, and `decided_at` to `CriterionEvaluationItem`. |
| `backend/app/schemas/review.py` | Backend Schemas | Updated `ReviewDecisionResponse.flag_status` to optional `ReviewFlagStatus \| None = None`. |
| `backend/app/repositories/domain.py` | Backend DB | Added `selectinload(CriterionEvidence.review_decisions)` to `EvaluationRepository`; added idempotency check to `ReviewDecisionRepository.record_decision`. |
| `backend/app/services/evaluation.py` | Backend Service | Serialized human decision state, timestamps, and sanitized `public_rationale` (stripping internal notes) into `CriterionEvaluationItem`. |
| `backend/app/services/review.py` | Backend Service | Generalized `record_reviewer_decision` to support direct `CriterionEvidence.id` adjudication and generalized `submit_candidate_clarification` to support `CriterionEvidence.id`. |
| `frontend/src/contracts/models.ts` | Frontend Contracts | Added verification and human decision fields to `CriterionEvaluationItem`. |
| `frontend/src/components/ui/Badge.tsx` | Frontend UI | Added explicit badge mappings for `human_verified`, `human_rejected`, `candidate_clarified`, `evidence_supported`, and `unverified`. |
| `frontend/src/components/evidence/CriterionEvidenceCard.tsx` | Frontend UI | Added dynamic badge mapping, reviewer determination cards, review action modal with mandatory 25+ char rationale, and candidate contest flow. |
| `frontend/src/pages/employer/EmployerApplicationDetailPage.tsx` | Frontend Page | Wired `isReviewerOrEmployer={true}` and connected `handleReviewDecision` to call `reviewService.recordReviewDecision` and refetch live evaluation data. |
| `frontend/src/pages/candidate/CandidateApplicationDetailPage.tsx` | Frontend Page | Added "Sync Status" button, refined clarification contest binding to `criterion_evidence_id`, and added live refetch synchronization. |
| `backend/tests/integration/test_skill_verification_sync.py` | Automated Tests | Created 15-step end-to-end integration test verifying full verification and synchronization lifecycle. |

---

## 5. Database Migrations

**No new migration required.**
The existing SQLite database schema (`clearhire_dev.db`) already possessed all necessary columns and indices:
- `criterion_evidence.verification_state` (VARCHAR)
- `review_decisions.is_active` (BOOLEAN)
- `review_decisions.mandatory_rationale` (TEXT)
- `audit_events` append-only hash chain

All queries and mutations strictly honor foreign key constraints and transactional integrity.

---

## 6. Automated Test Results

### 6.1 Phase 6 End-to-End Synchronization Test
`backend/tests/integration/test_skill_verification_sync.py`:
```
tests/integration/test_skill_verification_sync.py::test_skill_verification_lifecycle_and_candidate_synchronization PASSED [100%]
```
Verified Steps:
1. Candidate uploads resume with Python, FastAPI, and SQL.
2. AI extracts all 3 skills into structured candidate profile.
3. Verified real source excerpt and page references (`source_page >= 1`).
4. Verified evidence validation records are persisted in `criterion_evidence`.
5. Employer opens application dossier.
6. Employer accepts Python with mandatory rationale.
7. Decision persisted against exact claim (`CriterionEvidence.id`).
8. Candidate application page refetches dossier.
9. Python displays `human_verified` (`human_decision === 'accepted'`).
10. FastAPI and SQL remain in `unverified` review state.
11. Refreshed application dossier.
12. Python verification persists reliably across requests.
13. Employer rejects SQL with rationale containing `[Internal Notes: candidate lacks distributed db experience]`.
14. Candidate sees rejection status (`human_rejected`) and sanitized explanation (internal notes stripped).
15. Verified append-only audit trail preserves both decisions in `audit_events` and `review_decisions`.

### 6.2 Full Test Suite Results
- **Backend Test Suite**:
  ```
  191 passed in 42.89s
  ```
  All 191 unit and integration tests passed with zero failures.
- **Frontend Typecheck**:
  ```
  npx tsc --noEmit: Exited with code 0 (0 errors).
  ```
- **Frontend Production Build**:
  ```
  npm run build: Built in 2.26s cleanly with code 0.
  ```

---

## 7. Manual Browser Verification Protocol

A tester using one candidate and one employer account can verify the system with the following sequence:

1. **Candidate Action**:
   - Sign in as candidate (`candidate@example.com` / `CandidatePass123!`).
   - Navigate to `/candidate/jobs` -> Apply to "Senior Cloud Backend Engineer".
   - Upload resume with Python, FastAPI, SQL.
   - Open application detail page `/candidate/applications/:id`.
   - Observe that criteria with verbatim quotes display badge **"Evidence Supported" (Awaiting Human Review)** rather than "Not Verified".
2. **Employer Action**:
   - Sign in as employer/admin (`admin@clearhire.internal` / `AdminPass123!`).
   - Navigate to `/employer/applications/:id` -> Evidence tab.
   - Under "Python", click "Accept / Verify". Enter rationale (25+ chars): `"Candidate possesses verified enterprise Python experience."`
   - Observe the card updates to green badge **"Human Verified"** and shows the recorded rationale.
3. **Candidate Verification & Sync**:
   - Switch to candidate view (or candidate browser window).
   - Click "Sync Status" button (or refresh page).
   - "Python" immediately displays green **"Human Verified"** badge with the verified rationale.
   - "FastAPI" and "SQL" remain as "Evidence Supported (Awaiting Human Review)".
4. **Employer Rejection**:
   - Employer clicks "Reject" on "SQL", entering: `"SQL profile does not meet query tuning bar. [Internal Notes: Needs distributed DB lead]"`
   - Card updates to **"Human Rejected"**.
5. **Candidate View Verification**:
   - Candidate clicks "Sync Status".
   - "SQL" displays **"Human Rejected"** with public rationale `"SQL profile does not meet query tuning bar."`
   - Confirm confidential `[Internal Notes: ...]` is not visible to the candidate.
   - Candidate clicks "Contest with clarification" to submit updated evidence.

---

## 8. Remaining Limitations & Edge Cases

1. **Auto-Polling Interval vs WebSockets**: The candidate application detail page currently relies on a "Sync Status" button and periodic polling during active pipeline runs. In a future iteration, WebSocket or Server-Sent Events (SSE) push notifications could provide instantaneous live badge transitions without user interaction.
2. **Candidate Clarification Resolution**: When a candidate submits clarification, the item transitions to `candidate_clarified`. The reviewer can then review and either accept or reject the clarified evidence.
