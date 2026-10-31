import uuid

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import UserRole
from app.db.models.document import Document
from app.db.models.enums import DocumentProcessingStatus
from app.db.models.user import User
from app.integrations.llm.fake import FakeLLMProvider
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
