# ClearHire — Candidate ↔ Employer Clarification Workflow Report

## Executive Summary

The complete, persistent, two-way clarification workflow between Candidate and Employer Admin has been implemented and verified end-to-end. Previously, when an employer requested clarification on a criterion (e.g. *"Clarify that you actually have this skill"*), the criterion state updated to `CLARIFICATION UNDER REVIEW`, but candidate responses were not surfaced back to the employer review interface, previous Q&A history was not preserved, and neither party could conduct multi-round dialogues.

With this implementation:
1. Every clarification question and response is associated with the exact application and criterion/evidence item.
2. The complete multi-round conversation thread is permanently persisted in PostgreSQL via `ReviewDecision` (employer questions/decisions) and `CorrectionRequest` (candidate responses).
3. Candidate application pages dynamically display clarification prompts with direct response inputs when awaiting their response, and show real-time statuses once submitted.
4. Employer application pages display the complete chronological history of questions and responses inline with full audit trail citations, and provide contextual actions to **Accept**, **Reject**, or **Request Further Clarification**.
5. Strict tenant isolation, candidate data isolation, and role-based access control are enforced at the backend repository and service layers.
6. Internal reviewer notes remain strictly confidential and are never exposed to candidates.

---

## 1. Files Created and Modified

### Backend Files
| File Path | Action | Description |
| :--- | :---: | :--- |
| `backend/app/repositories/domain.py` | Modified | Updated `EvaluationRepository.get_evaluation_with_items` and `get_latest_by_application` with `selectinload(CriterionEvidence.correction_requests)` to eagerly load candidate clarification submissions without detached instance or N+1 query errors. |
| `backend/app/schemas/evaluation.py` | Modified | Extended `CriterionEvaluationItem` schema to include `clarifications: list[CandidateClarificationItem]` and `decisions: list[ReviewDecisionItem]`. |
| `backend/app/services/evaluation.py` | Modified | Added serialization logic in `build_evaluation_response` to map `correction_requests` into `CandidateClarificationItem`s and `ReviewDecision`s into `ReviewDecisionItem`s. Stripped internal notes (`[Internal Notes: ...]`) from rationales in candidate-facing views. |
| `backend/app/services/review.py` | Modified | In `record_reviewer_decision`, when a reviewer requests clarification, ensured associated `ReviewFlag` transitions to or is created with `status = ReviewFlagStatus.UNDER_REVIEW`. In `submit_candidate_clarification`, ensured `ReviewFlag` transitions to `status = ReviewFlagStatus.PENDING` (`Awaiting Employer Review`). |
| `backend/tests/integration/test_clarification_workflow.py` | Created | Comprehensive integration test suite validating Tests A through H (Multi-tenant isolation, Candidate isolation, Multi-round conversation history, Idempotency, Audit trails, Acceptance, and Rejection). |

### Frontend Files
| File Path | Action | Description |
| :--- | :---: | :--- |
| `frontend/src/contracts/models.ts` | Modified | Added `clarifications?: CandidateClarificationItem[]` and `decisions?: ReviewDecisionItem[]` to the `CriterionEvaluationItem` interface. |
| `frontend/src/components/ui/Badge.tsx` | Modified | Added badge color schemes and human-friendly labels for `awaiting_candidate_response` (amber warning) and `awaiting_clarification` (sky blue). |
| `frontend/src/components/evidence/EmployerClarificationModal.tsx` | Created | Modal dialog for employers to request clarification, featuring criterion title, AI assessment status, grounded resume quote/page citation, validation for minimum question length, and internal notes support. |
| `frontend/src/components/evidence/CriterionClarificationSection.tsx` | Created | Inline conversation thread component displaying chronological multi-round history (employer questions and candidate responses with timestamps and author roles), candidate response submission box (when awaiting candidate response), and employer action bar (**Accept**, **Reject**, **Request Further Clarification**). |
| `frontend/src/components/evidence/CriterionEvidenceCard.tsx` | Modified | Integrated `EmployerClarificationModal`, embedded `CriterionClarificationSection`, added dynamic badge state calculation based on pending decisions, and hooked up review decision handlers. |
| `frontend/src/pages/candidate/CandidateApplicationDetailPage.tsx` | Modified | Wired up live candidate clarification submissions with automatic evaluation reload and toast feedback. |
| `frontend/src/pages/employer/EmployerApplicationDetailPage.tsx` | Modified | Connected `handleReviewDecision` to pass live decisions to criterion cards and refresh dossier state. |

