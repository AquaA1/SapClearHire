# ClearHire — Review Resolution, Unresolved Counts & Triage Synchronization Report

## Executive Summary

This report documents the architectural fixes and end-to-end synchronization implemented across ClearHire to resolve inconsistencies between reviewer decisions, unresolved counts, triage queue statuses, and candidate-facing verifications.

Prior to these fixes, when an authorized reviewer or employer admin accepted or rejected an evaluation criterion:
1. Associated review flags frequently remained stuck in `PENDING` status.
2. The triage queue count did not decrement consistently.
3. Resolved criteria lingered in the "Needs Review / Pending Action" tab.
4. Calling screening evaluation or re-flagging would re-open already adjudicated criteria.
5. Clarification requests prematurely decremented the pending count even though the case was still unresolved.

Following the implementation, the backend is established as the authoritative single source of truth, tenant isolation is maintained, auto-reconciliation is applied to legacy and edge-case flags without data loss, and real-time state synchronization is enforced across both employer and reviewer interfaces.

---

## Root Cause Analysis

### 1. Disconnect Between Criterion Decisions and Multi-Flag Records
- **Mechanism**: An evaluation criterion evidence record (`CriterionEvidence`) could be associated with one or more `ReviewFlag` entities (e.g. raised individually or generated via automated batches).
- **Failure Mode**: When `record_reviewer_decision` or `update_criteria_verification` recorded an accept or reject decision, only the specific flag ID or the first flag (`ce.review_flags[0]`) was transitioned to `RESOLVED`. Any duplicate or sibling flags linked to the same criterion evidence remained in `PENDING` or `UNDER_REVIEW`, causing the triage queue to continue showing the case as pending.

### 2. Blind Re-Flagging in `create_review_flags`
- **Mechanism**: The automated review flagging service inspected only `ce.ai_status in (AMBIGUOUS, NOT_FOUND)`.
- **Failure Mode**: It failed to check `ce.verification_state`. When an employer ran screening or re-evaluation on an application where criteria had already been human-verified or human-rejected, `create_review_flags` created brand-new `PENDING` flags for already adjudicated criteria.

### 3. Misclassification of Clarification Requests
- **Mechanism**: The triage queue's pending count was calculated in the frontend simply as `flags.filter(f => f.status === 'pending').length`.
- **Failure Mode**: When a reviewer requested clarification (`REQUESTED_CLARIFICATION`), the flag status changed to `UNDER_REVIEW`. The client-side count dropped by 1, misleading the reviewer into thinking the item was resolved when in fact the case was awaiting candidate clarification and was still unresolved.

### 4. Client-Side Block on Employer Admin Queue Access
- **Mechanism**: In `reviewService.ts`, `listReviewFlags` previously contained an artificial check:
  ```ts
  if (role === UserRole.EMPLOYER_ADMIN && !applicationId) {
    return [];
  }
  ```
- **Failure Mode**: Employer admins attempting to view their triage queue were blocked on the client side unless the frontend issued $N$ separate network requests for every application in their organization.

---

## Architectural Changes & Implementation Details

### 1. Backend Service & Repository Enhancements

#### `backend/app/repositories/domain.py`
- **Scoping to Employer Requisitions**: Enhanced `ReviewFlagRepository.get_assigned_flags` with `employer_id` and `org_employer_id` filtering. It joins `applications` and `jobs`, filtering by `jobs.employer_id` to enforce strict organization-level multi-tenant isolation.
- **Support for Multi-Status Queries**: Added `status_list: list[ReviewFlagStatus] | None = None` to query multiple statuses simultaneously (e.g., retrieving both `PENDING` and `UNDER_REVIEW` flags in a single SQL query).
- **Bulk Criterion Flag Resolution**: Implemented `update_status_for_criterion_evidence(criterion_evidence_id, status, resolved_at)` to atomically transition all flags tied to a criterion evidence to `RESOLVED` with an authoritative timestamp.

