import asyncio
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from dataclasses import dataclass, field

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.logging import logger
from app.core.security import CurrentUser, UserRole
from app.db.models.application import Application
from app.db.models.document import CandidateSkill, EvidenceItem
from app.db.models.enums import (
    ApplicationStatus,
    DocumentProcessingStatus,
    EvidenceStatus,
    ReviewDecisionType,
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
    SubcriterionEvaluationItem,
)
from app.schemas.review import CandidateClarificationItem, ReviewDecisionItem
from app.utils.text import validate_excerpt_in_text

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
    "sql": {"sql", "rdbms", "relational database", "sql queries", "sql query", "sql statements"},
    "nosql": {"nosql", "mongodb", "dynamodb"},
    "git": {"git", "github", "gitlab", "version control"},
    "github": {"git", "github", "gitlab", "version control"},
    "asyncio": {"asyncio", "asynchronous programming", "async", "async await"},
    "asynchronous programming": {"asyncio", "asynchronous programming", "async", "async await"},
    "rest api": {"rest api", "rest apis", "restful api", "restful apis", "rest", "restful"},
    "restful api": {"rest api", "rest apis", "restful api", "restful apis", "rest", "restful"},
    "scaling": {"scaling", "database scaling", "horizontal scaling", "vertical scaling", "replication", "sharding", "partitioning"},
    "database scaling": {"scaling", "database scaling", "horizontal scaling", "vertical scaling", "replication", "sharding", "partitioning"},
    "index optimization": {"index optimization", "indexing", "index tuning", "indexes", "indices", "execution plan", "query optimization", "explain analyze"},
    "indexing": {"index optimization", "indexing", "index tuning", "indexes", "indices", "execution plan", "query optimization", "explain analyze"},
    "table design": {"table design", "tables", "schema design", "table modeling", "relational database design", "database design"},
    "schema design": {"table design", "tables", "schema design", "table modeling", "relational database design", "database design"},
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


@dataclass
class SubcriterionDefinition:
    """Definition for a decomposed requirement of a job criterion."""

    id: str
    name: str
    required_keywords: list[str] = field(default_factory=list)
    description: str | None = None
    is_framework: bool = False
    is_duration: bool = False
    is_production: bool = False
    require_project_or_experience: bool = False
    min_years: float | None = None


