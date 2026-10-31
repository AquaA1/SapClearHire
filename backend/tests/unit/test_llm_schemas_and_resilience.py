import uuid

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import ValidationError
from app.core.security import UserRole
from app.db.models.document import Document
from app.db.models.enums import DocumentProcessingStatus
from app.db.models.user import User
from app.integrations.llm.fake import FakeLLMProvider
from app.integrations.llm.normalization import (
    normalize_llm_json_payload,
    parse_and_normalize_llm_json,
)
from app.integrations.llm.schemas import (
    CandidateClaim,
    EvidenceStatus,
    ExtractedCertification,
    ExtractedEducation,
    ExtractedExperience,
    ExtractedProject,
    ExtractedResumeProfile,
    ExtractedSkill,
    SourceQuote,
)
from app.services.extraction import AIExtractionService


def test_education_with_null_institution():
    """Education qualification with null institution parses cleanly without error."""
    raw = {
        "institution": None,
        "degree": "B.S.",
        "field_of_study": "Computer Science",
        "graduation_date": "2020",
        "source_quote": {
            "page_number": 1,
            "exact_excerpt": "B.S. in Computer Science (2020)",
        },
    }
    edu = ExtractedEducation.model_validate(raw)
    assert edu.institution is None
    assert edu.degree == "B.S."
    assert edu.field_of_study == "Computer Science"
    assert edu.graduation_date == "2020"
    assert edu.source_quote.page_number == 1


def test_education_missing_graduation_dates():
    """Education qualification with missing/null graduation date parses cleanly."""
    raw = {
        "institution": "University of California, Berkeley",
        "degree": "Master of Science",
        "field_of_study": "Information Systems",
        "graduation_date": None,
        "source_quote": {
            "page_number": 2,
            "exact_excerpt": "Master of Science in Information Systems - UC Berkeley",
        },
    }
    edu = ExtractedEducation.model_validate(raw)
    assert edu.institution == "University of California, Berkeley"
    assert edu.graduation_date is None
    assert edu.field_of_study == "Information Systems"


def test_missing_optional_experience_fields():
    """Experience with missing company, dates, or job title parses with valid defaults."""
    raw = {
        "job_title": None,
        "company": None,
        "start_date": None,
        "end_date": None,
        "is_current": True,
        "responsibilities": [],
        "source_quote": {
            "page_number": 1,
            "exact_excerpt": "Independent consultant working with distributed systems.",
        },
    }
    exp = ExtractedExperience.model_validate(raw)
    assert exp.job_title is None
    assert exp.company is None
    assert exp.start_date is None
    assert exp.end_date is None
    assert exp.is_current is True
    assert exp.responsibilities == []


def test_missing_project_descriptions():
    """Project with missing description and technologies parses with default values."""
    raw = {
        "project_name": "ClearHire",
        "description": None,
        "technologies": [],
        "source_quote": {
            "page_number": 1,
            "exact_excerpt": "ClearHire open source contributor.",
        },
    }
    proj = ExtractedProject.model_validate(raw)
    assert proj.project_name == "ClearHire"
    assert proj.description is None
    assert proj.technologies == []