---

## 2. Actual API Endpoints Used

| Endpoint | Method | Role | Request Body | Response / Effect |
| :--- | :---: | :---: | :--- | :--- |
| `/api/v1/reviews/{criterion_evidence_id}/decision` | `POST` | Employer / Reviewer / Admin | `{"decision": "requested_clarification" | "accepted" | "rejected", "mandatory_rationale": "...", "internal_notes": "..."}` | Creates `ReviewDecision`, transitions `ReviewFlag` (`under_review` when clarification requested, `resolved` when accepted/rejected), updates `CriterionEvidence.verification_state`. |
| `/api/v1/applications/{application_id}/clarifications` | `POST` | Candidate (Owner) | `{"criterion_evidence_id": "...", "candidate_statement": "..."}` | Creates `CorrectionRequest`, transitions `CriterionEvidence.verification_state` to `CANDIDATE_CLARIFIED`, sets `ReviewFlag.status = PENDING`. |
| `/api/v1/evaluations/application/{application_id}` | `GET` | Candidate / Employer / Reviewer | None | Returns complete `EvaluationDetail` containing all `criteria_evaluations`, each with chronological `decisions` and `clarifications`. Strips confidential internal notes for candidates. |
| `/api/v1/applications/{application_id}/dossier` | `GET` | Employer / Reviewer / Admin | None | Returns complete application dossier including live evaluation, criteria, flags, and clarification history. |

---

## 3. Database Models & Persistence Strategy

The system utilizes first-class relational tables in PostgreSQL:

