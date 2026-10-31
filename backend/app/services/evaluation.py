import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.security import CurrentUser, UserRole
from app.db.models.application import Application
from app.db.models.document import CandidateSkill, EvidenceItem
from app.db.models.enums import (
    ApplicationStatus,
    DocumentProcessingStatus,
    EvidenceStatus,
    VerificationState,
)
from app.db.models.evaluation import Evaluation
from app.db.models.job import Job, JobCriterion
from app.db.session import get_session_factory
from app.repositories.domain import EvaluationRepository, ExtractionRepository, JobRepository
from app.schemas.evaluation import (
    CriterionEvaluationItem,
    EvaluationResponse,
    EvidenceCoverageSummary,
)

# Known technology and domain synonyms
SYNONYMS: dict[str, set[str]] = {
    "postgres": {"postgresql", "postgres", "psql"},
    "postgresql": {"postgresql", "postgres", "psql"},
    "k8s": {"kubernetes", "k8s"},
    "kubernetes": {"kubernetes", "k8s"},
    "py": {"python", "py", "python3"},
    "python": {"python", "py", "python3"},
    "react": {"react", "react.js", "reactjs"},
    "react.js": {"react", "react.js", "reactjs"},
    "reactjs": {"react", "react.js", "reactjs"},
    "fastapi": {"fastapi"},
    "node": {"node", "nodejs", "node.js"},
    "nodejs": {"node", "nodejs", "node.js"},
    "node.js": {"node", "nodejs", "node.js"},
    "aws": {"aws", "amazon web services"},
    "amazon web services": {"aws", "amazon web services"},
    "gcp": {"gcp", "google cloud", "google cloud platform"},
    "google cloud": {"gcp", "google cloud", "google cloud platform"},
    "docker": {"docker", "containerization", "containers"},
    "ts": {"typescript", "ts"},
    "typescript": {"typescript", "ts"},
    "js": {"javascript", "js"},
    "javascript": {"javascript", "js"},
    "sql": {"sql", "rdbms", "relational database"},
    "nosql": {"nosql", "mongodb", "dynamodb"},
}

# Subjective or vague criteria that cannot be verified from static resume evidence alone
VAGUE_CRITERIA_KEYWORDS: set[str] = {
    "team player",
    "strong communication",
    "communication skills",
    "good communication",
    "communication",
    "work ethic",
    "fast learner",
    "quick learner",
    "hard worker",
    "detail oriented",
    "leadership qualities",
    "leadership skills",
    "problem solver",
    "problem solving",
    "self starter",
    "motivated",
    "passion",
    "passionate",
    "culture fit",
    "enthusiastic",
}

# Weak or qualifying phrases that indicate ambiguous or insufficient exposure
WEAK_EXPOSURE_KEYWORDS: set[str] = {
    "basic",
    "familiarity",
    "exposure",
    "learning",
    "student",
    "introductory",
    "beginner",
    "novice",
    "academic only",
    "elementary",
    "minimal",
}


def normalize_term(term: str) -> str:
    """Normalize a string by lowercasing and replacing non-alphanumeric chars with spaces."""
    return re.sub(r"[^a-z0-9]+", " ", term.lower()).strip()


def get_synonym_set(term: str) -> set[str]:
    """Return all synonymous terms for a given term, including the term itself."""
    norm = normalize_term(term)
    syns = {norm}
    for key, variants in SYNONYMS.items():
        if norm == key or norm in variants:
            syns.update(variants)
    return syns


def is_vague_criterion(name: str) -> bool:
    """Check if a criterion is subjective or vague."""
    norm = normalize_term(name)
    if norm in VAGUE_CRITERIA_KEYWORDS:
        return True
    return any(vague in norm for vague in VAGUE_CRITERIA_KEYWORDS)