def test_fully_populated_profile():
    """A comprehensive profile with all nested models and fields parses with 100% data retention."""
    raw = {
        "candidate_name": "John Doe",
        "skills": [
            {
                "skill_name": "Python",
                "category": "Programming Languages",
                "years_of_experience": 5.5,
                "confidence": 0.99,
                "source_quote": {
                    "page_number": 1,
                    "exact_excerpt": "5+ years of production Python development",
                },
            }
        ],
        "experiences": [
            {
                "job_title": "Lead Engineer",
                "company": "Acme Inc",
                "start_date": "2021-01",
                "end_date": "Present",
                "is_current": True,
                "responsibilities": ["Led architecture team", "Managed microservices"],
                "source_quote": {
                    "page_number": 1,
                    "exact_excerpt": "Lead Engineer at Acme Inc (2021-01 to Present)",
                },
            }
        ],
        "projects": [
            {
                "project_name": "Data Pipeline",
                "description": "High-throughput streaming ETL",
                "technologies": ["Kafka", "PostgreSQL", "FastAPI"],
                "source_quote": {
                    "page_number": 1,
                    "exact_excerpt": "Built high-throughput Kafka ETL pipeline",
                },
            }
        ],
        "education": [
            {
                "institution": "Stanford University",
                "degree": "B.S.",
                "field_of_study": "Computer Science",
                "graduation_date": "2020",
                "source_quote": {
                    "page_number": 1,
                    "exact_excerpt": "B.S. in Computer Science from Stanford University (2020)",
                },
            }
        ],
        "certifications": [
            {
                "certification_name": "AWS Certified Solutions Architect",
                "issuing_organization": "Amazon Web Services",
                "issue_date": "2022-03",
                "expiration_date": "2025-03",
                "credential_id": "AWS-12345",
                "source_quote": {
                    "page_number": 1,
                    "exact_excerpt": "AWS Certified Solutions Architect (Credential: AWS-12345)",
                },
            }
        ],
        "detected_conflicts": ["Overlapping full-time dates in 2022"],
    }
    profile = ExtractedResumeProfile.model_validate(raw)
    assert profile.candidate_name == "John Doe"
    assert len(profile.skills) == 1
    assert profile.skills[0].years_of_experience == 5.5
    assert len(profile.experiences) == 1
    assert profile.experiences[0].is_current is True
    assert len(profile.projects) == 1
    assert len(profile.education) == 1
    assert len(profile.certifications) == 1
    assert profile.certifications[0].credential_id == "AWS-12345"
    assert profile.detected_conflicts == ["Overlapping full-time dates in 2022"]


def test_invalid_types_in_genuinely_required_fields():
    """Genuinely required fields reject missing values, empty strings, and invalid constraints."""
    # 1. SourceQuote missing required page_number
    with pytest.raises(PydanticValidationError) as exc:
        SourceQuote.model_validate({"exact_excerpt": "Some excerpt"})
    assert "page_number" in str(exc.value)

    # 2. SourceQuote invalid page_number < 1
    with pytest.raises(PydanticValidationError) as exc:
        SourceQuote.model_validate({"page_number": 0, "exact_excerpt": "Excerpt"})
    assert "greater than or equal to 1" in str(exc.value)

    # 3. SourceQuote empty string exact_excerpt
    with pytest.raises(PydanticValidationError) as exc:
        SourceQuote.model_validate({"page_number": 1, "exact_excerpt": ""})
    assert "exact_excerpt" in str(exc.value)

    # 4. ExtractedSkill missing required skill_name
    with pytest.raises(PydanticValidationError) as exc:
        ExtractedSkill.model_validate(
            {
                "source_quote": {"page_number": 1, "exact_excerpt": "Excerpt"},
            }
        )
    assert "skill_name" in str(exc.value)

    # 5. ExtractedSkill empty skill_name
    with pytest.raises(PydanticValidationError) as exc:
        ExtractedSkill.model_validate(
            {
                "skill_name": "",
                "source_quote": {"page_number": 1, "exact_excerpt": "Excerpt"},
            }
        )
    assert "skill_name" in str(exc.value)

    # 6. ExtractedEducation missing required source_quote
    with pytest.raises(PydanticValidationError) as exc:
        ExtractedEducation.model_validate({"degree": "B.S."})
    assert "source_quote" in str(exc.value)

    # 7. CandidateClaim missing required fields
    with pytest.raises(PydanticValidationError) as exc:
        CandidateClaim.model_validate({"claim_id": "c1", "status": EvidenceStatus.SUPPORTED})
    assert "criterion_name" in str(exc.value)


