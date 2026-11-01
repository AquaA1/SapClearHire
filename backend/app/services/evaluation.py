import asyncio
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.logging import logger
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
    "git": {"git", "github", "gitlab", "version control"},
    "github": {"git", "github", "gitlab", "version control"},
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

# Weak or qualifying phrases that indicate ambiguous or insufficient exposure.
# Note: 'student' is intentionally excluded so titles like 'Student Expense Tracker'
# are not penalized simply for containing the word student.
WEAK_EXPOSURE_KEYWORDS: set[str] = {
    "basic",
    "familiarity",
    "familiar with",
    "exposure",
    "learning",
    "introductory",
    "beginner",
    "novice",
    "academic only",
    "elementary",
    "minimal",
}

# Evidence priority tiers
TIER_EXPERIENCE = 1
TIER_PROJECT = 2
TIER_CERTIFICATION = 3
TIER_EDUCATION = 4
TIER_SKILL = 5


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


def matches_criterion_term(text: str, synonyms: set[str]) -> bool:
    """Check if normalized text contains any synonym as a distinct token/phrase using word boundaries."""
    norm = normalize_term(text)
    if not norm:
        return False
    for syn in synonyms:
        syn_norm = normalize_term(syn)
        if syn_norm and re.search(rf"\b{re.escape(syn_norm)}\b", norm):
            return True
    return False


def has_weak_exposure_qualifier(criterion_name: str, text: str, synonyms: set[str]) -> bool:
    """
    Check if a weak exposure keyword specifically qualifies the target criterion in context.
    Splits text by clause delimiters (commas, semicolons, bullets, parentheses, newlines)
    to isolate qualifications to their specific skill or claim without contaminating adjacent items.
    """
    if not text:
        return False

    segments = re.split(r"[,;\n•|\(\)\[\]\.\t/]", text)
    for seg in segments:
        seg_clean = seg.strip()
        if not seg_clean:
            continue
        if matches_criterion_term(seg_clean, synonyms):
            seg_norm = normalize_term(seg_clean)
            for kw in WEAK_EXPOSURE_KEYWORDS:
                kw_norm = normalize_term(kw)
                if re.search(rf"\b{re.escape(kw_norm)}\b", seg_norm):
                    return True
    return False


def is_vague_criterion(name: str) -> bool:
    """Check if a criterion is subjective or vague."""
    norm = normalize_term(name)
    if norm in VAGUE_CRITERIA_KEYWORDS:
        return True
    return any(vague in norm for vague in VAGUE_CRITERIA_KEYWORDS)


def is_bare_skill_list(excerpt: str) -> bool:
    """
    Check if an excerpt represents a bare skill list rather than contextual descriptive text.
    Bare skill lists typically start with section headers (e.g., 'Tools:', 'Programming:')
    and consist solely of comma- or bullet-separated technology names without connecting
    prepositions or descriptive context (e.g., 'using', 'with', 'in', 'clusters', 'pipeline').
    """
    cleaned = excerpt.strip().lower()

    # Check for skill-list headers first
    headers = (
        "tools:",
        "languages:",
        "skills:",
        "technologies:",
        "programming:",
        "frameworks:",
        "databases:",
        "concepts:",
        "platforms:",
        "libraries:",
        "technical skills:",
    )
    if any(cleaned.startswith(h) for h in headers):
        return True

    # Prepositions / conjunctions / operational nouns indicating contextual application
    contextual_indicators = (
        "using",
        "with",
        "for",
        "via",
        "through",
        "deployed",
        "built",
        "designed",
        "created",
        "implemented",
        "architected",
        "tuned",
        "administered",
        "managed",
        "clusters",
        "microservices",
        "pipelines",
        "repository",
        "repositories",
        "branches",
        "commits",
        "tables",
        "queries",
        "statements",
        "framework",
    )
    if any(re.search(rf"\b{re.escape(ind)}\b", cleaned) for ind in contextual_indicators):
        return False

    # Check if text is just a comma-separated list of 2+ items without descriptive context
    items = [it.strip() for it in re.split(r"[,;•|/]", cleaned) if it.strip()]
    if len(items) >= 2 and all(len(it.split()) <= 3 for it in items):
        return True

    return False


