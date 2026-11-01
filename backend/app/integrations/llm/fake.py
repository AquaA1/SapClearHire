import re
import uuid

from app.core.exceptions import ValidationError
from app.integrations.llm.base import BaseLLMProvider
from app.integrations.llm.normalization import parse_and_normalize_llm_json
from app.integrations.llm.schemas import (
    CandidateClaim,
    EvidenceStatus,
    ExtractedEducation,
    ExtractedExperience,
    ExtractedProject,
    ExtractedResumeProfile,
    ExtractedSkill,
    ExtractionResult,
    SourceQuote,
)


class FakeLLMProvider(BaseLLMProvider):
    """
    Deterministic LLM provider for tests, local development, and offline evaluation.
    Matches criteria and extracts structured profiles (skills, experience, projects, education)
    with genuine or configurable test responses.
    """

    def __init__(
        self,
        provider_name: str = "fake",
        model_name: str = "deterministic-stub-v1",
        custom_profile_override: ExtractedResumeProfile | None = None,
        simulate_error: Exception | None = None,
        raw_json_override: str | None = None,
        correction_response_raw: str | None = None,
    ):
        self.provider_name = provider_name
        self.model_name = model_name
        self.custom_profile_override = custom_profile_override
        self.simulate_error = simulate_error
        self.raw_json_override = raw_json_override
        self.correction_response_raw = correction_response_raw
        self.correction_attempt_called: bool = False

    async def extract_resume_profile(
        self,
        resume_pages: dict[int, str],
        document_hash: str,
    ) -> ExtractedResumeProfile:
        """
        Extracts structured skills, experiences, projects, and education deterministically
        from raw page text by looking for keywords and common structural patterns.
        """
        if self.simulate_error:
            raise self.simulate_error

        if self.raw_json_override is not None:
            try:
                normalized = parse_and_normalize_llm_json(self.raw_json_override)
                return ExtractedResumeProfile.model_validate(normalized)
            except Exception as initial_error:
                if self.correction_response_raw is not None:
                    self.correction_attempt_called = True
                    try:
                        corr_norm = parse_and_normalize_llm_json(self.correction_response_raw)
                        return ExtractedResumeProfile.model_validate(corr_norm)
                    except Exception as corr_error:
                        raise ValidationError(
                            f"LLM output violated profile schema: {str(corr_error)}"
                        ) from corr_error
                raise ValidationError(
                    f"LLM output violated profile schema: {str(initial_error)}"
                ) from initial_error

        if self.custom_profile_override is not None:
            return self.custom_profile_override

        skills: list[ExtractedSkill] = []
        experiences: list[ExtractedExperience] = []
        projects: list[ExtractedProject] = []
        education: list[ExtractedEducation] = []
        detected_conflicts: list[str] = []

        known_skill_keywords = [
            ("python", "Programming Languages"),
            ("fastapi", "Backend Frameworks"),
            ("postgresql", "Databases"),
            ("postgres", "Databases"),
            ("docker", "DevOps & Containers"),
            ("kubernetes", "DevOps & Orchestration"),
            ("k8s", "DevOps & Orchestration"),
            ("react", "Frontend Frameworks"),
            ("typescript", "Programming Languages"),
            ("aws", "Cloud Infrastructure"),
            ("sap", "Enterprise Software"),
            ("sql", "Databases"),
            ("git", "Developer Tools"),
            ("rest api", "API Concepts"),
            ("sqlite", "Databases"),
        ]

        # Scan each page for skills
        for page_num, text in sorted(resume_pages.items()):
            for kw, category in known_skill_keywords:
                match = re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE)
                if match:
                    # Create window for excerpt
                    start_idx = max(0, match.start() - 25)
                    end_idx = min(len(text), match.end() + 35)
                    excerpt = text[start_idx:end_idx].strip()

                    # Extract years if nearby
                    years = None
                    years_match = re.search(
                        r"(\d+)\s*(?:\+?\s*)years?",
                        text[max(0, match.start() - 60) : min(len(text), match.end() + 60)],
                        re.IGNORECASE,
                    )
                    if years_match:
                        years = float(years_match.group(1))

                    skill_disp = (
                        kw.upper()
                        if kw.lower() in ("aws", "sql", "sap", "git")
                        else ("REST API" if kw.lower() == "rest api" else kw.capitalize())
                    )
                    skills.append(
                        ExtractedSkill(
                            skill_name=skill_disp,
                            category=category,
                            years_of_experience=years,
                            confidence=0.95,
                            source_quote=SourceQuote(
                                page_number=page_num,
                                exact_excerpt=excerpt,
                                start_char=start_idx,
                                end_char=end_idx,
                            ),
                        )
                    )

            # Heuristic detection for Projects
            proj_matches = list(
                re.finditer(
                    r"^([A-Za-z0-9][^\n·•-]{1,50}?)\s*[·•-]\s*([^\n·•-]+?)\s*[·•-]\s*([^\n]+)$",
                    text,
                    re.MULTILINE,
                )
            )
            for i, pm in enumerate(proj_matches):
                p_name = pm.group(1).strip()
                p_techs = [t.strip() for t in pm.group(2).split(",") if t.strip()]
                start_idx = pm.start()
                if i + 1 < len(proj_matches):
                    end_idx = proj_matches[i + 1].start()
                else:
                    next_sec = re.search(r"\n[A-Z\s]{4,}\n", text[pm.end() :])
                    end_idx = pm.end() + next_sec.start() if next_sec else min(len(text), pm.end() + 350)
                proj_excerpt = text[start_idx:end_idx].strip()

                projects.append(
                    ExtractedProject(
                        project_name=p_name,
                        technologies=p_techs,
                        description=proj_excerpt,
                        source_quote=SourceQuote(
                            page_number=page_num,
                            exact_excerpt=proj_excerpt,
                            start_char=start_idx,
                            end_char=end_idx,
                        ),
                    )
                )

            # Heuristic detection for Experience
            exp_matches = re.finditer(
                r"(?:Senior |Lead |Staff |Junior )?(?:Software|Backend|Full Stack|DevOps|Data|Systems)\s+(?:Engineer|Developer|Architect)",
                text,
                re.IGNORECASE,
            )
            for m in exp_matches:
                job_title = m.group(0)
                start_idx = max(0, m.start() - 10)
                end_idx = min(len(text), m.end() + 100)
                excerpt = text[start_idx:end_idx].strip()

                # Look for dates
                date_match = re.search(
                    r"((?:20\d\d|19\d\d)(?:-\d\d)?)\s*(?:-|to)\s*((?:20\d\d|19\d\d)(?:-\d\d)?|Present)",
                    excerpt,
                    re.IGNORECASE,
                )
                start_date = date_match.group(1) if date_match else "2021-01"
                end_date = date_match.group(2) if date_match else "Present"
                is_current = end_date.lower() == "present"

                experiences.append(
                    ExtractedExperience(
                        job_title=job_title,
                        company="TechCorp" if "techcorp" in text.lower() else "Enterprise Inc",
                        start_date=start_date,
                        end_date=end_date,
                        is_current=is_current,
                        responsibilities=[
                            "Designed and maintained scalable backend microservices."
                        ],
                        source_quote=SourceQuote(
                            page_number=page_num,
                            exact_excerpt=excerpt,
                            start_char=start_idx,
                            end_char=end_idx,
                        ),
                    )
                )

            # Heuristic detection for Education
            edu_matches = re.finditer(
                r"(?:B\.?S\.?|Bachelor|M\.?S\.?|Master|Ph\.?D\.?)\s+(?:of|in)?\s*(?:Computer Science|Software Engineering|Electrical Engineering)?",
                text,
                re.IGNORECASE,
            )
            for m in edu_matches:
                degree_text = m.group(0).strip()
                start_idx = max(0, m.start() - 20)
                end_idx = min(len(text), m.end() + 80)
                excerpt = text[start_idx:end_idx].strip()

                education.append(
                    ExtractedEducation(
                        institution="University of Technology"
                        if "university" not in text.lower()
                        else "Tech University",
                        degree=degree_text,
                        field_of_study="Computer Science",
                        graduation_date="2020",
                        source_quote=SourceQuote(
                            page_number=page_num,
                            exact_excerpt=excerpt,
                            start_char=start_idx,
                            end_char=end_idx,
                        ),
                    )
                )

        return ExtractedResumeProfile(
            candidate_name="Jane Candidate",
            skills=skills,
            experiences=experiences,
            projects=projects,
            education=education,
            detected_conflicts=detected_conflicts,
        )

    async def extract_claims(
        self,
        resume_pages: dict[int, str],
        criteria: list[str],
        document_hash: str,
    ) -> ExtractionResult:
        if self.simulate_error:
            raise self.simulate_error

        profile = await self.extract_resume_profile(resume_pages, document_hash)
        claims: list[CandidateClaim] = []

        for criterion in criteria:
            criterion_clean = criterion.strip().lower()
            found_quote: SourceQuote | None = None
            is_ambiguous = False

            # Search across pages in order
            for page_num, text in sorted(resume_pages.items()):
                match = re.search(re.escape(criterion_clean), text, re.IGNORECASE)
                if match:
                    start_idx = max(0, match.start() - 40)
                    end_idx = min(len(text), match.end() + 60)
                    excerpt = text[start_idx:end_idx].strip()

                    context_snippet = text[
                        max(0, match.start() - 100) : min(len(text), match.end() + 100)
                    ].lower()
                    if any(
                        term in context_snippet
                        for term in ["familiar with", "basic", "exposure", "learning"]
                    ):
                        is_ambiguous = True

                    found_quote = SourceQuote(
                        page_number=page_num,
                        exact_excerpt=excerpt,
                        start_char=start_idx,
                        end_char=end_idx,
                    )
                    break

            if found_quote and is_ambiguous:
                claims.append(
                    CandidateClaim(
                        claim_id=str(uuid.uuid4()),
                        criterion_name=criterion,
                        status=EvidenceStatus.AMBIGUOUS,
                        confidence=0.65,
                        source_quotes=[found_quote],
                        rationale=f"Found mention of '{criterion}' with qualifying language indicating limited depth.",
                    )
                )
            elif found_quote:
                claims.append(
                    CandidateClaim(
                        claim_id=str(uuid.uuid4()),
                        criterion_name=criterion,
                        status=EvidenceStatus.SUPPORTED,
                        confidence=0.95,
                        source_quotes=[found_quote],
                        rationale=f"Direct evidence found on page {found_quote.page_number}.",
                    )
                )
            else:
                claims.append(
                    CandidateClaim(
                        claim_id=str(uuid.uuid4()),
                        criterion_name=criterion,
                        status=EvidenceStatus.NOT_FOUND,
                        confidence=0.90,
                        source_quotes=[],
                        rationale=f"No direct evidence for '{criterion}' identified in uploaded document.",
                    )
                )

        return ExtractionResult(
            claims=claims,
            profile=profile,
            document_hash=document_hash,
            provider=self.provider_name,
            model_name=self.model_name,
            prompt_version="2026.1-defensive",
        )