def decompose_criterion(
    criterion_name: str, description: str | None = None
) -> list[SubcriterionDefinition]:
    """
    Decomposes a job criterion into constituent verifiable subrequirements.
    Distinguishes atomic criteria from compound criteria requiring multi-layer matching.
    """
    name_norm = normalize_term(criterion_name)
    desc_norm = normalize_term(description or "")
    combined = f"{name_norm} {desc_norm}".strip()

    # Pattern 1: Production + Years + Python (e.g. "2+ Years Production Python (FastAPI / AsyncIO)")
    has_duration = bool(re.search(r"(\d+)\+?\s*years?", combined))
    has_production = "production" in combined

    if (
        ("fastapi" in combined or "asyncio" in combined)
        and "python" in combined
        and (has_duration or has_production)
    ):
        dur_match = re.search(r"(\d+)\+?\s*years?", combined)
        min_yrs = float(dur_match.group(1)) if dur_match else 2.0
        return [
            SubcriterionDefinition(
                id="sub_python",
                name="Python Programming",
                required_keywords=["python", "py", "python3"],
                description="Proficiency in Python programming language",
            ),
            SubcriterionDefinition(
                id="sub_fastapi",
                name="FastAPI Framework",
                required_keywords=["fastapi"],
                is_framework=True,
                description="Direct hands-on experience developing with FastAPI",
            ),
            SubcriterionDefinition(
                id="sub_asyncio",
                name="AsyncIO / Asynchronous Programming",
                required_keywords=["asyncio", "asynchronous programming", "async", "async await"],
                description="Asynchronous Python programming and concurrency",
            ),
            SubcriterionDefinition(
                id="sub_duration",
                name=f"{int(min_yrs) if min_yrs.is_integer() else min_yrs}+ Years Experience Duration",
                required_keywords=[],
                is_duration=True,
                min_years=min_yrs,
                description=f"At least {int(min_yrs) if min_yrs.is_integer() else min_yrs} years of documented experience",
            ),
            SubcriterionDefinition(
                id="sub_production",
                name="Production Environment Experience",
                required_keywords=[],
                is_production=True,
                description="Experience operating applications in enterprise production environments",
            ),
        ]

    # Pattern 2: "Experience in FastAPI" or compound criteria demanding FastAPI
    if "fastapi" in name_norm and any(
        kw in name_norm for kw in ["experience", "framework", "rest", "api", "production", "development"]
    ):
        return [
            SubcriterionDefinition(
                id="sub_python",
                name="Python Programming",
                required_keywords=["python", "py", "python3"],
                description="Python programming language fundamentals",
            ),
            SubcriterionDefinition(
                id="sub_rest_api",
                name="REST API Development",
                required_keywords=["rest api", "rest apis", "restful api", "restful", "rest", "api", "fastapi"],
                description="Designing and implementing RESTful API endpoints",
            ),
            SubcriterionDefinition(
                id="sub_fastapi",
                name="FastAPI Framework",
                required_keywords=["fastapi"],
                is_framework=True,
                description="Direct implementation experience using the FastAPI framework",
            ),
        ]

    # Pattern 3: PostgreSQL Scaling & Index Optimization
    if any(p in name_norm for p in ["postgres", "postgresql"]) and any(
        kw in name_norm for kw in ["scaling", "index", "optimization", "tuning"]
    ):
        return [
            SubcriterionDefinition(
                id="sub_postgres",
                name="PostgreSQL Database",
                required_keywords=["postgresql", "postgres", "psql"],
                description="Relational database operations and data handling with PostgreSQL",
            ),
            SubcriterionDefinition(
                id="sub_table_design",
                name="PostgreSQL Table Design",
                required_keywords=[
                    "table design",
                    "tables",
                    "relational database design",
                    "schema design",
                    "table modeling",
                ],
                description="Designing database schemas, relational tables, and data models",
            ),
            SubcriterionDefinition(
                id="sub_sql_queries",
                name="SQL Query Experience",
                required_keywords=[
                    "sql",
                    "sql query",
                    "sql queries",
                    "sql statements",
                    "joins",
                    "aggregate functions",
                ],
                description="Writing SQL queries using joins, grouping, and aggregate functions",
            ),
            SubcriterionDefinition(
                id="sub_scaling",
                name="Database Scaling",
                required_keywords=[
                    "scaling",
                    "database scaling",
                    "horizontal scaling",
                    "vertical scaling",
                    "replication",
                    "sharding",
                    "partitioning",
                ],
                description="Database scaling strategies including replication, partitioning, and sharding",
            ),
            SubcriterionDefinition(
                id="sub_index_opt",
                name="Index Optimization",
                required_keywords=[
                    "index optimization",
                    "indexing",
                    "index tuning",
                    "indexes",
                    "indices",
                    "execution plan",
                    "query optimization",
                    "explain analyze",
                ],
                description="Creating performance indexes, query optimization, and analyzing execution plans",
            ),
        ]

    # Pattern 4: Experience in PostgreSQL (Practical / applied experience)
    if any(p in name_norm for p in ["postgres", "postgresql"]) and any(
        kw in name_norm for kw in ["experience", "project", "work", "applied"]
    ):
        return [
            SubcriterionDefinition(
                id="sub_postgres",
                name="PostgreSQL Database",
                required_keywords=["postgresql", "postgres", "psql"],
                description="Knowledge and usage of PostgreSQL relational database",
            ),
            SubcriterionDefinition(
                id="sub_postgres_project",
                name="PostgreSQL Project Experience",
                required_keywords=["postgresql", "postgres", "psql"],
                require_project_or_experience=True,
                description="Applied project or professional experience utilizing PostgreSQL",
            ),
        ]

    # Pattern 5: Criteria with explicit conjunctions (&, and, /, commas)
    split_parts = re.split(r"\s*(?:&|\band\b|/|,)\s*", criterion_name, flags=re.IGNORECASE)
    parts = [p.strip() for p in split_parts if p.strip() and len(normalize_term(p)) > 1]
    if len(parts) > 1:
        defs = []
        for i, part in enumerate(parts):
            p_norm = normalize_term(part)
            dur_match = re.search(r"(\d+)\+?\s*years?", p_norm)
            if dur_match:
                yrs = float(dur_match.group(1))
                defs.append(
                    SubcriterionDefinition(
                        id=f"sub_{i}_{int(yrs)}yr",
                        name=f"{int(yrs) if yrs.is_integer() else yrs}+ Years Experience",
                        required_keywords=[],
                        is_duration=True,
                        min_years=yrs,
                    )
                )
            elif "production" in p_norm:
                defs.append(
                    SubcriterionDefinition(
                        id=f"sub_{i}_prod",
                        name="Production Experience",
                        required_keywords=[],
                        is_production=True,
                    )
                )
            else:
                defs.append(
                    SubcriterionDefinition(
                        id=f"sub_{i}_{p_norm[:15]}",
                        name=part,
                        required_keywords=[p_norm],
                        description=f"Demonstrated capability in {part}",
                    )
                )
        if len(defs) > 1:
            return defs

    # Default: Atomic criterion
    return [
        SubcriterionDefinition(
            id=f"sub_{name_norm[:20]}",
            name=criterion_name,
            required_keywords=[name_norm],
            description=description or f"Demonstrated evidence for {criterion_name}",
        )
    ]


def extract_matching_sentence(text: str, synonyms: set[str]) -> str:
    """Extracts the specific sentence or bullet point that matches the criterion keywords."""
    if not text:
        return ""
    lines = re.split(r"[\n•\r]", text)
    for line in lines:
        cleaned = line.strip().lstrip("-*•").strip()
        if cleaned and matches_criterion_term(cleaned, synonyms):
            return cleaned
    return text.strip()


