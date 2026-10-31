import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import logger
from app.db.models.document import CandidateSkill, EvidenceItem, ExtractionRun
from app.db.models.enums import DocumentProcessingStatus
from app.db.session import get_session_factory
from app.integrations.llm import BaseLLMProvider, get_llm_provider
from app.integrations.llm.schemas import ExtractedResumeProfile
from app.repositories.domain import DocumentRepository, ExtractionRepository
from app.utils.text import (
    detect_date_conflicts,
    detect_prompt_injection_indicators,
    validate_excerpt_in_text,
)


class AIExtractionService:
    """
    Orchestrates LLM-based structured evidence extraction, rigorous source grounding,
    prompt injection defense, deduplication, conflict detection, and immutable persistence.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        self.llm_provider = llm_provider or get_llm_provider()
        self.session_factory = session_factory or get_session_factory()

    async def extract_and_persist(
        self,
        document_id: uuid.UUID,
        run_id: uuid.UUID | None = None,
    ) -> tuple[ExtractionRun, list[CandidateSkill], list[EvidenceItem]]:
        """
        Runs the full AI extraction pipeline on a document:
        1. Loads document and page-preserved extracted text.
        2. Detects prompt injection patterns in raw text.
        3. Invokes LLM provider with defensive XML wrapping.
        4. Validates each source quote against original page text without modifying excerpts.
        5. Performs deduplication and detects chronological / claim conflicts.
        6. Persists ExtractionRun, CandidateSkill, and EvidenceItem records.
        """
        # Step 1: Fetch document & initialize or update run to PROCESSING
        async with self.session_factory() as session:
            doc_repo = DocumentRepository(session)
            doc = await doc_repo.get_by_id(document_id)
            if not doc:
                raise ValueError(f"Document {document_id} not found")

            candidate_id = doc.candidate_id
            document_hash = doc.file_hash
            raw_pages_raw = doc.extracted_text_by_page or {}
            # Ensure integer keys
            resume_pages: dict[int, str] = {int(k): str(v) for k, v in raw_pages_raw.items()}

            if not resume_pages:
                raise ValueError(f"Document {document_id} contains no extracted page text")

            ext_repo = ExtractionRepository(session)
            if run_id:
                run = await ext_repo.get_by_id(run_id)
                if not run:
                    raise ValueError(f"Extraction run {run_id} not found")
                run.status = DocumentProcessingStatus.PROCESSING
                run.started_at = datetime.now(UTC)
                await session.commit()
            else:
                provider_name = getattr(self.llm_provider, "provider_name", "fake")
                model_name = getattr(self.llm_provider, "model_name", "default")
                run = await ext_repo.create_extraction_run(
                    document_id=document_id,
                    provider=provider_name,
                    model_name=model_name,
                    status=DocumentProcessingStatus.PROCESSING,
                )
                run_id = run.id
                await session.commit()

        try:
            # Step 2: Detect prompt injection attempts in raw input
            injection_flags: list[str] = []
            for p_num, p_text in resume_pages.items():
                flags = detect_prompt_injection_indicators(p_text)
                for f in flags:
                    injection_flags.append(f"Page {p_num}: {f}")

            if injection_flags:
                logger.warning(
                    "Prompt injection indicator(s) detected in document %s: %s",
                    document_id,
                    injection_flags,
                )

            # Step 3: Invoke LLM extraction
            profile = await self.llm_provider.extract_resume_profile(
                resume_pages=resume_pages,
                document_hash=document_hash,
            )
            if not isinstance(profile, ExtractedResumeProfile):
                raise ValueError(f"Invalid profile type returned by provider: {type(profile)}")

            # Step 4 & 5: Validate, Deduplicate, Detect Conflicts, and Persist
            async with self.session_factory() as session:
                ext_repo = ExtractionRepository(session)
                persisted_skills: list[CandidateSkill] = []
                persisted_evidence: list[EvidenceItem] = []

                # Deduplication trackers
                seen_skill_names: set[str] = set()
                seen_evidence_keys: set[tuple[str, int]] = set()

                # Process Skills
                for skill in profile.skills:
                    norm_name = skill.skill_name.strip().lower()
                    is_duplicate = norm_name in seen_skill_names
                    seen_skill_names.add(norm_name)

                    # Grounding validation
                    page_text = resume_pages.get(skill.source_quote.page_number, "")
                    is_grounded = validate_excerpt_in_text(
                        excerpt=skill.source_quote.exact_excerpt,
                        target_text=page_text,
                    )

                    metadata: dict[str, Any] = {
                        "item_type": "skill",
                        "skill_name": skill.skill_name,
                        "category": skill.category,
                        "years_of_experience": skill.years_of_experience,
                        "is_duplicate": is_duplicate,
                    }
                    if not is_grounded:
                        metadata["grounding_failure"] = "Excerpt not found in source page text"
                        logger.warning(
                            "Skill '%s' excerpt failed source grounding validation on page %d",
                            skill.skill_name,
                            skill.source_quote.page_number,
                        )

                    if injection_flags:
                        metadata["prompt_injection_flags"] = injection_flags

                    # Persist EvidenceItem
                    ev_item = await ext_repo.add_evidence_item(
                        extraction_run_id=run_id,
                        document_id=document_id,
                        claim_text=f"Candidate possesses skill: {skill.skill_name}",
                        source_page=skill.source_quote.page_number,
                        source_excerpt=skill.source_quote.exact_excerpt,
                        confidence=skill.confidence if is_grounded else 0.0,
                        grounding_verified=is_grounded,
                        raw_metadata=metadata,
                    )
                    persisted_evidence.append(ev_item)

                    # Persist CandidateSkill (confidence is 0.0 if ungrounded)
                    cand_skill = await ext_repo.add_candidate_skill(
                        extraction_run_id=run_id,
                        candidate_id=candidate_id,
                        skill_name=skill.skill_name,
                        category=skill.category,
                        confidence=skill.confidence if is_grounded else 0.0,
                        source_page=skill.source_quote.page_number,
                        source_excerpt=skill.source_quote.exact_excerpt,
                    )
                    persisted_skills.append(cand_skill)

                # Process Experiences
                for exp in profile.experiences:
                    page_text = resume_pages.get(exp.source_quote.page_number, "")
                    is_grounded = validate_excerpt_in_text(
                        excerpt=exp.source_quote.exact_excerpt,
                        target_text=page_text,
                    )

                    # Date Conflict Checking
                    date_conflict = detect_date_conflicts(exp.start_date, exp.end_date)

                    ev_key = (
                        f"{exp.job_title or ''}_{exp.company or ''}".lower(),
                        exp.source_quote.page_number,
                    )
                    is_duplicate = ev_key in seen_evidence_keys
                    seen_evidence_keys.add(ev_key)

                    metadata = {
                        "item_type": "experience",
                        "job_title": exp.job_title,
                        "company": exp.company,
                        "start_date": exp.start_date,
                        "end_date": exp.end_date,
                        "is_current": exp.is_current,
                        "responsibilities": exp.responsibilities,
                        "is_duplicate": is_duplicate,
                    }
                    if date_conflict:
                        metadata["date_conflict"] = date_conflict
                        logger.warning("Experience date conflict detected: %s", date_conflict)

                    if not is_grounded:
                        metadata["grounding_failure"] = "Excerpt not found in source page text"
                        logger.warning(
                            "Experience '%s' excerpt failed source grounding validation on page %d",
                            exp.job_title or "unspecified role",
                            exp.source_quote.page_number,
                        )

                    if injection_flags:
                        metadata["prompt_injection_flags"] = injection_flags

                    exp_confidence = (0.95 if not date_conflict else 0.5) if is_grounded else 0.0
                    role_str = exp.job_title or "Unspecified role"
                    company_str = f" at {exp.company}" if exp.company else ""
                    dates_str = (
                        f" ({exp.start_date or ''} - {exp.end_date or ''})".strip()
                        if (exp.start_date or exp.end_date)
                        else ""
                    )
                    ev_item = await ext_repo.add_evidence_item(
                        extraction_run_id=run_id,
                        document_id=document_id,
                        claim_text=f"Experience as {role_str}{company_str}{dates_str}",
                        source_page=exp.source_quote.page_number,
                        source_excerpt=exp.source_quote.exact_excerpt,
                        confidence=exp_confidence,
                        grounding_verified=is_grounded,
                        raw_metadata=metadata,
                    )
                    persisted_evidence.append(ev_item)

                # Process Projects
                for proj in profile.projects:
                    page_text = resume_pages.get(proj.source_quote.page_number, "")
                    is_grounded = validate_excerpt_in_text(
                        excerpt=proj.source_quote.exact_excerpt,
                        target_text=page_text,
                    )

                    metadata = {
                        "item_type": "project",
                        "project_name": proj.project_name,
                        "description": proj.description,
                        "technologies": proj.technologies,
                    }
                    if not is_grounded:
                        metadata["grounding_failure"] = "Excerpt not found in source page text"

                    proj_name = proj.project_name or "Unspecified project"
                    ev_item = await ext_repo.add_evidence_item(
                        extraction_run_id=run_id,
                        document_id=document_id,
                        claim_text=f"Project: {proj_name}",
                        source_page=proj.source_quote.page_number,
                        source_excerpt=proj.source_quote.exact_excerpt,
                        confidence=0.95 if is_grounded else 0.0,
                        grounding_verified=is_grounded,
                        raw_metadata=metadata,
                    )
                    persisted_evidence.append(ev_item)

                # Process Education
                for edu in profile.education:
                    page_text = resume_pages.get(edu.source_quote.page_number, "")
                    is_grounded = validate_excerpt_in_text(
                        excerpt=edu.source_quote.exact_excerpt,
                        target_text=page_text,
                    )

                    metadata = {
                        "item_type": "education",
                        "institution": edu.institution,
                        "degree": edu.degree,
                        "field_of_study": edu.field_of_study,
                        "graduation_date": edu.graduation_date,
                    }
                    if not is_grounded:
                        metadata["grounding_failure"] = "Excerpt not found in source page text"

                    degree_part = f"{edu.degree or ''} {edu.field_of_study or ''}".strip()
                    degree_desc = degree_part if degree_part else "Education credential"
                    inst_part = f" at {edu.institution}" if edu.institution else ""
                    date_part = f" ({edu.graduation_date})" if edu.graduation_date else ""
                    claim_text = f"Education: {degree_desc}{inst_part}{date_part}"

                    ev_item = await ext_repo.add_evidence_item(
                        extraction_run_id=run_id,
                        document_id=document_id,
                        claim_text=claim_text,
                        source_page=edu.source_quote.page_number,
                        source_excerpt=edu.source_quote.exact_excerpt,
                        confidence=0.95 if is_grounded else 0.0,
                        grounding_verified=is_grounded,
                        raw_metadata=metadata,
                    )
                    persisted_evidence.append(ev_item)

                # Process Certifications
                for cert in profile.certifications:
                    page_text = resume_pages.get(cert.source_quote.page_number, "")
                    is_grounded = validate_excerpt_in_text(
                        excerpt=cert.source_quote.exact_excerpt,
                        target_text=page_text,
                    )

                    metadata = {
                        "item_type": "certification",
                        "certification_name": cert.certification_name,
                        "issuing_organization": cert.issuing_organization,
                        "issue_date": cert.issue_date,
                        "expiration_date": cert.expiration_date,
                        "credential_id": cert.credential_id,
                    }
                    if not is_grounded:
                        metadata["grounding_failure"] = "Excerpt not found in source page text"

                    cert_name = cert.certification_name or "Certification"
                    org_part = (
                        f" from {cert.issuing_organization}" if cert.issuing_organization else ""
                    )
                    claim_text = f"Certification: {cert_name}{org_part}"

                    ev_item = await ext_repo.add_evidence_item(
                        extraction_run_id=run_id,
                        document_id=document_id,
                        claim_text=claim_text,
                        source_page=cert.source_quote.page_number,
                        source_excerpt=cert.source_quote.exact_excerpt,
                        confidence=0.95 if is_grounded else 0.0,
                        grounding_verified=is_grounded,
                        raw_metadata=metadata,
                    )
                    persisted_evidence.append(ev_item)

                # Finalize ExtractionRun
                completed_run = await ext_repo.complete_extraction_run(
                    extraction_run_id=run_id,
                    status=DocumentProcessingStatus.COMPLETED,
                    raw_output=profile.model_dump(),
                    error_message=None,
                )
                await session.commit()

                return completed_run, persisted_skills, persisted_evidence

        except Exception as exc:
            logger.exception(
                "AI extraction failed for document %s (run %s): %s", document_id, run_id, str(exc)
            )
            async with self.session_factory() as session:
                ext_repo = ExtractionRepository(session)
                await ext_repo.complete_extraction_run(
                    extraction_run_id=run_id,
                    status=DocumentProcessingStatus.FAILED,
                    raw_output={"error": str(exc)},
                    error_message=str(exc),
                )
                await session.commit()
            raise