#### `backend/app/services/review.py`
- **Prevention of Re-Flagging**: In `create_review_flags`, added guards preventing creation of new flags if:
  1. `ce.verification_state in (VerificationState.HUMAN_VERIFIED, VerificationState.HUMAN_REJECTED)`
  2. Sibling flags for the same `criterion_evidence_id` already exist with `status == ReviewFlagStatus.RESOLVED`.
- **Universal Adjudication Resolution**: In `record_reviewer_decision`, when a decision is `accepted` or `rejected`:
  - Directly marks all sibling flags for the criterion as `RESOLVED`.
  - Sets `resolved_at = datetime.now(timezone.utc)`.
  - When `decision == requested_clarification`, explicitly sets flag status to `UNDER_REVIEW` (unresolved).
- **Auto-Reconciliation Engine**: In `get_assigned_review_cases`, whenever flags are fetched for an authorized reviewer or employer admin, the service cross-checks the underlying `CriterionEvidence.verification_state`. If the criterion is already human-adjudicated but its flag remained `PENDING`, the flag is immediately reconciled to `RESOLVED` and persisted to the database.
- **Queue Deduplication**: Queues are deduplicated by `(application_id, criterion_evidence_id)` before delivery to the frontend, ensuring each criterion appears exactly once.

#### `backend/app/api/v1/endpoints/reviews.py`
- **Query Mapping**: Added `status_filter: str | None = Query(default=None, alias="status")`.
  - `status=pending`, `unresolved`, or `needs_review` maps to `[ReviewFlagStatus.PENDING, ReviewFlagStatus.UNDER_REVIEW]`.
  - `status=resolved` maps to `ReviewFlagStatus.RESOLVED`.
  - `status=under_review` maps to `ReviewFlagStatus.UNDER_REVIEW`.
  - `status=all` maps to all statuses.
- **Persistence**: Added `await db.commit()` in `list_review_cases` to permanently persist auto-reconciled flag states to the database.

#### `backend/app/schemas/review.py` & `frontend/src/contracts/models.ts`
- Added `criterion_evidence_id: uuid.UUID | None = None` to `ReviewFlagSummaryResponse` and `criterion_evidence_id?: string | null` to `ReviewFlagSummary`, providing a direct association between flags and criteria for frontend deduplication and tracking.

---

### 2. Frontend State Synchronization & UI Refinements

#### `frontend/src/services/api/reviewService.ts`
- Removed the client-side block on `EMPLOYER_ADMIN`. Both reviewer and employer queues now fetch directly from the server-filtered `/api/v1/review-flags` endpoint with complete tenant isolation.

#### `frontend/src/pages/employer/EmployerReviewQueuePage.tsx` & `ReviewerQueuePage.tsx`
- **Authoritative Unresolved Counts**:
  - `pendingCount` is calculated as `flags.filter(f => f.status === 'pending' || f.status === 'under_review').length`.
  - `resolvedCount` is calculated as `flags.filter(f => f.status === 'resolved').length`.
- **Deduplication**: Cases are deduplicated by `criterion_evidence_id` to prevent duplicate cards.
- **Tab Filtering**:
  - "Pending Action" / "Needs Review" filters for `status === 'pending' || status === 'under_review'`.
  - "Resolved" filters for `status === 'resolved'`.
  - "All Cases" retains all cases.
- **Manual & Auto Refresh**: Added "Refresh Queue" button with loading spinners, providing instantaneous re-fetch after adjudication.

#### `frontend/src/pages/reviewer/ReviewCaseDetailPage.tsx`
- **Double Submission Prevention**: The submit button is explicitly disabled while `submitting === true`.
- **Immediate State Invalidation**: Directly re-fetches the updated review case from the backend immediately following submission before navigating back to the triage queue.

#### `frontend/src/pages/employer/EmployerApplicationDetailPage.tsx`
- Updated `handleReviewDecision` to invalidate and re-fetch both the application details and the latest evaluation simultaneously upon any decision confirmation.