def classify_evidence_item(
    item: EvidenceItem, criterion_name: str, synonyms: set[str]
) -> tuple[bool, int, float, str]:
    """
    Evaluates whether an EvidenceItem is relevant to a criterion without cross-contamination.
    Returns:
        (is_matched, priority_tier, relevance_score, match_description)
    """
    raw_meta = item.raw_metadata or {}
    item_type = raw_meta.get("item_type")

    # If item_type is not explicitly set, infer from claim_text or structure
    if not item_type:
        claim_lower = item.claim_text.lower()
        if claim_lower.startswith("candidate possesses skill:"):
            item_type = "skill"
        elif claim_lower.startswith("experience as") or "experience" in claim_lower:
            item_type = "experience"
        elif claim_lower.startswith("project:") or "project" in claim_lower:
            item_type = "project"
        elif claim_lower.startswith("education:") or "education" in claim_lower:
            item_type = "education"
        elif claim_lower.startswith("certification:") or "certification" in claim_lower:
            item_type = "certification"
        else:
            item_type = "general"

    if item_type == "skill":
        # Cross-criterion isolation:
        # Match ONLY using skill_name or structured claim; NEVER match across shared source excerpts!
        skill_name = raw_meta.get("skill_name")
        if not skill_name:
            m = re.match(r"^Candidate possesses skill:\s*(.+)$", item.claim_text, re.IGNORECASE)
            skill_name = m.group(1).strip() if m else item.claim_text

        if matches_criterion_term(skill_name, synonyms):
            is_exact = normalize_term(skill_name) == normalize_term(criterion_name)
            relevance = 1.0 if is_exact else 0.9

            excerpt = (item.source_excerpt or "").strip()
            is_bare = is_bare_skill_list(excerpt)
            tier = TIER_SKILL if is_bare else TIER_EXPERIENCE
            desc = f"Skill: {skill_name}" if is_bare else f"Applied skill experience: {skill_name}"
            return True, tier, relevance, desc
        return False, 99, 0.0, ""

    elif item_type == "experience":
        job_title = raw_meta.get("job_title", "")
        resps = raw_meta.get("responsibilities", [])
        resps_text = " ".join(resps) if isinstance(resps, list) else str(resps)

        matched_title = matches_criterion_term(job_title, synonyms)
        matched_resp = matches_criterion_term(resps_text, synonyms)
        matched_claim = matches_criterion_term(item.claim_text, synonyms)
        matched_excerpt = matches_criterion_term(item.source_excerpt, synonyms)

        if matched_title or matched_resp or matched_claim or matched_excerpt:
            relevance = 1.0 if (matched_title or matched_resp) else 0.85
            role_desc = job_title or "Professional Experience"
            return True, TIER_EXPERIENCE, relevance, f"Experience: {role_desc}"
        return False, 99, 0.0, ""

    elif item_type == "project":
        project_name = raw_meta.get("project_name", "") or "Project"
        technologies = raw_meta.get("technologies", [])
        if isinstance(technologies, list):
            matched_tech = any(matches_criterion_term(t, synonyms) for t in technologies)
        else:
            matched_tech = matches_criterion_term(str(technologies), synonyms)

        description = raw_meta.get("description", "")
        matched_desc = matches_criterion_term(description, synonyms)
        matched_claim = matches_criterion_term(item.claim_text, synonyms)
        matched_excerpt = matches_criterion_term(item.source_excerpt, synonyms)

        if matched_tech or matched_desc or matched_claim or matched_excerpt:
            relevance = 1.0 if (matched_tech and matched_desc) else (0.95 if matched_tech else 0.85)
            return True, TIER_PROJECT, relevance, f"Project: {project_name}"
        return False, 99, 0.0, ""

    elif item_type == "certification":
        cert_name = raw_meta.get("certification_name", "") or item.claim_text
        if matches_criterion_term(cert_name, synonyms) or matches_criterion_term(
            item.source_excerpt, synonyms
        ):
            return True, TIER_CERTIFICATION, 1.0, f"Certification: {cert_name}"
        return False, 99, 0.0, ""

    elif item_type == "education":
        degree = raw_meta.get("degree", "")
        field = raw_meta.get("field_of_study", "")
        matched_field = matches_criterion_term(field, synonyms)
        matched_degree = matches_criterion_term(degree, synonyms)
        if matched_field or matched_degree:
            return True, TIER_EDUCATION, 0.7, f"Education: {degree} in {field}"
        return False, 99, 0.0, ""

    else:
        # General / legacy fallback
        matched_claim = matches_criterion_term(item.claim_text, synonyms)
        excerpt = item.source_excerpt or ""
        is_header_list = any(
            excerpt.strip().lower().startswith(header)
            for header in (
                "tools:",
                "languages:",
                "skills:",
                "technologies:",
                "programming:",
                "concepts:",
            )
        )
        matched_excerpt = False if is_header_list else matches_criterion_term(excerpt, synonyms)

        if matched_claim or matched_excerpt:
            has_action_verbs = any(
                re.search(rf"\b{verb}\b", f"{item.claim_text} {excerpt}".lower())
                for verb in (
                    "built",
                    "developed",
                    "created",
                    "used",
                    "administered",
                    "deployed",
                    "designed",
                    "implemented",
                    "engineered",
                )
            )
            tier = TIER_PROJECT if has_action_verbs else TIER_SKILL
            relevance = 0.9 if has_action_verbs else 0.6
            return True, tier, relevance, "Document evidence"
        return False, 99, 0.0, ""