@pytest.mark.asyncio
async def test_extraction_service_with_nullable_fields_and_evidence_grounding(
    test_engine,
):
    """
    End-to-end integration: Tests that extraction persistence succeeds when
    education has null institution, experience has null company, project has null description,
    and ungrounded claims are rejected with grounding_verified=False and confidence 0.0.
    """
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    candidate_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    resume_p1 = (
        "Alice Smith. B.S. in Computer Science (2020).\n"
        "Lead Engineer at Acme Inc (2021 - Present).\n"
        "Created Data Pipeline project.\n"
        "AWS Certified Solutions Architect."
    )

    async with session_factory() as session:
        user = User(
            id=candidate_id,
            email=f"{candidate_id}@example.com",
            full_name="Alice Smith",
            role=UserRole.CANDIDATE,
        )
        doc = Document(
            id=doc_id,
            candidate_id=candidate_id,
            file_name="alice_resilience.pdf",
            file_path="/storage/alice_resilience.pdf",
            file_hash="mock_hash_resilience",
            file_size_bytes=2048,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            extracted_text_by_page={"1": resume_p1},
        )
        session.add(user)
        session.add(doc)
        await session.commit()

    # Profile containing null fields and one ungrounded excerpt
    profile = ExtractedResumeProfile(
        candidate_name="Alice Smith",
        skills=[
            ExtractedSkill(
                skill_name="Python",
                category=None,
                years_of_experience=None,
                confidence=0.9,
                source_quote=SourceQuote(
                    page_number=1,
                    exact_excerpt="Invented Excerpt Not in Resume",
                ),
            )
        ],
        experiences=[
            ExtractedExperience(
                job_title="Lead Engineer",
                company=None,
                start_date="2021",
                end_date="Present",
                is_current=True,
                responsibilities=[],
                source_quote=SourceQuote(
                    page_number=1,
                    exact_excerpt="Lead Engineer at Acme Inc (2021 - Present)",
                ),
            )
        ],
        projects=[
            ExtractedProject(
                project_name="Data Pipeline",
                description=None,
                technologies=[],
                source_quote=SourceQuote(
                    page_number=1,
                    exact_excerpt="Created Data Pipeline project.",
                ),
            )
        ],
        education=[
            ExtractedEducation(
                institution=None,  # Real failure reproduced: null institution
                degree="B.S.",
                field_of_study="Computer Science",
                graduation_date=None,
                source_quote=SourceQuote(
                    page_number=1,
                    exact_excerpt="B.S. in Computer Science (2020)",
                ),
            )
        ],
        certifications=[
            ExtractedCertification(
                certification_name="AWS Certified Solutions Architect",
                issuing_organization=None,
                issue_date=None,
                expiration_date=None,
                credential_id=None,
                source_quote=SourceQuote(
                    page_number=1,
                    exact_excerpt="AWS Certified Solutions Architect.",
                ),
            )
        ],
    )

    fake_provider = FakeLLMProvider(custom_profile_override=profile)
    service = AIExtractionService(
        llm_provider=fake_provider,
        session_factory=session_factory,
    )

    run, skills, evidence = await service.extract_and_persist(doc_id)

    assert run.status == DocumentProcessingStatus.COMPLETED
    assert run.completed_at is not None
    assert run.error_message is None

    # Verify skill with ungrounded excerpt: grounding_verified is False, confidence is 0.0
    assert len(skills) == 1
    assert skills[0].confidence == 0.0

    skill_ev = next(e for e in evidence if "Python" in e.claim_text)
    assert skill_ev.grounding_verified is False
    assert skill_ev.confidence == 0.0
    assert skill_ev.source_excerpt == "Invented Excerpt Not in Resume"

    # Verify education with null institution: cleanly formatted without "None"
    edu_ev = next(e for e in evidence if "Education:" in e.claim_text)
    assert "None" not in edu_ev.claim_text
    assert "B.S. Computer Science" in edu_ev.claim_text
    assert edu_ev.grounding_verified is True
    assert edu_ev.confidence > 0.0

    # Verify experience with null company: cleanly formatted without "None"
    exp_ev = next(e for e in evidence if "Experience as" in e.claim_text)
    assert "None" not in exp_ev.claim_text
    assert "Lead Engineer" in exp_ev.claim_text
    assert exp_ev.grounding_verified is True

    # Verify project with null description: cleanly formatted
    proj_ev = next(e for e in evidence if "Project:" in e.claim_text)
    assert "Data Pipeline" in proj_ev.claim_text
    assert proj_ev.grounding_verified is True

    # Verify certification persisted
    cert_ev = next(e for e in evidence if "Certification:" in e.claim_text)
    assert "AWS Certified Solutions Architect" in cert_ev.claim_text
    assert cert_ev.grounding_verified is True