class EvaluationService:
    """
    Deterministic evidence evaluation service.
    Evaluates candidate documents and structured evidence against versioned job criteria.
    Strictly yields exactly one status per criterion: supported, not_found, or ambiguous.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None):
        self.session_factory = session_factory or get_session_factory()

    async def evaluate_application(
        self,
        application_id: uuid.UUID,
        session: AsyncSession | None = None,
        actor_id: str | None = None,
        current_user: CurrentUser | None = None,
    ) -> Evaluation:
        """
        Evaluates an application against active job criteria.
        Creates an immutable, versioned Evaluation record with factual evidence links.
        """
        if session is not None:
            return await self._evaluate_with_session(
                session, application_id, actor_id, current_user
            )

        async with self.session_factory() as local_session:
            async with local_session.begin():
                return await self._evaluate_with_session(
                    local_session, application_id, actor_id, current_user
                )

    async def _evaluate_with_session(
        self,
        session: AsyncSession,
        application_id: uuid.UUID,
        actor_id: str | None,
        current_user: CurrentUser | None = None,
    ) -> Evaluation:
        job_repo = JobRepository(session)
        eval_repo = EvaluationRepository(session)
        extraction_repo = ExtractionRepository(session)

        # 1. Fetch application
        app_query = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.job).selectinload(Job.creator),
                selectinload(Application.primary_document),
            )
        )
        app_result = await session.execute(app_query)
        application = app_result.scalar_one_or_none()
        if not application:
            raise NotFoundError(f"Application {application_id} not found.")

        # Check tenant authorization if current_user is provided
        if current_user is not None:
            if current_user.role == UserRole.CANDIDATE:
                raise AuthorizationError("Candidates are not authorized to evaluate applications.")
            elif current_user.role in (UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER):
                if not application.job:
                    raise NotFoundError(f"Job for application {application_id} not found.")
                is_creator = str(application.job.employer_id) == current_user.id
                org_matches = bool(
                    current_user.employer_id
                    and application.job.creator
                    and application.job.creator.employer_id == current_user.employer_id
                )
                if not (is_creator or org_matches):
                    raise AuthorizationError(
                        "You are not authorized to evaluate applications for this job requisition."
                    )
            elif current_user.role == UserRole.SYSTEM_AUDITOR:
                pass
            else:
                raise AuthorizationError("You are not authorized to evaluate applications.")

        # 2. Fetch latest extraction run for primary document
        extraction_run = await extraction_repo.get_latest_run_for_document(
            application.primary_document_id
        )
        if not extraction_run or extraction_run.status != DocumentProcessingStatus.COMPLETED:
            raise ValidationError(
                f"Application document {application.primary_document_id} has not completed evidence extraction."
            )

        # 3. Fetch active criteria for the job
        active_criteria = await job_repo.get_active_criteria(application.job_id)
        if not active_criteria:
            raise ValidationError(f"Job {application.job_id} has no active criteria defined.")

        criteria_version = await job_repo.get_latest_criteria_version(application.job_id)

        # 4. Fetch candidate skills and evidence items from extraction run
        candidate_skills = await extraction_repo.get_candidate_skills_for_run(extraction_run.id)
        evidence_items = await extraction_repo.get_evidence_items_for_run(extraction_run.id)

        # 5. Evaluate each criterion deterministically
        criterion_mappings: list[dict[str, Any]] = []

        for criterion in active_criteria:
            mapping = self._evaluate_single_criterion(
                criterion=criterion,
                candidate_skills=candidate_skills,
                evidence_items=evidence_items,
            )
            criterion_mappings.append(mapping)

        # 6. Compute coverage counts and overall status
        total_count = len(criterion_mappings)
        supported_count = sum(
            1 for m in criterion_mappings if m["ai_status"] == EvidenceStatus.SUPPORTED
        )
        not_found_count = sum(
            1 for m in criterion_mappings if m["ai_status"] == EvidenceStatus.NOT_FOUND
        )

        required_criteria = [
            c for c in active_criteria if str(c.category).lower() in ("required", "requirement")
        ]
        required_supported = sum(
            1
            for m in criterion_mappings
            if m["ai_status"] == EvidenceStatus.SUPPORTED
            and str(m["category"]).lower() in ("required", "requirement")
        )

        if supported_count == total_count or (
            required_criteria and required_supported == len(required_criteria)
        ):
            overall_status = EvidenceStatus.SUPPORTED
        elif not_found_count == total_count:
            overall_status = EvidenceStatus.NOT_FOUND
        else:
            overall_status = EvidenceStatus.AMBIGUOUS

        # 7. Record evaluation and audit trail
        evaluation = await eval_repo.record_evaluation(
            application_id=application.id,
            job_criteria_version=criteria_version,
            extraction_run_id=extraction_run.id,
            overall_status=overall_status,
            criterion_mappings=criterion_mappings,
            summary_notes=(
                f"Evaluated {total_count} criteria: {supported_count} supported, "
                f"{not_found_count} not found, {total_count - supported_count - not_found_count} ambiguous."
            ),
            raw_model_output={
                "job_criteria_version": criteria_version,
                "extraction_run_id": str(extraction_run.id),
                "extraction_run_number": extraction_run.run_number,
                "document_id": str(application.primary_document_id),
            },
            actor_id=actor_id,
        )

        # 8. Transition application status to SCREENING
        application.status = ApplicationStatus.SCREENING
        await session.flush()

        loaded_eval = await eval_repo.get_evaluation_with_items(evaluation.id)
        return loaded_eval or evaluation

    def _evaluate_single_criterion(
        self,
        criterion: JobCriterion,
        candidate_skills: list[CandidateSkill],
        evidence_items: list[EvidenceItem],
    ) -> dict[str, Any]:
        """
        Evaluates a single criterion against extracted skills and evidence.
        Returns mapping dictionary for CriterionEvidence record.
        """
        criterion_name = criterion.name.strip()
        criterion_category = str(criterion.category)

        # Rule A: Check if criterion itself is vague or subjective
        if is_vague_criterion(criterion_name):
            return {
                "job_criterion_id": criterion.id,
                "category": criterion_category,
                "evidence_item_id": None,
                "ai_status": EvidenceStatus.AMBIGUOUS,
                "ai_confidence": 0.5,
                "ai_reasoning": (
                    f"Criterion '{criterion_name}' is subjective or vague. Evaluated as ambiguous "
                    "because subjective criteria cannot be definitively verified from static resume evidence "
                    "without structured interview assessment."
                ),
                "verification_state": VerificationState.UNVERIFIED,
                "source_excerpt": None,
                "source_page": None,
            }

        synonyms = get_synonym_set(criterion_name)

        # Find matching candidate skills
        matched_skills: list[CandidateSkill] = []
        for skill in candidate_skills:
            skill_norm = normalize_term(skill.skill_name)
            if any(syn in skill_norm or skill_norm in syn for syn in synonyms):
                matched_skills.append(skill)

        # Find matching evidence items
        matched_evidence: list[EvidenceItem] = []
        for item in evidence_items:
            claim_norm = normalize_term(item.claim_text)
            excerpt_norm = normalize_term(item.source_excerpt)
            if any(syn in claim_norm or syn in excerpt_norm for syn in synonyms):
                matched_evidence.append(item)

        # Rule B: If no skills and no evidence found -> not_found
        if not matched_skills and not matched_evidence:
            return {
                "job_criterion_id": criterion.id,
                "category": criterion_category,
                "evidence_item_id": None,
                "ai_status": EvidenceStatus.NOT_FOUND,
                "ai_confidence": 1.0,
                "ai_reasoning": (
                    f"No validated evidence for '{criterion_name}' was found in the submitted material. "
                    "Note: This does not mean the candidate lacks this skill, only that it was not documented "
                    "in the submitted resume."
                ),
                "verification_state": VerificationState.UNVERIFIED,
                "source_excerpt": None,
                "source_page": None,
            }

        # Rule C: Evidence or skill found, determine whether supported or ambiguous
        primary_evidence: EvidenceItem | None = matched_evidence[0] if matched_evidence else None
        primary_skill: CandidateSkill | None = matched_skills[0] if matched_skills else None

        source_excerpt = (
            primary_evidence.source_excerpt
            if primary_evidence
            else (primary_skill.source_excerpt if primary_skill else None)
        )
        source_page = (
            primary_evidence.source_page
            if primary_evidence
            else (primary_skill.source_page if primary_skill else None)
        )
        evidence_item_id = primary_evidence.id if primary_evidence else None

        # Check for ungrounded evidence
        if primary_evidence and not primary_evidence.grounding_verified:
            return {
                "job_criterion_id": criterion.id,
                "category": criterion_category,
                "evidence_item_id": evidence_item_id,
                "ai_status": EvidenceStatus.AMBIGUOUS,
                "ai_confidence": 0.4,
                "ai_reasoning": (
                    f"Evidence referencing '{criterion_name}' was extracted, but grounding verification "
                    "against the original document text failed or was unverified."
                ),
                "verification_state": VerificationState.UNVERIFIED,
                "source_excerpt": source_excerpt,
                "source_page": source_page,
            }

        # Check for weak or qualifying language in excerpt or claim
        combined_text = f"{source_excerpt or ''} {primary_evidence.claim_text if primary_evidence else ''}".lower()
        has_weak_language = any(
            re.search(rf"\b{re.escape(w)}\b", combined_text) for w in WEAK_EXPOSURE_KEYWORDS
        )

        # Check for date conflicts in metadata
        has_date_conflict = False
        if primary_evidence and primary_evidence.raw_metadata:
            has_date_conflict = bool(
                primary_evidence.raw_metadata.get("date_conflict")
                or primary_evidence.raw_metadata.get("has_date_conflict")
            )

        if has_weak_language or has_date_conflict:
            reason = (
                f"Candidate mentions '{criterion_name}', but evidence indicates limited exposure, "
                "basic familiarity, or conflicting dates in the timeline."
            )
            return {
                "job_criterion_id": criterion.id,
                "category": criterion_category,
                "evidence_item_id": evidence_item_id,
                "ai_status": EvidenceStatus.AMBIGUOUS,
                "ai_confidence": 0.6,
                "ai_reasoning": reason,
                "verification_state": VerificationState.UNVERIFIED,
                "source_excerpt": source_excerpt,
                "source_page": source_page,
            }

        # Validated, grounded, direct evidence
        confidence = (
            primary_evidence.confidence
            if primary_evidence
            else (primary_skill.confidence if primary_skill else 1.0)
        )
        return {
            "job_criterion_id": criterion.id,
            "category": criterion_category,
            "evidence_item_id": evidence_item_id,
            "ai_status": EvidenceStatus.SUPPORTED,
            "ai_confidence": confidence,
            "ai_reasoning": (
                f"Validated source evidence directly demonstrates experience with '{criterion_name}' "
                f"on page {source_page}."
            ),
            "verification_state": VerificationState.UNVERIFIED,
            "source_excerpt": source_excerpt,
            "source_page": source_page,
        }

    @staticmethod
    def build_evaluation_response(evaluation: Evaluation) -> EvaluationResponse:
        """
        Builds the EvaluationResponse schema with explicit factual coverage counts
        and individual criterion evaluations.
        """
        items: list[CriterionEvaluationItem] = []
        supported_count = 0
        not_found_count = 0
        ambiguous_count = 0
        required_total = 0
        required_supported = 0
        preferred_total = 0
        preferred_supported = 0

        for ce in evaluation.criterion_evidence_items:
            cat = str(ce.criterion.category) if ce.criterion else "required"
            is_req = cat.lower() in ("required", "requirement")

            if is_req:
                required_total += 1
            else:
                preferred_total += 1

            if ce.ai_status == EvidenceStatus.SUPPORTED:
                supported_count += 1
                if is_req:
                    required_supported += 1
                else:
                    preferred_supported += 1
            elif ce.ai_status == EvidenceStatus.NOT_FOUND:
                not_found_count += 1
            else:
                ambiguous_count += 1

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

        coverage = EvidenceCoverageSummary(
            total_criteria=len(items),
            supported_count=supported_count,
            not_found_count=not_found_count,
            ambiguous_count=ambiguous_count,
            required_total=required_total,
            required_supported_count=required_supported,
            preferred_total=preferred_total,
            preferred_supported_count=preferred_supported,
        )

        return EvaluationResponse(
            id=evaluation.id,
            application_id=evaluation.application_id,
            version=evaluation.version,
            job_criteria_version=evaluation.job_criteria_version,
            extraction_run_id=evaluation.extraction_run_id,
            overall_status=evaluation.overall_status,
            coverage=coverage,
            criteria_evaluations=items,
            summary_notes=evaluation.summary_notes,
            created_at=evaluation.created_at,
        )
