# ClearHire — AI Evidence Matching and Compound Criterion Evaluation Report

## Executive Summary

This report documents the architectural design, implementation, and verification of compound criterion evaluation, granular subcriteria evidence matching, and partial-support assessment states across the ClearHire platform.

Prior to this implementation, ClearHire's evaluation engine evaluated job requirements as monolithic strings. When a candidate possessed several constituent elements of a requirement but lacked an advanced or specialized component, the evaluation engine suffered from an all-or-nothing failure mode, marking the criterion as `NOT_FOUND`.

For instance, against candidate **Riya Sharma**'s uploaded resume—which explicitly documented Python development, PostgreSQL relational database modeling, relational table design, and complex SQL query authoring—the system previously marked:
- `Experience in FastAPI`: **NOT_FOUND**
- `PostgreSQL Scaling & Index Optimization`: **NOT_FOUND**
- `Experience in PostgreSQL`: **NOT_FOUND**

Following this implementation:
1. **Intelligent Requirement Decomposition**: Compound criteria are deterministically broken down into verifiable subrequirements (e.g., Python Programming, REST API Development, FastAPI Framework).
2. **Partial Support State (`PARTIALLY_SUPPORTED`)**: ClearHire natively distinguishes partial evidence from missing evidence across backend models, database representations, API schemas, and frontend displays.
3. **Preserved Source Citations & Grounding**: Every supported or partially supported subcriterion preserves grounded verbatim excerpts and source page numbers.
4. **Honest Absence-of-Evidence Reporting**: Unmatched requirements explicitly clarify that evidence was absent from the submitted resume, avoiding unwarranted claims of candidate inability.
5. **Multi-View Synchronization**: Candidate application views, employer review dossiers, and triage queue summaries synchronize with identical subcriteria breakdowns and coverage counts.

---

## Root Cause Analysis

### 1. Monolithic Evaluation Matching
- **Mechanism**: The legacy `_evaluate_single_criterion` matched a criterion's name directly against extracted skills and evidence using full-term synonym expansion.
- **Failure Mode**: When evaluating compound criteria like `"Experience in FastAPI"` or `"PostgreSQL Scaling & Index Optimization"`, the rule checked if the entire compound phrase or its direct synonyms matched an extracted skill. Because `"fastapi"` was not present in the resume, the criterion was classified as `NOT_FOUND` despite the candidate possessing demonstrated Python programming and RESTful API experience. Similarly, for `"PostgreSQL Scaling & Index Optimization"`, the absence of horizontal scaling or query execution plan optimization overshadowed extensive PostgreSQL table design and SQL query achievements.

### 2. Binary Status Limitations
- **Mechanism**: The platform supported only `SUPPORTED`, `NOT_FOUND`, and `AMBIGUOUS` in `EvidenceStatus`.
- **Failure Mode**: When a candidate demonstrated solid foundational qualifications (e.g., 2 out of 3 subrequirements), the evaluator had no intermediate state. Forcing a choice between `SUPPORTED` (which would falsely verify unproven skills) and `NOT_FOUND` (which discarded proven experience) compromised evaluation accuracy and reviewer trust.

### 3. Shallow Extraction of Applied Experience
- **Mechanism**: Heuristic extractors in local test/fake runners focused strictly on comma-separated skills sections and failed to extract structured project records and applied bullet points.
- **Failure Mode**: Project accomplishments like `"Student Expense Tracker (Python, PostgreSQL)"` and `"Library Inventory API (Python, REST API, SQLite)"` were not ingested as structured project evidence items with verified grounding, leaving the evaluator with only bare skill names.

---

## Architectural Changes & Implementation Details

### 1. Domain Models and Enums
- **`backend/app/db/models/enums.py`**:
  - Added `PARTIALLY_SUPPORTED = "partially_supported"` to `EvidenceStatus`.
- **`frontend/src/contracts/enums.ts`**:
  - Added `PARTIALLY_SUPPORTED = 'partially_supported'` to `EvidenceStatus`.

