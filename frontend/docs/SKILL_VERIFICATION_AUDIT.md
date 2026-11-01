# Forensic Skill Verification & Decision Synchronization Audit

**Document:** ClearHire Skill Verification Lifecycle Trace & Root Cause Analysis  
**Date:** 2026-11-01  
**Scope:** Backend (`backend/app`), Frontend (`frontend/src`), Database Models, and API Contracts  
**Auditor:** ClearHire Engineering

---

## Executive Summary

ClearHire's evidence screening engine was designed to enforce deterministic source-grounded evidence verification before human reviewers accept or reject candidate qualifications. During single-account end-to-end testing with one candidate and one employer/admin account, two critical flaws were identified:

1. **Problem 1:** Every AI-extracted skill displayed as "Not Verified" (or "UNVERIFIED"), even when the candidate resume contained valid, verbatim supporting excerpts on identified pages.
2. **Problem 2:** When an authorized employer/admin or reviewer accepted a skill with a mandatory rationale, the candidate's application detail view failed to reflect the accepted decision, remaining indefinitely stuck on the initial state.

This audit provides a forensic trace of a skill from resume extraction to candidate UI rendering, identifies the precise breakdown points in the data flow, and establishes the architectural remediation plan.

---

## 1. End-to-End Trace of a Skill Claim

We traced a concrete skill claim (**Python**) from resume upload through candidate view:

```
[Candidate Resume Upload]
       │
       ▼ (OCR & Page Segmentation)
[Document.extracted_text_by_page]
       │
       ▼ (LLM Structured Claim Extraction)
[CandidateSkill] & [EvidenceItem]
       │  (Exact excerpt validated via validate_excerpt_in_text; grounding_verified = True)
       ▼
[EvidenceEvaluationService.evaluate_application]
       │  (Matches JobCriterion "Python" -> ranked_evidence -> ai_status = SUPPORTED)
       ▼
[CriterionEvidence DB Record]
       │  • ai_status = SUPPORTED
       │  • verification_state = UNVERIFIED (Default initial state)
       │  • source_excerpt = "Designed distributed Python microservices..."
       │  • source_page = 1
       │
       ├───► [Reviewer Action: POST /api/v1/reviews/{id}/decision]
       │        │
       │        ▼ (ReviewDecisionRepository.record_decision)
       │     [ReviewDecision DB Record Created]
       │        • decision = ACCEPTED
       │        • mandatory_rationale = "Verified 3 years production Python experience"
       │        • is_active = True
       │     [CriterionEvidence.verification_state UPDATED -> HUMAN_VERIFIED]
       │     [AuditEvent logged: REVIEW_DECISION_RECORDED]
       │
       ▼ (Data Retrieval by Candidate / Employer)
[GET /api/v1/evaluations/application/{app_id}]
       │
       ▼ (EvaluationService.build_evaluation_response)
[EvaluationResponse JSON Payload]
       │  ❌ BREAKDOWN 1: criterion_evidence_id is NOT included in schema
       │  ❌ BREAKDOWN 2: verification_state is NOT included in CriterionEvaluationItem schema
       │  ❌ BREAKDOWN 3: review_decisions are NOT loaded or included in the response
       │  ❌ BREAKDOWN 4: status field hardcoded to ce.ai_status ("SUPPORTED")
       │
       ▼
[Frontend: CandidateApplicationDetailPage.tsx & CriterionEvidenceCard.tsx]
       │  ❌ BREAKDOWN 5: item.verification_state is undefined
       │  ❌ BREAKDOWN 6: CriterionEvidenceCard falls back to item.status ("SUPPORTED" / "AMBIGUOUS")
       │  ❌ BREAKDOWN 7: StatusBadge displays static AI state without human review verdict
```

---

## 2. Root Cause Analysis

### Root Cause 1: Schema Incompleteness in `CriterionEvaluationItem`
In `backend/app/schemas/evaluation.py`:
```python
class CriterionEvaluationItem(BaseModel):
    criterion_id: uuid.UUID
    criterion_name: str
    category: str
    status: EvidenceStatus
    confidence: float
    plain_language_explanation: str
    source_excerpt: str | None = None
    source_page: int | None = None
    evidence_item_id: uuid.UUID | None = None
```
**Defects:**
- `criterion_evidence_id` is missing. The frontend and candidate view cannot reference the actual evidence record or submit targeted clarifications without guessing or conflating `job_criterion_id` with `criterion_evidence_id`.
- `verification_state` is missing. Even though `CriterionEvidence.verification_state` is maintained in the SQLite database, it was completely omitted from the serialization schema.
- `human_decision`, `decision_rationale`, and `decided_at` are missing. When a reviewer enters an authoritative determination with a written explanation, the evaluation response never serializes or returns this data.

### Root Cause 2: Failure to Load and Map Review Decisions in `EvaluationService.build_evaluation_response`
In `backend/app/services/evaluation.py` lines 837–849:
```python
items.append(
    CriterionEvaluationItem(
        criterion_id=ce.job_criterion_id,
        criterion_name=ce.criterion.name if ce.criterion else "Unknown",
        category=cat,
        status=ce.ai_status,
        confidence=ce.ai_confidence,
        plain_language_explanation=ce.ai_reasoning or "",
        source_excerpt=ce.source_excerpt,
        source_page=ce.source_page,
        evidence_item_id=ce.evidence_item_id,
    )
)
```
**Defects:**
- `status` only reflected `ce.ai_status` (immutable model assessment) and never considered `ce.verification_state` (authoritative human state).
- The query in `EvaluationRepository.get_latest_by_application` did not eager-load `CriterionEvidence.review_decisions`.
- There was no logic to extract the latest active `ReviewDecision`, sanitize private internal notes (e.g. stripping `[Internal Notes: ...]`), and expose the public audit rationale to the candidate.