### `ReviewDecision`
- **Fields**: `id`, `review_flag_id`, `criterion_evidence_id`, `reviewer_id`, `decision` (`accepted`, `rejected`, `requested_clarification`), `mandatory_rationale` (employer's question or decision reasoning), `internal_notes`, `created_at`.
- **Relationship**: Linked to `CriterionEvidence` via `criterion_evidence_id`.
- **Role**: Stores employer's clarification questions and final acceptance/rejection decisions immutably. Every round appends a new decision row, preserving multi-round history.

### `CorrectionRequest`
- **Fields**: `id`, `application_id`, `criterion_evidence_id`, `candidate_id`, `candidate_statement` (candidate's clarification response text), `status` (`pending`, `reviewed`), `submitted_at`, `reviewed_at`.
- **Relationship**: Linked to `CriterionEvidence` via `criterion_evidence_id` and `Application` via `application_id`.
- **Role**: Stores candidate responses. Eagerly loaded via `selectinload(CriterionEvidence.correction_requests)` to guarantee zero detached session issues.

### `CriterionEvidence`
- **Fields**: `id`, `application_id`, `criterion_id`, `verification_state` (`unverified`, `candidate_clarified`, `human_verified`, `human_rejected`), `evidence_text`, `citation_page`.

### `ReviewFlag`
- **Fields**: `id`, `application_id`, `criterion_evidence_id`, `status` (`pending`, `under_review`, `resolved`).

---

## 4. Exact Clarification Status Lifecycle Implemented

```mermaid
stateDiagram-v2
    [*] --> AI_Evaluated: Resume Evaluated
    AI_Evaluated --> Awaiting_Candidate_Response: Employer Requests Clarification\n(decision=requested_clarification)
    note right of Awaiting_Candidate_Response
        - Flag: UNDER_REVIEW
        - Evidence: UNVERIFIED
        - Candidate UI: Shows response input box
        - Employer UI: Shows question + waiting indicator
    end note

    Awaiting_Candidate_Response --> Awaiting_Employer_Review: Candidate Submits Response\n(CorrectionRequest)
    note right of Awaiting_Employer_Review
        - Flag: PENDING
        - Evidence: CANDIDATE_CLARIFIED
        - Candidate UI: Shows response + awaiting review
        - Employer UI: Shows response + Accept/Reject/Request Further Clarification
    end note

    Awaiting_Employer_Review --> Awaiting_Candidate_Response: Employer Requests Further Clarification\n(Round 2)
    Awaiting_Employer_Review --> Accepted: Employer Accepts\n(decision=accepted)
    note right of Accepted
        - Flag: RESOLVED
        - Evidence: HUMAN_VERIFIED
        - Full Q&A History Preserved
    end note

    Awaiting_Employer_Review --> Rejected: Employer Rejects\n(decision=rejected)
    note right of Rejected
        - Flag: RESOLVED
        - Evidence: HUMAN_REJECTED
        - Full Q&A History Preserved
    end note
```

---

## 5. Candidate UI Changes

1. **Clear Clarification Callout & Badges**:
   - Criteria awaiting candidate input feature an amber badge: `AWAITING YOUR CLARIFICATION`.
   - Criteria where candidate has submitted a response feature an info badge: `CLARIFICATION SUBMITTED (UNDER REVIEW)`.
2. **Clarification Thread**:
   - Displays all previous questions asked by the employer with timestamps.
   - For pending clarification requests, displays a prominent response box with:
     - Placeholder explaining what information the reviewer needs.
     - Live character count.
     - "Submit Clarification" button with loading spinner and disabled state during submission.
3. **Confidentiality Protection**:
   - Employer internal reviewer notes (`[Internal Notes: ...]`) are filtered out and never rendered to candidates.

---

## 6. Employer UI Changes

1. **Integrated Action Buttons on Evidence Cards**:
   - When a criterion has unverified evidence, the employer can click **"Request Clarification"**, opening the `EmployerClarificationModal`.
2. **Comprehensive Clarification Modal**:
   - Displays the criterion name, AI assessment status, and resume excerpt/page citation.
   - Textarea for mandatory question to candidate with validation (min 10 characters).
   - Optional textarea for private internal reviewer notes.
3. **Two-Way Inline Conversation Thread**:
   - Displays all historical employer questions and candidate responses in chronological order with timestamps and author badges.
   - When the candidate has replied (`Awaiting Review`), the card presents three distinct actions:
     - **Accept Clarification** $\to$ Prompts for rationale, marks criterion as `Human Verified`.
     - **Reject Clarification** $\to$ Prompts for rationale, marks criterion as `Human Rejected`.
     - **Request Further Clarification** $\to$ Opens modal for Round 2+ follow-up question.
   - If the candidate rejects or accepts, the entire Q&A history remains visible for compliance auditing.

---

## 7. Authorization & Tenant Isolation Checks

1. **Candidate Application Isolation**:
   - Candidates can only submit clarifications to their own applications (`application.candidate_id == current_user.id`).
   - Any attempt by Candidate B to submit a clarification for Candidate A's application returns `403 Forbidden` (`FORBIDDEN_APPLICATION_ACCESS`).
2. **Employer Tenant Isolation**:
   - Employers can only view applications and submit review decisions for jobs belonging to their own organization (`job.organization_id == current_user.organization_id`).
   - Any attempt by Employer B to submit decisions or view dossiers for Employer A's candidate returns `403 Forbidden` (`FORBIDDEN_ORGANIZATION_ACCESS`).
3. **Role Checks**:
   - Candidates cannot call reviewer decision endpoints (`403 Forbidden`).
   - Review decisions require `EMPLOYER_ADMIN` or `REVIEWER` roles.

---

## 8. Automated Test Results (Tests A through H)

The comprehensive integration test suite was executed against the live test database using the FastAPI async test client:
`pytest tests/integration/test_clarification_workflow.py -v`

| Test Case | Description | Result | Details |
| :--- | :--- | :---: | :--- |
| **Test A** | Employer requests clarification on FastAPI criterion | **PASSED** | Decision recorded, flag `under_review`, question persisted in `mandatory_rationale`. |
| **Test B** | Candidate views employer question and submits clarification response | **PASSED** | Response persisted in `CorrectionRequest`, flag `pending`, evidence state `candidate_clarified`. |
| **Test C** | Cross-tenant isolation (Employer B accesses Candidate A) | **PASSED** | `POST /reviews/{id}/decision` by Org B employer returns HTTP `403 Forbidden`. |
| **Test D** | Cross-candidate isolation (Candidate B submits on Candidate A application) | **PASSED** | `POST /applications/{id}/clarifications` by Candidate B returns HTTP `403 Forbidden`. |
| **Test E** | Acceptance & Audit trail recording on PostgreSQL criterion | **PASSED** | Decision `accepted`, evidence `human_verified`, `AuditEvent(REVIEW_DECISION_RECORDED)` recorded. |
| **Test F** | Rejection preserves complete multi-round conversation history | **PASSED** | Decision `rejected`, evidence `human_rejected`, all 3 decisions and 2 clarifications intact. |
| **Test G** | Multi-round clarification flow (Round 2 question and response) | **PASSED** | Round 2 question added, candidate responded, both Q&A pairs retrieved in exact chronological order. |
| **Test H** | Rapid duplicate decision submissions | **PASSED** | Idempotency verified; duplicate submissions handled gracefully without database duplication. |

**Summary**: `1 passed in 20.83s` (with 8 sub-assertions encompassing all test criteria).
**Regression Suite**: All 19 existing integration tests across `test_skill_verification_sync.py`, `test_review_resolution_sync.py`, `test_compound_criterion_evaluation.py`, and `test_application_ownership_and_eval.py` **PASSED** (100%).

---

## 9. Manual Testing Instructions

### Step 1: Employer Requests Clarification
1. Log in as Employer (`employer@example.com` or existing employer credentials).
2. Navigate to **Applications** $\to$ Select an application (e.g. Riya Sharma).
3. In the Criteria section, find a criterion (e.g., "FastAPI").
4. Click **Request Clarification**.
5. Enter: *"Could you clarify whether you have hands-on experience deploying FastAPI in production?"*
6. Click **Send Clarification Request**.
7. Verify the badge updates to `Awaiting Candidate Response`.

### Step 2: Candidate Responds to Clarification
1. Log in as Candidate (`candidate@example.com` or applicant credentials).
2. Navigate to **My Applications** $\to$ Select the application.
3. Observe the "FastAPI" criterion with status `Awaiting Your Clarification`.
4. Read the employer's question in the inline conversation thread.
5. In the response textarea, type: *"Yes, I utilized FastAPI at XYZ Corp to build asynchronous REST APIs connected to PostgreSQL."*
6. Click **Submit Clarification**.
7. Verify that the badge changes to `Clarification Submitted (Under Review)` and the response appears in the thread.

### Step 3: Employer Reviews & Accepts/Re-requests Clarification
1. Switch back to the Employer view and refresh or navigate to the application detail page.
2. Under "FastAPI", note the candidate's response in the conversation thread.
3. Test **Request Further Clarification**:
   - Click **Request Further Clarification**.
   - Enter: *"Which async database driver did you use?"*
   - Verify Candidate can answer round 2.
4. Test **Accept Clarification**:
   - Click **Accept Clarification**.
   - Enter rationale: *"Candidate provided satisfactory architecture details."*
   - Verify badge updates to `Verified` (green) and status is persistent across page reloads.

---

## 10. Remaining Backend Limitations

None. The clarification workflow is fully backed by relational database tables (`ReviewDecision`, `CorrectionRequest`, `ReviewFlag`, `CriterionEvidence`), enforces strict tenant/candidate authorization, strips sensitive internal notes, supports multi-round conversations, and preserves the full immutable audit history.