### 2. Evaluation Schemas & Contracts
- **`backend/app/schemas/evaluation.py`**:
  - Added `SubcriterionEvaluationItem`:
    - `id: str`
    - `name: str`
    - `status: EvidenceStatus`
    - `confidence: float`
    - `source_excerpt: str | None`
    - `source_page: int | None`
    - `explanation: str | None`
    - `citations: list[dict[str, Any]]`
    - `missing_reason: str | None`
  - Added `subcriteria: list[SubcriterionEvaluationItem]` and `missing_requirements: list[str]` to `CriterionEvaluationItem`.
  - Added `partially_supported_count: int` to `EvidenceCoverageSummary`.
- **`frontend/src/contracts/models.ts`**:
  - Added matching TypeScript interface `SubcriterionEvaluationItem`.
  - Added `subcriteria` and `missing_requirements` fields to `CriterionEvaluationItem`.
  - Added `partially_supported_count` to `EvidenceCoverageSummary`.

### 3. Deterministic Decomposition Engine (`backend/app/services/evaluation.py`)
- **`SubcriterionDefinition`**:
  - Structured definition capturing subrequirement identifier, name, required keywords, flags for framework, duration, and production environment requirements.
- **`decompose_criterion`**:
  - **Pattern 1: Production + Duration + Framework**: Decomposes criteria like `"2+ Years Production Python (FastAPI / AsyncIO)"` into Python Programming, FastAPI Framework, AsyncIO Programming, Duration, and Production Environment Experience.
  - **Pattern 2: Compound FastAPI Criteria**: Criteria such as `"Experience in FastAPI"` decompose into Python Programming, REST API Development, and FastAPI Framework. Atomic criteria (e.g., `"FastAPI"` alone) remain atomic to preserve standard skill verification contracts.
  - **Pattern 3: PostgreSQL Scaling & Optimization**: Decomposes into PostgreSQL Database, PostgreSQL Table Design, SQL Query Experience, Database Scaling, and Index Optimization.
  - **Pattern 4: Practical PostgreSQL Experience**: Decomposes into PostgreSQL Database and PostgreSQL Project Experience.
  - **Pattern 5: Conjunction / Multi-Phrase Criteria**: Decomposes criteria with explicit conjunctions (`&`, `and`, `/`, `,`) into atomic subrequirements.

### 4. Granular Subcriterion Evaluation (`evaluate_subcriterion`)
- **Strict Isolation Rules**:
  - **No Framework Over-Inference**: Knowing Python and REST API does *not* satisfy FastAPI. FastAPI requires direct implementation evidence.
  - **No Production Over-Inference**: Academic, student, or personal projects do *not* satisfy enterprise production requirements.
  - **No Duration Over-Inference**: Technology mentions without documented start/end dates or explicit years do *not* satisfy duration thresholds.
- **Rollup Assessment Status**:
  - If **all** subcriteria are `SUPPORTED` $\to$ Parent is `SUPPORTED`.
  - If **none** are found $\to$ Parent is `NOT_FOUND`.
  - If **some** are supported and some missing $\to$ Parent is `PARTIALLY_SUPPORTED`.
  - Unmatched requirements populate `missing_requirements` and `missing_reason`.
  - Grounded verbatim citations and source page numbers are collected and attached to each subcriterion.

### 5. Frontend UI & Synchronization
- **`frontend/src/components/ui/Badge.tsx`**:
  - Added amber badge styling for `PARTIALLY_SUPPORTED` (`bg-amber-100 text-amber-800 border-amber-300`).
  - Updated `NOT_FOUND` label to `"Not Found in Evidence"` for honesty and clarity.
- **`frontend/src/components/evidence/CriterionEvidenceCard.tsx`**:
  - Added support for `partially_supported` status badge.
  - Implemented collapsible subcriteria breakdown showing:
    - Supported subcriteria with green checkmarks, verbatim quotes, and page tags.
    - Missing subcriteria with amber alert icons, descriptive titles, and honest absence explanations.
  - Rendered `missing_requirements` summary tags for fast visual triage.