### Root Cause 3: Asymmetry in Review Decision Endpoint Authorization & Target Resolution
In `backend/app/services/review.py`:
`record_reviewer_decision(flag_id, ...)` looked up `id` strictly in `review_flags`.
However:
- When evidence is `SUPPORTED` (e.g. Python with strong citations), ClearHire does **not** auto-create a `ReviewFlag` (flags are auto-created only for `AMBIGUOUS` or `NOT_FOUND` criteria).
- Therefore, an employer looking at a `SUPPORTED` skill on the application dossier had no review flag to submit against.
- The endpoint `POST /api/v1/reviews/{id}/decision` rejected any ID that was not a `ReviewFlag.id`.

### Root Cause 4: Missing Review Decision Controls in Employer Application Dossier
In `frontend/src/pages/employer/EmployerApplicationDetailPage.tsx`:
- The EVIDENCE tab rendered `CriterionEvidenceCard` in read-only mode without Accept/Reject/Clarify action buttons or an auditable rationale modal.
- Employers could only triage the entire application to the reviewer queue via "Triage to Reviewer", rather than recording immediate determinations on individual criteria.

### Root Cause 5: Semantic Confusion Between AI Extraction, Grounding, and Human Verification
- AI extraction is probabilistic claim detection.
- Source-grounding verification (`grounding_verified = True`) is deterministic proof that the text exists in the PDF.
- Human verification (`verification_state = 'human_verified'`) is an explicit audit sign-off by an authorized reviewer.
- When `CriterionEvidenceCard` rendered badges, if `verification_state` was missing or defaulted to `'unverified'`, it displayed `UNVERIFIED` without distinguishing between "AI Grounded Evidence Found (Awaiting Review)" vs "Unverified / Missing".

---

## 3. Forensic Status & Data Model Comparison

| Concept | Backend Model & Field | Enum Type | Expected Candidate Badge | Expected Employer Action |
|---|---|---|---|---|
| **AI Extracted (Ungrounded)** | `EvidenceItem.grounding_verified = False` | `EvidenceStatus.AMBIGUOUS` | Ambiguous / Ungrounded | Review Excerpt / Contest |
| **Evidence Supported** | `CriterionEvidence.ai_status = SUPPORTED`, `verification_state = UNVERIFIED` | `EvidenceStatus.SUPPORTED`, `VerificationState.UNVERIFIED` | Evidence Supported (Awaiting Human Review) | Accept / Reject / Request Clarification |
| **Human Verified** | `CriterionEvidence.verification_state = HUMAN_VERIFIED`, `ReviewDecision.decision = ACCEPTED` | `VerificationState.HUMAN_VERIFIED`, `ReviewDecisionType.ACCEPTED` | Human Verified (Mint Green) | View Rationale / Revise Decision |
| **Human Rejected** | `CriterionEvidence.verification_state = HUMAN_REJECTED`, `ReviewDecision.decision = REJECTED` | `VerificationState.HUMAN_REJECTED`, `ReviewDecisionType.REJECTED` | Human Review Rejected (Rose Red) | View Rationale / Revise Decision |
| **Clarification Requested** | `CriterionEvidence.verification_state = CANDIDATE_CLARIFIED` or `ReviewDecisionType.REQUESTED_CLARIFICATION` | `VerificationState.CANDIDATE_CLARIFIED`, `ReviewDecisionType.REQUESTED_CLARIFICATION` | Clarification Requested / Under Review | Submit Clarification (Candidate) / Review Statement (Employer) |

---

## 4. Remediation Plan

1. **Backend Schemas (`schemas/evaluation.py`):**
   - Extend `CriterionEvaluationItem` to include `criterion_evidence_id`, `verification_state`, `human_decision`, `decision_rationale`, and `decided_at`.
2. **Backend Services & Repositories (`evaluation.py` & `domain.py`):**
   - Eager-load `review_decisions` in `EvaluationRepository.get_latest_by_application` and `get_evaluation_with_items`.
   - Update `build_evaluation_response` to populate the new fields and strip `[Internal Notes: ...]` from `decision_rationale` for candidate security.
3. **Backend Review Endpoint (`reviews.py` & `review.py`):**
   - Enhance `record_reviewer_decision` so that `id` in `POST /api/v1/reviews/{id}/decision` can resolve either a `ReviewFlag.id` OR a `CriterionEvidence.id`.
   - If resolved via `CriterionEvidence.id`, verify employer authorization against `application.job`, auto-link any existing flag, record `ReviewDecision`, update `verification_state`, and emit `REVIEW_DECISION_RECORDED`.
4. **Frontend Contracts & Components (`models.ts`, `CriterionEvidenceCard.tsx`, `EmployerApplicationDetailPage.tsx`, `CandidateApplicationDetailPage.tsx`):**
   - Align TypeScript contracts with the updated backend schema.
   - Add inline review determination controls (Accept, Reject, Request Clarification) with mandatory 25+ character rationale modal to `EmployerApplicationDetailPage.tsx` and `CriterionEvidenceCard.tsx`.
   - Update `CandidateApplicationDetailPage.tsx` and `CriterionEvidenceCard.tsx` to render distinct badges: "Evidence Supported", "Human Verified", "Human Review Rejected", "Clarification Requested", with reviewer rationale.
   - Ensure instant state synchronization and refetching on decision submission.
5. **Single-Account Verification & Automated Test Suite:**
   - Write automated pytest tests covering the 15-step single-account lifecycle.
   - Run full backend tests and frontend typecheck/build.