def test_education_institution_omitted_entirely():
    """Requirement 2: Education institution omitted entirely from JSON parses with None."""
    raw = {
        "degree": "Bachelor of Technology",
        "field_of_study": "Information Technology",
        "source_quote": {
            "page_number": 1,
            "exact_excerpt": "Bachelor of Technology in IT",
        },
    }
    edu = ExtractedEducation.model_validate(raw)
    assert edu.institution is None
    assert edu.degree == "Bachelor of Technology"
    assert edu.graduation_date is None


def test_missing_employment_organization():
    """Requirement 4: Missing employment organization / company name parses with None."""
    raw = {
        "job_title": "Independent Software Developer",
        "start_date": "2020-01",
        "end_date": "2022-06",
        "source_quote": {
            "page_number": 1,
            "exact_excerpt": "Independent Software Developer 2020-01 to 2022-06",
        },
    }
    exp = ExtractedExperience.model_validate(raw)
    assert exp.company is None
    assert exp.job_title == "Independent Software Developer"


def test_valid_normal_gemini_response():
    """Requirement 5: Valid normal Gemini response JSON string parses and normalizes cleanly."""
    json_str = """
    {
        "candidate_name": "Bob Vance",
        "skills": [
            {
                "skill_name": "Python",
                "category": "Languages",
                "years_of_experience": 4,
                "confidence": 0.95,
                "source_quote": {
                    "page_number": 1,
                    "exact_excerpt": "4 years experience developing backend Python APIs"
                }
            }
        ],
        "experiences": [
            {
                "job_title": "Backend Developer",
                "company": "Vance Refrigeration",
                "start_date": "2019",
                "end_date": "2023",
                "is_current": false,
                "responsibilities": ["Maintained inventory database"],
                "source_quote": {
                    "page_number": 1,
                    "exact_excerpt": "Backend Developer at Vance Refrigeration (2019-2023)"
                }
            }
        ],
        "projects": [],
        "education": [],
        "certifications": [],
        "detected_conflicts": []
    }
    """
    normalized = parse_and_normalize_llm_json(json_str)
    profile = ExtractedResumeProfile.model_validate(normalized)
    assert profile.candidate_name == "Bob Vance"
    assert len(profile.skills) == 1
    assert profile.skills[0].skill_name == "Python"
    assert profile.skills[0].confidence == 0.95
    assert len(profile.experiences) == 1
    assert profile.experiences[0].company == "Vance Refrigeration"


def test_json_inside_markdown_code_fences():
    """Requirement 6: JSON enclosed in Markdown code fences with surrounding commentary extracts cleanly."""
    fenced_str = """
    Here is the requested extraction result from the candidate document:

    ```json
    {
        "candidate_name": "Carol Danvers",
        "skills": [
            {
                "skill_name": "FastAPI",
                "category": "Frameworks",
                "years_of_experience": null,
                "confidence": null,
                "source_quote": {
                    "page_number": 1,
                    "exact_excerpt": "Built REST services with FastAPI"
                }
            }
        ],
        "experiences": null,
        "education": null,
        "certifications": null,
        "projects": null,
        "detected_conflicts": null
    }
    ```

    Please let me know if you need additional details.
    """
    normalized = parse_and_normalize_llm_json(fenced_str)
    profile = ExtractedResumeProfile.model_validate(normalized)
    assert profile.candidate_name == "Carol Danvers"
    assert len(profile.skills) == 1
    assert profile.skills[0].skill_name == "FastAPI"
    assert profile.skills[0].confidence == 1.0  # Normalized null confidence to default 1.0
    assert profile.experiences == []  # Normalized null list to []
    assert profile.education == []
    assert profile.certifications == []
    assert profile.projects == []
    assert profile.detected_conflicts == []