---

## Verification & Test Results

### 1. Integration Test Suite (`test_review_resolution_sync.py`)
A comprehensive end-to-end integration test was developed covering:
1. **Initial Queue State**: Employer posts job with required criteria -> Candidate applies -> Evaluation runs -> Ambiguous/missing criteria flagged -> Triage queue verifies authoritative initial counts (`pending = 2`, `resolved = 0`).
2. **Accept Adjudication**:
   - Reviewer records `accepted` with mandatory rationale.
   - Pending count decrements from 2 to 1.
   - Resolved count increments from 0 to 1.
   - Candidate application dossier reflects `human_verified` with the recorded rationale.
   - Subsequent execution of `create_review_flags` does NOT re-flag the criterion.
3. **Full Refresh Persistence**: Database session cache expired (`test_session.expire_all()`) and queried directly; database confirms `ReviewFlag.status == RESOLVED` and `resolved_at IS NOT NULL`.
4. **Reject Adjudication**:
   - Reviewer records `rejected` with mandatory rationale.
   - Pending count decrements from 1 to 0.
   - Resolved count increments from 1 to 2.
   - Candidate application dossier reflects `human_rejected`.
5. **Clarification Handling**:
   - Reviewer submits `requested_clarification`.
   - Flag transitions to `UNDER_REVIEW`.
   - Pending count **does not decrement** (remains unresolved).
   - Case does **not** enter the Resolved tab.
6. **Audit Trail**: Verification that `AuditEvent` records and `ReviewDecision` records are fully preserved.

**Result**:
```
tests/integration/test_review_resolution_sync.py::test_review_resolution_unresolved_counts_and_triage_synchronization PASSED [100%]
1 passed in 11.53s
```

### 2. Full Backend Test Suite
Executed the entire backend pytest suite to verify zero regressions across authentication, documents, evaluation engines, audit logging, and domain models:
```
============================= 192 passed in 57.57s =============================
```

### 3. Frontend Type Check & Production Build
Executed strict TypeScript compiler check and production Vite build:
```bash
npx tsc --noEmit && npm run build
```
**Result**:
- 0 TypeScript errors.
- Production build succeeded in 2.43s.

### 4. Dev Database Auto-Reconciliation Verification
Inspected `clearhire_dev.db`:
- Prior to auto-reconciliation, flags `bca99a17...` and `f9b84528...` were stuck in `PENDING` despite their underlying criteria being `HUMAN_VERIFIED` and `HUMAN_REJECTED`.
- Executed the triage query with `admin@gmail.com`:
  - Historical flags were automatically reconciled to `RESOLVED` with UTC timestamps.
  - Triage queue returned 1 genuinely unresolved pending case and 3 resolved cases.
  - Verified persistence in SQLite:
    ```
    ('e0f3bf3fa538428f8a389f40cb484d13', 'PENDING', None)
    ('6a8be4d98050499a95a71890c0965631', 'RESOLVED', '2026-11-01 11:24:01.160620')
    ('f9b845281eb64ea9aa87c2bd4d59f6a9', 'RESOLVED', '2026-11-01 12:45:03.945140')
    ('bca99a1782534442b8e176620d59742b', 'RESOLVED', '2026-11-01 12:45:03.941381')
    ```

---

## Conclusion & Guarantees

- **Backend Authority**: Backend is the sole arbiter of flag and criterion status.
- **Count Integrity**: Unresolved counts accurately reflect all items requiring action (`PENDING` + `UNDER_REVIEW`). Decisions decrement pending by 1 and increment resolved by 1. Clarification requests never prematurely decrement pending counts.
- **Refresh Persistence**: All state changes persist permanently across full browser reloads.
- **Zero Data Loss**: No audit events, review decisions, or historical flags were deleted or wiped.
- **Tenant Isolation**: Employers can only view and adjudicate cases for requisitions belonging to their organization.