class EvaluationService:
    """
    Deterministic evidence evaluation service.
    Evaluates candidate documents and structured evidence against versioned job criteria.
    Strictly yields exactly one status per criterion: supported, not_found, or ambiguous.
    """

    _global_lock = asyncio.Lock()
    _app_locks: dict[uuid.UUID, asyncio.Lock] = {}

    @classmethod
    async def _get_app_lock(cls, app_id: uuid.UUID) -> asyncio.Lock:
        async with cls._global_lock:
            if app_id not in cls._app_locks:
                cls._app_locks[app_id] = asyncio.Lock()
            return cls._app_locks[app_id]

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
        Guards against duplicate concurrent evaluations for the same application via per-application locking.
        """
        app_lock = await self._get_app_lock(application_id)
        async with app_lock:
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
                f"Application document {application.primary_document_id} has not completed evidence extraction. "
                "Structured AI claim extraction is required before evidence screening can be evaluated."
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

        criteria_summary = {
            str(m["job_criterion_id"]): {
                "primary_evidence_id": str(m["evidence_item_id"])
                if m.get("evidence_item_id")
                else None,
                "supporting_evidence_ids": [
                    str(sid) for sid in m.get("supporting_evidence_ids", [])
                ],
            }
            for m in criterion_mappings
        }

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
                "criteria_evidence_summary": criteria_summary,
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
                "supporting_evidence_ids": [],
            }

        synonyms = get_synonym_set(criterion_name)

        # 1. Collect and rank all matching evidence items using deterministic multi-tier ranking
        ranked_evidence: list[tuple[int, int, float, float, int, EvidenceItem, str]] = []
        for item in evidence_items:
            is_matched, tier, relevance, desc = classify_evidence_item(
                item=item, criterion_name=criterion_name, synonyms=synonyms
            )
            if is_matched:
                rank_tuple = (
                    tier,
                    -int(item.grounding_verified),
                    -relevance,
                    -item.confidence,
                    -len(item.source_excerpt or ""),
                    item,
                    desc,
                )
                ranked_evidence.append(rank_tuple)

        ranked_evidence.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4]))

        # 2. Check CandidateSkill objects as fallback if no EvidenceItem matches
        matched_skills: list[CandidateSkill] = []
        for skill in candidate_skills:
            if matches_criterion_term(skill.skill_name, synonyms):
                matched_skills.append(skill)

        # Rule B: If no skills and no evidence found -> not_found
        if not ranked_evidence and not matched_skills:
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
                "supporting_evidence_ids": [],
            }

        # Rule C: Evidence item exists
        if ranked_evidence:
            primary_entry = ranked_evidence[0]
            primary_tier = primary_entry[0]
            primary_evidence = primary_entry[5]
            primary_desc = primary_entry[6]
            supporting_ids = [entry[5].id for entry in ranked_evidence[1:]]

            source_excerpt = primary_evidence.source_excerpt
            source_page = primary_evidence.source_page
            evidence_item_id = primary_evidence.id

            # Ungrounded evidence
            if not primary_evidence.grounding_verified:
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
                    "supporting_evidence_ids": supporting_ids,
                }

            # Date conflicts in metadata
            has_date_conflict = False
            if primary_evidence.raw_metadata:
                has_date_conflict = bool(
                    primary_evidence.raw_metadata.get("date_conflict")
                    or primary_evidence.raw_metadata.get("has_date_conflict")
                )
            if has_date_conflict:
                return {
                    "job_criterion_id": criterion.id,
                    "category": criterion_category,
                    "evidence_item_id": evidence_item_id,
                    "ai_status": EvidenceStatus.AMBIGUOUS,
                    "ai_confidence": 0.6,
                    "ai_reasoning": (
                        f"Candidate mentions '{criterion_name}', but evidence indicates conflicting dates in the timeline."
                    ),
                    "verification_state": VerificationState.UNVERIFIED,
                    "source_excerpt": source_excerpt,
                    "source_page": source_page,
                    "supporting_evidence_ids": supporting_ids,
                }

            # Criterion-specific weak exposure check
            combined_text = f"{source_excerpt or ''}\n{primary_evidence.claim_text or ''}"
            if has_weak_exposure_qualifier(criterion_name, combined_text, synonyms):
                return {
                    "job_criterion_id": criterion.id,
                    "category": criterion_category,
                    "evidence_item_id": evidence_item_id,
                    "ai_status": EvidenceStatus.AMBIGUOUS,
                    "ai_confidence": 0.6,
                    "ai_reasoning": (
                        f"Candidate mentions '{criterion_name}', but evidence indicates limited exposure, "
                        "basic familiarity, or introductory usage."
                    ),
                    "verification_state": VerificationState.UNVERIFIED,
                    "source_excerpt": source_excerpt,
                    "source_page": source_page,
                    "supporting_evidence_ids": supporting_ids,
                }

            # Bare skill-list scoring: bare skill listing alone produces ambiguous (never supported with 1.0)
            if primary_tier == TIER_SKILL:
                return {
                    "job_criterion_id": criterion.id,
                    "category": criterion_category,
                    "evidence_item_id": evidence_item_id,
                    "ai_status": EvidenceStatus.AMBIGUOUS,
                    "ai_confidence": 0.7,
                    "ai_reasoning": (
                        f"Candidate lists '{criterion_name}' in skills inventory, but without project, "
                        "experience, or applied evidence demonstrating practical usage."
                    ),
                    "verification_state": VerificationState.UNVERIFIED,
                    "source_excerpt": source_excerpt,
                    "source_page": source_page,
                    "supporting_evidence_ids": supporting_ids,
                }

            # Education coursework for a non-education technical skill
            if primary_tier == TIER_EDUCATION:
                is_edu_criterion = any(
                    kw in normalize_term(criterion_name)
                    for kw in (
                        "degree",
                        "bachelor",
                        "master",
                        "phd",
                        "education",
                        "b tech",
                        "b s",
                        "m s",
                        "computer science",
                    )
                )
                if not is_edu_criterion:
                    return {
                        "job_criterion_id": criterion.id,
                        "category": criterion_category,
                        "evidence_item_id": evidence_item_id,
                        "ai_status": EvidenceStatus.AMBIGUOUS,
                        "ai_confidence": 0.6,
                        "ai_reasoning": (
                            f"Candidate references '{criterion_name}' in academic education coursework, "
                            "but without applied project or professional experience."
                        ),
                        "verification_state": VerificationState.UNVERIFIED,
                        "source_excerpt": source_excerpt,
                        "source_page": source_page,
                        "supporting_evidence_ids": supporting_ids,
                    }

            # Validated, applied source evidence (Experience, Project, Certification)
            confidence = primary_evidence.confidence
            support_note = ""
            if supporting_ids:
                support_note = f" (supported by {len(supporting_ids)} other evidence item(s))"

            return {
                "job_criterion_id": criterion.id,
                "category": criterion_category,
                "evidence_item_id": evidence_item_id,
                "ai_status": EvidenceStatus.SUPPORTED,
                "ai_confidence": confidence,
                "ai_reasoning": (
                    f"Validated source evidence ({primary_desc}) directly demonstrates experience with "
                    f"'{criterion_name}' on page {source_page}.{support_note}"
                ),
                "verification_state": VerificationState.UNVERIFIED,
                "source_excerpt": source_excerpt,
                "source_page": source_page,
                "supporting_evidence_ids": supporting_ids,
            }

        # Fallback: only CandidateSkill found
        primary_skill = matched_skills[0]
        return {
            "job_criterion_id": criterion.id,
            "category": criterion_category,
            "evidence_item_id": None,
            "ai_status": EvidenceStatus.AMBIGUOUS,
            "ai_confidence": 0.7,
            "ai_reasoning": (
                f"Candidate lists '{criterion_name}' in skills inventory, but without project, "
                "experience, or applied evidence demonstrating practical usage."
            ),
            "verification_state": VerificationState.UNVERIFIED,
            "source_excerpt": primary_skill.source_excerpt,
            "source_page": primary_skill.source_page,
            "supporting_evidence_ids": [],
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


EvidenceEvaluationService = EvaluationService