def test_invalid_json_handling():
    """Requirement 7: Malformed / unparseable JSON raises descriptive ValidationError."""
    bad_json = "This is plain text with no valid JSON brackets or keys."
    with pytest.raises(ValidationError) as exc_info:
        parse_and_normalize_llm_json(bad_json)
    assert "Invalid JSON" in str(exc_info.value) or "LLM output must be a JSON object" in str(
        exc_info.value
    )


def test_invalid_type_in_genuinely_required_field_normalizer():
    """Requirement 8: Normalizer does not fabricate required fields when types are invalid."""
    bad_payload = {
        "skills": [
            {
                "skill_name": "",  # Empty string rejected by min_length=1
                "source_quote": {
                    "page_number": "non_numeric_page",  # Cannot be coerced to int
                    "exact_excerpt": "Some excerpt",
                },
            }
        ]
    }
    normalized = normalize_llm_json_payload(bad_payload)
    with pytest.raises(PydanticValidationError) as exc_info:
        ExtractedResumeProfile.model_validate(normalized)
    assert "page_number" in str(exc_info.value) or "skill_name" in str(exc_info.value)


@pytest.mark.asyncio
async def test_correction_attempt_succeeds():
    """Requirement 9: Initial invalid JSON triggers controlled correction attempt which succeeds."""
    initial_broken = "```json\n{ candidate_name: unquoted }\n```"  # Malformed JSON
    valid_correction = """
    {
        "candidate_name": "Corrected Candidate",
        "skills": [
            {
                "skill_name": "PostgreSQL",
                "category": "Databases",
                "source_quote": {
                    "page_number": 1,
                    "exact_excerpt": "Designed schemas in PostgreSQL"
                }
            }
        ],
        "experiences": [],
        "education": [],
        "projects": [],
        "certifications": [],
        "detected_conflicts": []
    }
    """
    provider = FakeLLMProvider(
        raw_json_override=initial_broken,
        correction_response_raw=valid_correction,
    )
    profile = await provider.extract_resume_profile(
        resume_pages={1: "Designed schemas in PostgreSQL"},
        document_hash="test_hash",
    )
    assert provider.correction_attempt_called is True
    assert profile.candidate_name == "Corrected Candidate"
    assert len(profile.skills) == 1
    assert profile.skills[0].skill_name == "PostgreSQL"


@pytest.mark.asyncio
async def test_correction_attempt_fails():
    """Requirement 10: Correction attempt also returning invalid schema raises ValidationError and does not loop."""
    initial_broken = "{ invalid json"
    still_broken = "{ still invalid json"
    provider = FakeLLMProvider(
        raw_json_override=initial_broken,
        correction_response_raw=still_broken,
    )
    with pytest.raises(ValidationError) as exc_info:
        await provider.extract_resume_profile(
            resume_pages={1: "Sample text"},
            document_hash="test_hash",
        )
    assert provider.correction_attempt_called is True
    assert "LLM output violated profile schema" in str(exc_info.value)