---

## Target Behaviors Verified

| Evaluation Criterion | Candidate Evidence (Riya Sharma) | Overall Status | Subcriteria Breakdown |
|---|---|---|---|
| **Experience in FastAPI** | Python (Student Expense Tracker, Library Inventory API)<br>REST APIs (Library Inventory API)<br>No FastAPI mentions | `PARTIALLY_SUPPORTED` | • **Python Programming**: `SUPPORTED` (p.1)<br>• **REST API Development**: `SUPPORTED` (p.1)<br>• **FastAPI Framework**: `NOT_FOUND` (Missing: FastAPI Framework) |
| **PostgreSQL Scaling & Index Optimization** | PostgreSQL (Student Expense Tracker)<br>Table design (Relational tables)<br>SQL queries (Complex queries, joins)<br>No scaling or indexing mentions | `PARTIALLY_SUPPORTED` | • **PostgreSQL Database**: `SUPPORTED` (p.1)<br>• **PostgreSQL Table Design**: `SUPPORTED` (p.1)<br>• **SQL Query Experience**: `SUPPORTED` (p.1)<br>• **Database Scaling**: `NOT_FOUND`<br>• **Index Optimization**: `NOT_FOUND` |
| **Experience in PostgreSQL** | PostgreSQL listed in technical skills & applied in Student Expense Tracker | `SUPPORTED` | • **PostgreSQL Database**: `SUPPORTED` (p.1)<br>• **PostgreSQL Project Experience**: `SUPPORTED` (p.1) |

---

## Test Verification Suite

A comprehensive 12-point integration test suite was authored in `backend/tests/integration/test_compound_criterion_evaluation.py`:

1. `test_1_riya_fastapi_decomposed_to_partially_supported`: Verifies `"Experience in FastAPI"` yields `PARTIALLY_SUPPORTED` with Python & REST API supported, and FastAPI missing.
2. `test_2_riya_postgres_scaling_decomposed_to_partially_supported`: Verifies `"PostgreSQL Scaling & Index Optimization"` yields `PARTIALLY_SUPPORTED` with PostgreSQL, Table Design, and SQL Queries supported, and Scaling/Indexing missing.
3. `test_3_riya_experience_in_postgres_marked_supported`: Verifies `"Experience in PostgreSQL"` yields `SUPPORTED` across both general knowledge and applied project subrequirements.
4. `test_4_fastapi_missing_requirement_honesty`: Asserts missing requirement specifies FastAPI Framework without claiming a lack of Python or REST capability.
5. `test_5_postgres_scaling_missing_requirements_honesty`: Asserts missing requirements list Database Scaling and Index Optimization.
6. `test_6_exact_source_citations_preserved`: Validates exact verbatim quotes, page numbers, and grounding verification across all supported subcriteria.
7. `test_7_no_false_inferencing_of_frameworks`: Ensures Python/REST API experience never marks FastAPI as supported.
8. `test_8_experience_duration_honesty`: Ensures duration thresholds are marked not found when duration is unspecified, without guessing.
9. `test_9_production_vs_academic_project_isolation`: Ensures academic and student projects are not credited as enterprise production experience.
10. `test_10_evidence_coverage_summary_partially_supported_count`: Verifies `partially_supported_count` in evidence coverage metrics.
11. `test_11_candidate_and_reviewer_view_synchronization`: Verifies that candidate-facing and reviewer-facing evaluation views receive identical subcriteria data and citations.
12. `test_12_full_pipeline_with_riya_sharma_pdf_file`: Full end-to-end integration test ingesting the actual `ClearHire_Test_Resume_Riya_Sharma.pdf` fixture file through PDF text extraction, project and skill extraction, and compound evaluation.

### Test Results
- **Targeted Integration Tests**: 16/16 PASSED
- **Full Backend Suite**: 204/204 PASSED (100% green)
- **Frontend Production Build**: `npm run build` (`tsc && vite build`) PASSED with 0 errors