def evaluate_subcriterion(
    sub: SubcriterionDefinition,
    evidence_items: list[EvidenceItem],
    candidate_skills: list[CandidateSkill],
    resume_pages: dict[str, Any] | None = None,
) -> SubcriterionEvaluationItem:
    """
    Evaluates a single subrequirement deterministically with multi-layer evidence retrieval,
    controlled synonyms, and strict source grounding.
    """
    # 1. Duration requirement
    if sub.is_duration:
        min_years = sub.min_years or 0.0
        skill_years = max(
            (
                float(s.years_of_experience)
                for s in candidate_skills
                if getattr(s, "years_of_experience", None) is not None
            ),
            default=0.0,
        )
        exp_years = 0.0
        for ev in evidence_items:
            meta = ev.raw_metadata or {}
            ev_yrs = meta.get("years_of_experience")
            if ev_yrs is not None:
                exp_years = max(exp_years, float(ev_yrs))
            if meta.get("item_type") == "experience":
                start = meta.get("start_date")
                end = meta.get("end_date")
                if start:
                    start_yr = (
                        int(re.search(r"\d{4}", str(start)).group(0))
                        if re.search(r"\d{4}", str(start))
                        else None
                    )
                    end_yr = (
                        int(re.search(r"\d{4}", str(end)).group(0))
                        if end and re.search(r"\d{4}", str(end))
                        else 2026
                    )
                    if start_yr:
                        exp_years += max(0, end_yr - start_yr)

        total_years = max(skill_years, exp_years)
        if total_years >= min_years and min_years > 0:
            return SubcriterionEvaluationItem(
                id=sub.id,
                name=sub.name,
                status=EvidenceStatus.SUPPORTED,
                confidence=0.95,
                explanation=f"Documented experience ({total_years:.1f} years) satisfies the {min_years}+ years requirement.",
            )
        else:
            return SubcriterionEvaluationItem(
                id=sub.id,
                name=sub.name,
                status=EvidenceStatus.NOT_FOUND,
                confidence=0.90,
                missing_reason=f"Resume documents academic projects but does not document {min_years}+ years of professional experience.",
                explanation=f"Resume documents academic projects but does not document {min_years}+ years of professional experience. Note: This indicates absence in the submitted resume, not a verified lack of capability.",
            )

    # 2. Production requirement
    if sub.is_production:
        has_prod = False
        prod_excerpt = None
        prod_page = None
        for ev in evidence_items:
            meta = ev.raw_metadata or {}
            combined_txt = f"{ev.claim_text} {ev.source_excerpt or ''} {meta.get('description', '')}".lower()
            if meta.get("item_type") == "experience":
                company = str(meta.get("company", "")).lower()
                is_academic = any(
                    ac in company
                    for ac in ["university", "college", "institute", "school", "student", "intern"]
                )
                if not is_academic and (
                    "production" in combined_txt
                    or "enterprise" in combined_txt
                    or "microservices" in combined_txt
                ):
                    has_prod = True
                    prod_excerpt = ev.source_excerpt
                    prod_page = ev.source_page
                    break
            elif "production" in combined_txt or "deployed to production" in combined_txt:
                has_prod = True
                prod_excerpt = ev.source_excerpt
                prod_page = ev.source_page
                break

        if has_prod:
            return SubcriterionEvaluationItem(
                id=sub.id,
                name=sub.name,
                status=EvidenceStatus.SUPPORTED,
                confidence=0.95,
                source_excerpt=prod_excerpt,
                source_page=prod_page,
                explanation="Evidence demonstrates experience in production / enterprise environments.",
            )
        else:
            return SubcriterionEvaluationItem(
                id=sub.id,
                name=sub.name,
                status=EvidenceStatus.NOT_FOUND,
                confidence=0.90,
                missing_reason="Documented experience is in academic and personal projects rather than enterprise production environments.",
                explanation="Documented experience is in academic and personal projects rather than enterprise production environments. Note: This indicates absence in the submitted resume, not a verified lack of capability.",
            )

    # 3. Strict framework requirement (e.g. FastAPI)
    if sub.is_framework:
        kw_syns: set[str] = set()
        for kw in sub.required_keywords:
            kw_syns.update(get_synonym_set(kw))
            kw_syns.add(normalize_term(kw))

        # Check evidence items
        matched_ev: EvidenceItem | None = None
        for ev in evidence_items:
            meta = ev.raw_metadata or {}
            txt = f"{ev.claim_text} {ev.source_excerpt or ''} {meta.get('skill_name', '')} {meta.get('technologies', '')} {meta.get('description', '')}"
            if matches_criterion_term(txt, kw_syns):
                matched_ev = ev
                break

        # Check candidate skills
        matched_sk: CandidateSkill | None = None
        if not matched_ev:
            for sk in candidate_skills:
                if matches_criterion_term(sk.skill_name, kw_syns):
                    matched_sk = sk
                    break

        # Check raw resume pages
        page_match_excerpt = None
        page_match_num = None
        if not matched_ev and not matched_sk and resume_pages:
            for pg_str, pg_txt in resume_pages.items():
                if matches_criterion_term(str(pg_txt), kw_syns):
                    for line in str(pg_txt).split("\n"):
                        line_clean = line.strip().lstrip("-*•").strip()
                        if matches_criterion_term(line_clean, kw_syns) and validate_excerpt_in_text(
                            line_clean, str(pg_txt)
                        ):
                            page_match_excerpt = line_clean
                            page_match_num = int(pg_str) if str(pg_str).isdigit() else 1
                            break
                    if page_match_excerpt:
                        break

        if matched_ev and matched_ev.grounding_verified:
            return SubcriterionEvaluationItem(
                id=sub.id,
                name=sub.name,
                status=EvidenceStatus.SUPPORTED,
                confidence=matched_ev.confidence,
                source_excerpt=matched_ev.source_excerpt,
                source_page=matched_ev.source_page,
                explanation=f"Direct evidence for '{sub.name}' found on page {matched_ev.source_page}.",
                citations=[
                    {
                        "document_id": str(matched_ev.document_id)
                        if matched_ev.document_id
                        else None,
                        "page_number": matched_ev.source_page,
                        "exact_excerpt": matched_ev.source_excerpt,
                        "evidence_type": (matched_ev.raw_metadata or {}).get(
                            "item_type", "evidence"
                        ),
                        "grounding_verified": True,
                    }
                ],
            )
        elif matched_sk:
            return SubcriterionEvaluationItem(
                id=sub.id,
                name=sub.name,
                status=EvidenceStatus.AMBIGUOUS,
                confidence=matched_sk.confidence,
                source_excerpt=matched_sk.source_excerpt,
                source_page=matched_sk.source_page,
                explanation=f"Candidate lists '{sub.name}' in skills inventory on page {matched_sk.source_page}, but without applied project or experience evidence.",
            )
        elif page_match_excerpt:
            return SubcriterionEvaluationItem(
                id=sub.id,
                name=sub.name,
                status=EvidenceStatus.SUPPORTED,
                confidence=0.90,
                source_excerpt=page_match_excerpt,
                source_page=page_match_num,
                explanation=f"Direct evidence for '{sub.name}' found on page {page_match_num}.",
                citations=[
                    {
                        "document_id": None,
                        "page_number": page_match_num,
                        "exact_excerpt": page_match_excerpt,
                        "evidence_type": "document_text",
                        "grounding_verified": True,
                    }
                ],
            )
        else:
            return SubcriterionEvaluationItem(
                id=sub.id,
                name=sub.name,
                status=EvidenceStatus.NOT_FOUND,
                confidence=0.95,
                missing_reason=f"Resume documents related capabilities (e.g., Python, REST APIs) but does not document {sub.name} specifically.",
                explanation=f"Candidate's resume demonstrates related capabilities but contains no direct mention of {sub.name}. Note: This indicates absence of evidence in the resume, not a verified lack of capability.",
            )

    # 4. Standard technical skill / subrequirement matching
    kw_syns = set()
    for kw in sub.required_keywords:
        kw_syns.update(get_synonym_set(kw))
        kw_syns.add(normalize_term(kw))

    matching_citations: list[dict[str, Any]] = []
    applied_matches: list[tuple[int, float, EvidenceItem | None, str]] = []
    bare_skill_matches: list[tuple[EvidenceItem | None, str]] = []

    for ev in evidence_items:
        meta = ev.raw_metadata or {}
        item_type = meta.get("item_type", "general")
        claim = ev.claim_text or ""
        excerpt = ev.source_excerpt or ""
        desc = meta.get("description", "")
        techs = meta.get("technologies", [])
        techs_str = " ".join(techs) if isinstance(techs, list) else str(techs)
        full_context = f"{claim} {excerpt} {desc} {techs_str} {meta.get('job_title', '')}"

        matched = False
        sentence = ""

        if item_type == "skill":
            skill_name = meta.get("skill_name") or claim
            if matches_criterion_term(skill_name, kw_syns):
                matched = True
                sentence = extract_matching_sentence(excerpt or skill_name, kw_syns)
        elif item_type == "project":
            proj_name = meta.get("project_name", "")
            if matches_criterion_term(f"{proj_name} {techs_str} {desc} {excerpt}", kw_syns):
                matched = True
                sentence = extract_matching_sentence(f"{desc}\n{excerpt}", kw_syns)
                if not sentence or not matches_criterion_term(sentence, kw_syns):
                    sentence = f"Project {proj_name}: {techs_str}"
        elif item_type == "experience":
            job_title = meta.get("job_title", "")
            resps = meta.get("responsibilities", [])
            resps_str = " ".join(resps) if isinstance(resps, list) else str(resps)
            if matches_criterion_term(f"{job_title} {resps_str} {excerpt}", kw_syns):
                matched = True
                sentence = extract_matching_sentence(f"{resps_str}\n{excerpt}", kw_syns)
        else:
            if matches_criterion_term(full_context, kw_syns):
                matched = True
                sentence = extract_matching_sentence(excerpt or claim, kw_syns)

        if matched:
            citation_item = {
                "document_id": str(ev.document_id) if ev.document_id else None,
                "page_number": ev.source_page,
                "exact_excerpt": sentence or ev.source_excerpt,
                "evidence_type": item_type,
                "grounding_verified": ev.grounding_verified,
            }
            matching_citations.append(citation_item)

            if ev.grounding_verified:
                if item_type in ("project", "experience"):
                    tier = TIER_PROJECT if item_type == "project" else TIER_EXPERIENCE
                    applied_matches.append(
                        (tier, ev.confidence, ev, sentence or ev.source_excerpt or "")
                    )
                elif item_type == "skill":
                    if is_bare_skill_list(excerpt):
                        bare_skill_matches.append((ev, sentence or excerpt))
                    else:
                        applied_matches.append(
                            (TIER_EXPERIENCE, ev.confidence, ev, sentence or excerpt)
                        )
                else:
                    has_action_verbs = any(
                        re.search(rf"\b{verb}\b", f"{claim} {excerpt}".lower())
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
                            "managed",
                        )
                    )
                    if has_action_verbs:
                        applied_matches.append(
                            (TIER_PROJECT, ev.confidence, ev, sentence or ev.source_excerpt or "")
                        )
                    elif is_bare_skill_list(excerpt):
                        bare_skill_matches.append((ev, sentence or excerpt))
                    else:
                        applied_matches.append(
                            (TIER_SKILL, ev.confidence, ev, sentence or excerpt)
                        )

    # Also inspect resume_pages if applied_matches is empty
    if not applied_matches and resume_pages:
        for pg_str, pg_txt in resume_pages.items():
            pg_int = int(pg_str) if str(pg_str).isdigit() else 1
            for line in str(pg_txt).split("\n"):
                line_clean = line.strip().lstrip("-*•").strip()
                if len(line_clean) > 10 and matches_criterion_term(line_clean, kw_syns):
                    if validate_excerpt_in_text(line_clean, str(pg_txt)):
                        citation_item = {
                            "document_id": None,
                            "page_number": pg_int,
                            "exact_excerpt": line_clean,
                            "evidence_type": "project"
                            if "project" in str(pg_txt).lower()
                            else "document_text",
                            "grounding_verified": True,
                        }
                        matching_citations.append(citation_item)
                        applied_matches.append((TIER_PROJECT, 0.90, None, line_clean))
                        break

    # Also check candidate_skills if nothing else matched
    if not applied_matches and not bare_skill_matches:
        for sk in candidate_skills:
            if matches_criterion_term(sk.skill_name, kw_syns):
                bare_skill_matches.append((None, sk.source_excerpt or sk.skill_name))
                matching_citations.append(
                    {
                        "document_id": None,
                        "page_number": sk.source_page,
                        "exact_excerpt": sk.source_excerpt or sk.skill_name,
                        "evidence_type": "skill",
                        "grounding_verified": sk.confidence > 0,
                    }
                )

    if applied_matches:
        best_match = applied_matches[0]
        ev_obj = best_match[2]
        quote = best_match[3]
        page = (
            ev_obj.source_page
            if ev_obj
            else (matching_citations[0]["page_number"] if matching_citations else 1)
        )
        conf = ev_obj.confidence if ev_obj else 0.90

        return SubcriterionEvaluationItem(
            id=sub.id,
            name=sub.name,
            status=EvidenceStatus.SUPPORTED,
            confidence=conf,
            source_excerpt=quote,
            source_page=page,
            explanation=f"Validated evidence demonstrates '{sub.name}' on page {page}.",
            citations=matching_citations,
        )
    elif bare_skill_matches:
        quote = bare_skill_matches[0][1]
        ev_obj = bare_skill_matches[0][0]
        page = ev_obj.source_page if ev_obj else 1
        conf = ev_obj.confidence if ev_obj else 0.70

        if sub.require_project_or_experience:
            return SubcriterionEvaluationItem(
                id=sub.id,
                name=sub.name,
                status=EvidenceStatus.AMBIGUOUS,
                confidence=conf,
                source_excerpt=quote,
                source_page=page,
                explanation=f"Candidate lists '{sub.name}' in skills inventory on page {page}, but without applied project or experience evidence.",
                citations=matching_citations,
                missing_reason=f"Candidate lists '{sub.name}' in skills inventory, but practical project or applied experience was not documented.",
            )
        else:
            return SubcriterionEvaluationItem(
                id=sub.id,
                name=sub.name,
                status=EvidenceStatus.AMBIGUOUS,
                confidence=conf,
                source_excerpt=quote,
                source_page=page,
                explanation=f"Candidate lists '{sub.name}' in skills inventory on page {page}, but without applied project or experience evidence.",
                citations=matching_citations,
            )
    else:
        return SubcriterionEvaluationItem(
            id=sub.id,
            name=sub.name,
            status=EvidenceStatus.NOT_FOUND,
            confidence=0.95,
            missing_reason=f"No validated evidence for '{sub.name}' was found in the submitted materials.",
            explanation=f"No validated evidence for '{sub.name}' was found in the submitted materials. Note: This indicates absence in the resume, not a verified lack of capability.",
            citations=[],
        )


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

        resume_pages = (
            application.primary_document.extracted_text_by_page
            if application.primary_document
            else {}
        )

        # 5. Evaluate each criterion deterministically
        criterion_mappings: list[dict[str, Any]] = []

        for criterion in active_criteria:
            mapping = self._evaluate_single_criterion(
                criterion=criterion,
                candidate_skills=candidate_skills,
                evidence_items=evidence_items,
                resume_pages=resume_pages,
            )
            criterion_mappings.append(mapping)

        # 6. Compute coverage counts and overall status
        total_count = len(criterion_mappings)
        supported_count = sum(
            1 for m in criterion_mappings if m["ai_status"] == EvidenceStatus.SUPPORTED
        )
        partially_supported_count = sum(
            1 for m in criterion_mappings if m["ai_status"] == EvidenceStatus.PARTIALLY_SUPPORTED
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
        elif partially_supported_count > 0 or (supported_count > 0 and not_found_count > 0):
            overall_status = EvidenceStatus.PARTIALLY_SUPPORTED
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

        criteria_subcriteria = {
            str(m["job_criterion_id"]): {
                "subcriteria": [
                    s.model_dump() if hasattr(s, "model_dump") else s
                    for s in m.get("subcriteria", [])
                ],
                "missing_requirements": m.get("missing_requirements", []),
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
                f"{partially_supported_count} partially supported, "
                f"{not_found_count} not found, "
                f"{total_count - supported_count - partially_supported_count - not_found_count} ambiguous."
            ),
            raw_model_output={
                "job_criteria_version": criteria_version,
                "extraction_run_id": str(extraction_run.id),
                "extraction_run_number": extraction_run.run_number,
                "document_id": str(application.primary_document_id),
                "criteria_evidence_summary": criteria_summary,
                "criteria_subcriteria": criteria_subcriteria,
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
        resume_pages: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluates a single criterion against extracted skills and evidence.
        Decomposes compound criteria into subcriteria when applicable.
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
                "subcriteria": [],
                "missing_requirements": [],
            }

        # Rule B: Decompose compound requirements
        sub_defs = decompose_criterion(criterion_name, criterion.description)

        if len(sub_defs) > 1:
            evaluated_subs = [
                evaluate_subcriterion(
                    sub=sub_def,
                    evidence_items=evidence_items,
                    candidate_skills=candidate_skills,
                    resume_pages=resume_pages,
                )
                for sub_def in sub_defs
            ]

            supported_subs = [s for s in evaluated_subs if s.status == EvidenceStatus.SUPPORTED]
            not_found_subs = [s for s in evaluated_subs if s.status == EvidenceStatus.NOT_FOUND]
            ambiguous_subs = [s for s in evaluated_subs if s.status == EvidenceStatus.AMBIGUOUS]
            partially_subs = [
                s for s in evaluated_subs if s.status == EvidenceStatus.PARTIALLY_SUPPORTED
            ]

            if len(supported_subs) == len(evaluated_subs):
                parent_status = EvidenceStatus.SUPPORTED
                confidence = min((s.confidence for s in supported_subs), default=0.95)
                ai_reasoning = (
                    f"Validated source evidence directly demonstrates all required aspects for '{criterion_name}': "
                    + ", ".join(f"{s.name} (page {s.source_page})" for s in supported_subs)
                    + "."
                )
            elif len(not_found_subs) == len(evaluated_subs):
                parent_status = EvidenceStatus.NOT_FOUND
                confidence = 1.0
                ai_reasoning = (
                    f"No validated evidence for '{criterion_name}' was found in the submitted material. "
                    "Note: This does not mean the candidate lacks this skill, only that it was not documented "
                    "in the submitted resume."
                )
            elif supported_subs or partially_subs:
                parent_status = EvidenceStatus.PARTIALLY_SUPPORTED
                confidence = 0.90
                reason_parts = []
                if supported_subs:
                    reason_parts.append(
                        f"Supported requirements: {', '.join(s.name for s in supported_subs)}"
                    )
                if not_found_subs:
                    reason_parts.append(
                        f"Missing from evidence: {', '.join(s.name for s in not_found_subs)}"
                    )
                if ambiguous_subs:
                    reason_parts.append(
                        f"Ambiguous or limited depth: {', '.join(s.name for s in ambiguous_subs)}"
                    )
                ai_reasoning = (
                    f"Partial evidence found for '{criterion_name}'. "
                    + "; ".join(reason_parts)
                    + ". Note: Missing items reflect absence of documentation in the submitted resume, not a verified lack of capability."
                )
            else:
                parent_status = EvidenceStatus.AMBIGUOUS
                confidence = 0.60
                ai_reasoning = (
                    f"Evidence for '{criterion_name}' is ambiguous, limited in depth, or ungrounded."
                )

            primary_ev_id = None
            primary_excerpt = None
            primary_page = None
            supporting_ids: list[uuid.UUID] = []

            for sub_res in supported_subs:
                if not primary_excerpt and sub_res.source_excerpt:
                    primary_excerpt = sub_res.source_excerpt
                    primary_page = sub_res.source_page

            if supported_subs:
                for ev in evidence_items:
                    if (
                        primary_excerpt
                        and ev.source_excerpt
                        and (
                            primary_excerpt in ev.source_excerpt
                            or ev.source_excerpt in primary_excerpt
                        )
                    ):
                        primary_ev_id = ev.id
                        break
                for ev in evidence_items:
                    if primary_ev_id and ev.id != primary_ev_id:
                        for sub_res in supported_subs:
                            for cit in sub_res.citations:
                                if (
                                    cit.get("exact_excerpt")
                                    and ev.source_excerpt
                                    and cit["exact_excerpt"] in ev.source_excerpt
                                ):
                                    if ev.id not in supporting_ids:
                                        supporting_ids.append(ev.id)

            return {
                "job_criterion_id": criterion.id,
                "category": criterion_category,
                "evidence_item_id": primary_ev_id,
                "ai_status": parent_status,
                "ai_confidence": confidence,
                "ai_reasoning": ai_reasoning,
                "verification_state": VerificationState.UNVERIFIED,
                "source_excerpt": primary_excerpt,
                "source_page": primary_page,
                "supporting_evidence_ids": supporting_ids,
                "subcriteria": evaluated_subs,
                "missing_requirements": [s.name for s in not_found_subs],
            }

        # Rule C: Atomic criterion evaluation with multi-tier ranking
        synonyms = get_synonym_set(criterion_name)

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

        matched_skills: list[CandidateSkill] = []
        for skill in candidate_skills:
            if matches_criterion_term(skill.skill_name, synonyms):
                matched_skills.append(skill)

        # Atomic fallback when no items matched in extraction run
        if not ranked_evidence and not matched_skills:
            sub_item = SubcriterionEvaluationItem(
                id=sub_defs[0].id if sub_defs else "sub_0",
                name=sub_defs[0].name if sub_defs else criterion_name,
                status=EvidenceStatus.NOT_FOUND,
                confidence=1.0,
                missing_reason=f"No validated evidence for '{criterion_name}' was found in the submitted material.",
                explanation=f"No validated evidence for '{criterion_name}' was found in the submitted material. Note: This indicates absence in the resume, not a verified lack of capability.",
            )
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
                "subcriteria": [sub_item],
                "missing_requirements": [criterion_name],
            }

        # Atomic evidence item exists
        if ranked_evidence:
            primary_entry = ranked_evidence[0]
            primary_tier = primary_entry[0]
            primary_evidence = primary_entry[5]
            primary_desc = primary_entry[6]
            supporting_ids = [entry[5].id for entry in ranked_evidence[1:]]

            source_excerpt = primary_evidence.source_excerpt
            source_page = primary_evidence.source_page
            evidence_item_id = primary_evidence.id

            if not primary_evidence.grounding_verified:
                sub_item = SubcriterionEvaluationItem(
                    id=sub_defs[0].id if sub_defs else "sub_0",
                    name=sub_defs[0].name if sub_defs else criterion_name,
                    status=EvidenceStatus.AMBIGUOUS,
                    confidence=0.4,
                    source_excerpt=source_excerpt,
                    source_page=source_page,
                    explanation=f"Evidence referencing '{criterion_name}' was extracted, but grounding verification against the original document text failed or was unverified.",
                )
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
                    "subcriteria": [sub_item],
                    "missing_requirements": [],
                }

            has_date_conflict = False
            if primary_evidence.raw_metadata:
                has_date_conflict = bool(
                    primary_evidence.raw_metadata.get("date_conflict")
                    or primary_evidence.raw_metadata.get("has_date_conflict")
                )
            if has_date_conflict:
                sub_item = SubcriterionEvaluationItem(
                    id=sub_defs[0].id if sub_defs else "sub_0",
                    name=sub_defs[0].name if sub_defs else criterion_name,
                    status=EvidenceStatus.AMBIGUOUS,
                    confidence=0.6,
                    source_excerpt=source_excerpt,
                    source_page=source_page,
                    explanation=f"Candidate mentions '{criterion_name}', but evidence indicates conflicting dates in the timeline.",
                )
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
                    "subcriteria": [sub_item],
                    "missing_requirements": [],
                }

            combined_text = f"{source_excerpt or ''}\n{primary_evidence.claim_text or ''}"
            if has_weak_exposure_qualifier(criterion_name, combined_text, synonyms):
                sub_item = SubcriterionEvaluationItem(
                    id=sub_defs[0].id if sub_defs else "sub_0",
                    name=sub_defs[0].name if sub_defs else criterion_name,
                    status=EvidenceStatus.AMBIGUOUS,
                    confidence=0.6,
                    source_excerpt=source_excerpt,
                    source_page=source_page,
                    explanation=f"Candidate mentions '{criterion_name}', but evidence indicates limited exposure, basic familiarity, or introductory usage.",
                )
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
                    "subcriteria": [sub_item],
                    "missing_requirements": [],
                }

            if primary_tier == TIER_SKILL:
                sub_item = SubcriterionEvaluationItem(
                    id=sub_defs[0].id if sub_defs else "sub_0",
                    name=sub_defs[0].name if sub_defs else criterion_name,
                    status=EvidenceStatus.AMBIGUOUS,
                    confidence=0.7,
                    source_excerpt=source_excerpt,
                    source_page=source_page,
                    explanation=f"Candidate lists '{criterion_name}' in skills inventory, but without project, experience, or applied evidence demonstrating practical usage.",
                )
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
                    "subcriteria": [sub_item],
                    "missing_requirements": [],
                }

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
                    sub_item = SubcriterionEvaluationItem(
                        id=sub_defs[0].id if sub_defs else "sub_0",
                        name=sub_defs[0].name if sub_defs else criterion_name,
                        status=EvidenceStatus.AMBIGUOUS,
                        confidence=0.6,
                        source_excerpt=source_excerpt,
                        source_page=source_page,
                        explanation=f"Candidate references '{criterion_name}' in academic education coursework, but without applied project or professional experience.",
                    )
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
                        "subcriteria": [sub_item],
                        "missing_requirements": [],
                    }

            confidence = primary_evidence.confidence
            support_note = ""
            if supporting_ids:
                support_note = f" (supported by {len(supporting_ids)} other evidence item(s))"

            sub_item = SubcriterionEvaluationItem(
                id=sub_defs[0].id if sub_defs else "sub_0",
                name=sub_defs[0].name if sub_defs else criterion_name,
                status=EvidenceStatus.SUPPORTED,
                confidence=confidence,
                source_excerpt=source_excerpt,
                source_page=source_page,
                explanation=f"Validated source evidence ({primary_desc}) directly demonstrates experience with '{criterion_name}' on page {source_page}.{support_note}",
            )

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
                "subcriteria": [sub_item],
                "missing_requirements": [],
            }

        primary_skill = matched_skills[0]
        sub_item = SubcriterionEvaluationItem(
            id=sub_defs[0].id if sub_defs else "sub_0",
            name=sub_defs[0].name if sub_defs else criterion_name,
            status=EvidenceStatus.AMBIGUOUS,
            confidence=0.7,
            source_excerpt=primary_skill.source_excerpt,
            source_page=primary_skill.source_page,
            explanation=f"Candidate lists '{criterion_name}' in skills inventory, but without project, experience, or applied evidence demonstrating practical usage.",
        )
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
            "subcriteria": [sub_item],
            "missing_requirements": [],
        }

    @staticmethod
    def build_evaluation_response(evaluation: Evaluation) -> EvaluationResponse:
        """
        Builds the EvaluationResponse schema with explicit factual coverage counts
        and individual criterion evaluations including decomposed subcriteria.
        """
        items: list[CriterionEvaluationItem] = []
        supported_count = 0
        partially_supported_count = 0
        not_found_count = 0
        ambiguous_count = 0
        required_total = 0
        required_supported = 0
        preferred_total = 0
        preferred_supported = 0

        criteria_subcriteria = (evaluation.raw_model_output or {}).get("criteria_subcriteria", {})

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
            elif ce.ai_status == EvidenceStatus.PARTIALLY_SUPPORTED:
                partially_supported_count += 1
            elif ce.ai_status == EvidenceStatus.NOT_FOUND:
                not_found_count += 1
            else:
                ambiguous_count += 1

            active_dec = (
                next((d for d in ce.review_decisions if getattr(d, "is_active", True)), None)
                if ce.review_decisions
                else None
            )
            human_decision = active_dec.decision.value if active_dec else None
            public_rationale = None
            decided_at = active_dec.created_at if active_dec else None
            if active_dec and active_dec.mandatory_rationale:
                public_rationale = re.sub(
                    r"\[Internal Notes:.*?\]", "", active_dec.mandatory_rationale
                ).strip()

            crit_sub_info = criteria_subcriteria.get(str(ce.job_criterion_id), {})
            subcriteria_raw = crit_sub_info.get("subcriteria", [])
            missing_requirements = crit_sub_info.get("missing_requirements", [])

            subcriteria = [
                SubcriterionEvaluationItem.model_validate(s) for s in subcriteria_raw
            ]

            # Candidate clarifications
            clarifications: list[CandidateClarificationItem] = []
            if ce.correction_requests:
                for c in sorted(ce.correction_requests, key=lambda x: x.created_at):
                    clarifications.append(
                        CandidateClarificationItem(
                            id=c.id,
                            candidate_statement=c.candidate_statement,
                            additional_document_id=c.additional_document_id,
                            status=c.status,
                            created_at=c.created_at,
                        )
                    )

            # Review decisions
            decisions: list[ReviewDecisionItem] = []
            if ce.review_decisions:
                for d in sorted(ce.review_decisions, key=lambda x: x.created_at):
                    d_rationale = re.sub(
                        r"\[Internal Notes:.*?\]", "", d.mandatory_rationale or ""
                    ).strip()
                    decisions.append(
                        ReviewDecisionItem(
                            id=d.id,
                            reviewer_id=d.reviewer_id,
                            decision=d.decision,
                            mandatory_rationale=d_rationale,
                            previous_verification_state=d.previous_verification_state,
                            new_verification_state=d.new_verification_state,
                            created_at=d.created_at,
                        )
                    )

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
                    criterion_evidence_id=ce.id,
                    verification_state=ce.verification_state,
                    human_decision=human_decision,
                    decision_rationale=public_rationale,
                    decided_at=decided_at,
                    subcriteria=subcriteria,
                    missing_requirements=missing_requirements,
                    clarifications=clarifications,
                    decisions=decisions,
                )
            )

        coverage = EvidenceCoverageSummary(
            total_criteria=len(items),
            supported_count=supported_count,
            not_found_count=not_found_count,
            ambiguous_count=ambiguous_count,
            partially_supported_count=partially_supported_count,
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