@pytest.mark.asyncio
async def test_evidence_excerpts_source_text_validation(test_engine):
    """Requirement 11: Evidence excerpts undergo strict source-text verification without modifying excerpts."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    candidate_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    actual_resume_text = "Experienced Senior Python Engineer with 6 years experience."

    async with session_factory() as session:
        user = User(
            id=candidate_id,
            email=f"{candidate_id}@example.com",
            full_name="Source Test User",
            role=UserRole.CANDIDATE,
        )
        doc = Document(
            id=doc_id,
            candidate_id=candidate_id,
            file_name="source_test.pdf",
            file_path="/storage/source_test.pdf",
            file_hash="mock_source_hash",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            extracted_text_by_page={"1": actual_resume_text},
        )
        session.add(user)
        session.add(doc)
        await session.commit()

    profile = ExtractedResumeProfile(
        skills=[
            # 1. Grounded excerpt
            ExtractedSkill(
                skill_name="Python",
                source_quote=SourceQuote(
                    page_number=1,
                    exact_excerpt="Senior Python Engineer with 6 years experience.",
                ),
            ),
            # 2. Hallucinated / ungrounded excerpt
            ExtractedSkill(
                skill_name="Kubernetes",
                source_quote=SourceQuote(
                    page_number=1,
                    exact_excerpt="Deployed clusters to GCP using Kubernetes Helm charts.",
                ),
            ),
        ]
    )

    provider = FakeLLMProvider(custom_profile_override=profile)
    service = AIExtractionService(llm_provider=provider, session_factory=session_factory)
    run, skills, evidence = await service.extract_and_persist(doc_id)

    assert run.status == DocumentProcessingStatus.COMPLETED
    py_skill = next(s for s in skills if s.skill_name == "Python")
    k8s_skill = next(s for s in skills if s.skill_name == "Kubernetes")

    # Python is grounded
    assert py_skill.confidence > 0.0
    py_ev = next(e for e in evidence if "Python" in e.claim_text)
    assert py_ev.grounding_verified is True
    assert py_ev.confidence > 0.0

    # Kubernetes is ungrounded
    assert k8s_skill.confidence == 0.0
    k8s_ev = next(e for e in evidence if "Kubernetes" in e.claim_text)
    assert k8s_ev.grounding_verified is False
    assert k8s_ev.confidence == 0.0
    assert "Excerpt not found in source page text" in k8s_ev.raw_metadata["grounding_failure"]


@pytest.mark.asyncio
async def test_extraction_run_status_persisted_completed_and_failed(test_engine):
    """Requirement 12: ExtractionRun status is correctly committed to DB as COMPLETED or FAILED."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    candidate_id = uuid.uuid4()
    doc_success_id = uuid.uuid4()
    doc_fail_id = uuid.uuid4()

    async with session_factory() as session:
        user = User(
            id=candidate_id,
            email=f"{candidate_id}@example.com",
            full_name="Persistence User",
            role=UserRole.CANDIDATE,
        )
        doc1 = Document(
            id=doc_success_id,
            candidate_id=candidate_id,
            file_name="success.pdf",
            file_path="/storage/success.pdf",
            file_hash="hash_success",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            extracted_text_by_page={"1": "Software Engineer with Python skills."},
        )
        doc2 = Document(
            id=doc_fail_id,
            candidate_id=candidate_id,
            file_name="failure.pdf",
            file_path="/storage/failure.pdf",
            file_hash="hash_failure",
            file_size_bytes=1024,
            mime_type="application/pdf",
            processing_status=DocumentProcessingStatus.COMPLETED,
            page_count=1,
            extracted_text_by_page={"1": "Corrupted or unparseable input."},
        )
        session.add(user)
        session.add(doc1)
        session.add(doc2)
        await session.commit()

    # Success case
    good_provider = FakeLLMProvider()
    good_service = AIExtractionService(llm_provider=good_provider, session_factory=session_factory)
    good_run, _, _ = await good_service.extract_and_persist(doc_success_id)
    assert good_run.status == DocumentProcessingStatus.COMPLETED
    assert good_run.error_message is None

    # Failure case
    bad_provider = FakeLLMProvider(
        raw_json_override="{ invalid json",
        correction_response_raw="{ still invalid json",
    )
    bad_service = AIExtractionService(llm_provider=bad_provider, session_factory=session_factory)
    with pytest.raises(ValidationError):
        await bad_service.extract_and_persist(doc_fail_id)

    # Verify persisted in database as FAILED
    from app.repositories.domain import ExtractionRepository

    async with session_factory() as session:
        ext_repo = ExtractionRepository(session)
        latest_run = await ext_repo.get_latest_run_for_document(doc_fail_id)
        assert latest_run is not None
        assert latest_run.status == DocumentProcessingStatus.FAILED
        assert latest_run.error_message is not None
        assert "LLM output violated profile schema" in latest_run.error_message
