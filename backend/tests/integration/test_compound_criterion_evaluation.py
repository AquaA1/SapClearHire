import uuid
from typing import Any
import pypdf
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, UserRole
from app.db.models.application import Application
from app.db.models.document import CandidateSkill, Document, EvidenceItem, ExtractionRun
from app.db.models.enums import (
    ApplicationStatus,
    DocumentProcessingStatus,
    EvidenceStatus,
    VerificationState,
)
from app.db.models.job import Job, JobCriterion
from app.db.models.user import User
from app.services.evaluation import (
    EvaluationService,
    SubcriterionDefinition,
    decompose_criterion,
    evaluate_subcriterion,
)
from app.services.extraction import AIExtractionService
from app.integrations.llm.fake import FakeLLMProvider


async def setup_test_environment(
    session: AsyncSession,
    criteria_specs: list[tuple[str, str]],
    document_pages: dict[str, Any] | None = None,
) -> tuple[User, User, Job, Document, ExtractionRun, Application]:
    candidate_id = uuid.uuid4()
    employer_id = uuid.uuid4()

    candidate = User(
        id=candidate_id,
        email=f"cand_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Riya Sharma",
        role=UserRole.CANDIDATE,
    )
    employer = User(
        id=employer_id,
        email=f"emp_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Employer Admin",
        role=UserRole.EMPLOYER_ADMIN,
    )
    session.add_all([candidate, employer])
    await session.flush()

    job = Job(
        id=uuid.uuid4(),
        employer_id=employer_id,
        title="Backend Software Engineer",
        department="Platform Engineering",
    )
    session.add(job)
    await session.flush()

    for name, cat in criteria_specs:
        criterion = JobCriterion(
            id=uuid.uuid4(),
            job_id=job.id,
            name=name,
            category=cat,
            version=1,
            is_active=True,
        )
        session.add(criterion)
    await session.flush()

    doc = Document(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        file_name="ClearHire_Test_Resume_Riya_Sharma.pdf",
        file_path="/fixtures/ClearHire_Test_Resume_Riya_Sharma.pdf",
        file_hash=uuid.uuid4().hex,
        mime_type="application/pdf",
        file_size_bytes=24500,
        page_count=1,
        extracted_text_by_page=document_pages or {},
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    session.add(doc)
    await session.flush()

    run = ExtractionRun(
        id=uuid.uuid4(),
        document_id=doc.id,
        run_number=1,
        provider="fake",
        model_name="test-model",
        status=DocumentProcessingStatus.COMPLETED,
    )
    session.add(run)
    await session.flush()

    app = Application(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_id=candidate_id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SUBMITTED,
    )
    session.add(app)
    await session.flush()

    return candidate, employer, job, doc, run, app


@pytest.mark.asyncio
async def test_1_exact_skill_matching(test_session: AsyncSession) -> None:
    """1. Exact skill matching: Python -> Python, PostgreSQL -> PostgreSQL."""
    _, _, job, doc, run, app = await setup_test_environment(
        test_session, [("Python", "required"), ("PostgreSQL", "required")]
    )

    ev_python = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Candidate possesses skill: Python",
        source_page=1,
        source_excerpt="Programming: Python, SQL, basic Java",
        confidence=0.99,
        grounding_verified=True,
        raw_metadata={"item_type": "skill", "skill_name": "Python"},
    )
    ev_postgres = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Candidate possesses skill: PostgreSQL",
        source_page=1,
        source_excerpt="Databases: PostgreSQL, SQLite",
        confidence=0.99,
        grounding_verified=True,
        raw_metadata={"item_type": "skill", "skill_name": "PostgreSQL"},
    )
    test_session.add_all([ev_python, ev_postgres])
    await test_session.flush()

    service = EvaluationService()
    evaluation = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(evaluation)

    assert len(response.criteria_evaluations) == 2
    for item in response.criteria_evaluations:
        assert item.status in (EvidenceStatus.SUPPORTED, EvidenceStatus.AMBIGUOUS)
        assert len(item.subcriteria) == 1
        assert item.subcriteria[0].name in ("Python", "PostgreSQL")


@pytest.mark.asyncio
async def test_2_skills_embedded_in_project_descriptions(test_session: AsyncSession) -> None:
    """2. Skills embedded in project descriptions: PostgreSQL tables and SQL queries."""
    _, _, job, doc, run, app = await setup_test_environment(
        test_session, [("SQL", "required")]
    )

    ev_proj = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Project: Student Expense Tracker",
        source_page=1,
        source_excerpt="Designed PostgreSQL tables for users, transactions, and categories; wrote SQL queries using joins, grouping, and aggregate functions.",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={
            "item_type": "project",
            "project_name": "Student Expense Tracker",
            "technologies": ["Python", "PostgreSQL", "Git"],
            "description": "Designed PostgreSQL tables for users, transactions, and categories; wrote SQL queries using joins, grouping, and aggregate functions.",
        },
    )
    test_session.add(ev_proj)
    await test_session.flush()

    service = EvaluationService()
    evaluation = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(evaluation)

    sql_eval = response.criteria_evaluations[0]
    assert sql_eval.status == EvidenceStatus.SUPPORTED
    assert "queries" in sql_eval.source_excerpt.lower() or "sql" in sql_eval.source_excerpt.lower()


@pytest.mark.asyncio
async def test_3_controlled_synonym_matching(test_session: AsyncSession) -> None:
    """3. Controlled synonym matching: PostgreSQL <-> Postgres, AsyncIO <-> asynchronous programming."""
    sub_postgres = SubcriterionDefinition(
        id="sub_pg", name="PostgreSQL Database", required_keywords=["postgresql"]
    )
    ev_item = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        claim_text="Experience with Postgres databases",
        source_page=1,
        source_excerpt="Administered Postgres clusters with replication",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={"item_type": "experience", "job_title": "Database Admin"},
    )
    res = evaluate_subcriterion(sub_postgres, [ev_item], [])
    assert res.status == EvidenceStatus.SUPPORTED

    sub_async = SubcriterionDefinition(
        id="sub_async", name="AsyncIO", required_keywords=["asyncio"]
    )
    ev_async = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        claim_text="Applied asynchronous programming in Python",
        source_page=1,
        source_excerpt="Implemented asynchronous programming pipelines using event loops",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={"item_type": "project", "project_name": "Async Worker"},
    )
    res_async = evaluate_subcriterion(sub_async, [ev_async], [])
    assert res_async.status == EvidenceStatus.SUPPORTED


def test_4_compound_criteria_decomposition() -> None:
    """4. Compound criteria decomposition: FastAPI, PostgreSQL Scaling, Production Python."""
    fastapi_subs = decompose_criterion("Experience in FastAPI")
    fastapi_names = [s.name for s in fastapi_subs]
    assert "Python Programming" in fastapi_names
    assert "REST API Development" in fastapi_names
    assert "FastAPI Framework" in fastapi_names

    pg_subs = decompose_criterion("PostgreSQL Scaling & Index Optimization")
    pg_names = [s.name for s in pg_subs]
    assert "PostgreSQL Database" in pg_names
    assert "PostgreSQL Table Design" in pg_names
    assert "SQL Query Experience" in pg_names
    assert "Database Scaling" in pg_names
    assert "Index Optimization" in pg_names

    prod_subs = decompose_criterion("2+ Years Production Python (FastAPI / AsyncIO)")
    prod_names = [s.name for s in prod_subs]
    assert "Python Programming" in prod_names
    assert "FastAPI Framework" in prod_names
    assert "AsyncIO / Asynchronous Programming" in prod_names
    assert any("Years" in n for n in prod_names)
    assert "Production Environment Experience" in prod_names


@pytest.mark.asyncio
async def test_5_partial_evidence_assessment(test_session: AsyncSession) -> None:
    """5. Partial evidence assessment: Criterion A, B, and C with Riya Sharma profile."""
    criteria_specs = [
        ("Experience in FastAPI", "required"),
        ("PostgreSQL Scaling & Index Optimization", "required"),
        ("Experience in PostgreSQL", "preferred"),
    ]
    _, _, job, doc, run, app = await setup_test_environment(test_session, criteria_specs)

    ev_tracker = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Project: Student Expense Tracker",
        source_page=1,
        source_excerpt="Built a command-line expense tracker in Python with create, update, delete, and monthly-summary features.\nDesigned PostgreSQL tables for users, transactions, and categories; wrote SQL queries using joins, grouping, and aggregate functions.",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={
            "item_type": "project",
            "project_name": "Student Expense Tracker",
            "technologies": ["Python", "PostgreSQL", "Git"],
            "description": "Designed PostgreSQL tables for users, transactions, and categories; wrote SQL queries using joins, grouping, and aggregate functions.",
        },
    )
    ev_api = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Project: Library Inventory API",
        source_page=1,
        source_excerpt="Created a small REST API in Python to manage books, borrowers, and issue records.\nUsed SQL statements to search records, enforce relationships, and generate inventory summaries.",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={
            "item_type": "project",
            "project_name": "Library Inventory API",
            "technologies": ["Python", "SQLite", "Git"],
            "description": "Created a small REST API in Python to manage books, borrowers, and issue records.",
        },
    )
    test_session.add_all([ev_tracker, ev_api])
    await test_session.flush()

    service = EvaluationService()
    evaluation = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(evaluation)

    eval_by_name = {item.criterion_name: item for item in response.criteria_evaluations}

    # Criterion A: Experience in FastAPI -> PARTIALLY_SUPPORTED
    crit_a = eval_by_name["Experience in FastAPI"]
    assert crit_a.status == EvidenceStatus.PARTIALLY_SUPPORTED
    sub_status_a = {s.name: s.status for s in crit_a.subcriteria}
    assert sub_status_a["Python Programming"] == EvidenceStatus.SUPPORTED
    assert sub_status_a["REST API Development"] == EvidenceStatus.SUPPORTED
    assert sub_status_a["FastAPI Framework"] == EvidenceStatus.NOT_FOUND
    assert "FastAPI Framework" in crit_a.missing_requirements

    # Criterion B: PostgreSQL Scaling & Index Optimization -> PARTIALLY_SUPPORTED
    crit_b = eval_by_name["PostgreSQL Scaling & Index Optimization"]
    assert crit_b.status == EvidenceStatus.PARTIALLY_SUPPORTED
    sub_status_b = {s.name: s.status for s in crit_b.subcriteria}
    assert sub_status_b["PostgreSQL Database"] == EvidenceStatus.SUPPORTED
    assert sub_status_b["PostgreSQL Table Design"] == EvidenceStatus.SUPPORTED
    assert sub_status_b["SQL Query Experience"] == EvidenceStatus.SUPPORTED
    assert sub_status_b["Database Scaling"] == EvidenceStatus.NOT_FOUND
    assert sub_status_b["Index Optimization"] == EvidenceStatus.NOT_FOUND
    assert "Database Scaling" in crit_b.missing_requirements
    assert "Index Optimization" in crit_b.missing_requirements

    # Criterion C: Experience in PostgreSQL -> SUPPORTED
    crit_c = eval_by_name["Experience in PostgreSQL"]
    assert crit_c.status == EvidenceStatus.SUPPORTED
    assert len(crit_c.missing_requirements) == 0


@pytest.mark.asyncio
async def test_6_negative_inference_fastapi_not_inferred_from_python_api(
    test_session: AsyncSession,
) -> None:
    """6. Negative inference guard: FastAPI is NEVER inferred merely from Python REST API."""
    sub_fastapi = SubcriterionDefinition(
        id="sub_fastapi",
        name="FastAPI Framework",
        required_keywords=["fastapi"],
        is_framework=True,
    )
    ev_api = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        claim_text="Project: Library Inventory API",
        source_page=1,
        source_excerpt="Created a small REST API in Python to manage books, borrowers, and issue records.",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={
            "item_type": "project",
            "project_name": "Library Inventory API",
            "technologies": ["Python", "SQLite"],
            "description": "Created a small REST API in Python to manage books, borrowers, and issue records.",
        },
    )
    res = evaluate_subcriterion(sub_fastapi, [ev_api], [])
    assert res.status == EvidenceStatus.NOT_FOUND
    assert "FastAPI Framework" in res.missing_reason
    assert "does not mean the candidate lacks" in res.explanation or "absence of evidence" in res.explanation


@pytest.mark.asyncio
async def test_7_academic_vs_professional_experience(test_session: AsyncSession) -> None:
    """7. Academic vs professional experience: Personal/academic projects do not satisfy production environments."""
    sub_prod = SubcriterionDefinition(
        id="sub_prod",
        name="Production Environment Experience",
        is_production=True,
    )
    ev_student_proj = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        claim_text="Project: Student Expense Tracker",
        source_page=1,
        source_excerpt="Built a command-line expense tracker in Python for academic testing.",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={
            "item_type": "project",
            "project_name": "Student Expense Tracker",
            "technologies": ["Python"],
        },
    )
    res = evaluate_subcriterion(sub_prod, [ev_student_proj], [])
    assert res.status == EvidenceStatus.NOT_FOUND
    assert "enterprise production" in res.missing_reason.lower() or "academic" in res.missing_reason.lower()


@pytest.mark.asyncio
async def test_8_experience_duration_honesty(test_session: AsyncSession) -> None:
    """8. Experience duration honesty: Multi-year criteria require documented professional experience."""
    sub_dur = SubcriterionDefinition(
        id="sub_dur",
        name="3+ Years Experience",
        is_duration=True,
        min_years=3.0,
    )
    ev_skill = CandidateSkill(
        id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        skill_name="Python",
        confidence=0.95,
        source_page=1,
        source_excerpt="Programming: Python",
    )
    res = evaluate_subcriterion(sub_dur, [], [ev_skill])
    assert res.status == EvidenceStatus.NOT_FOUND
    assert "3.0+" in res.missing_reason or "3" in res.missing_reason


@pytest.mark.asyncio
async def test_9_multiple_source_citations(test_session: AsyncSession) -> None:
    """9. Multiple source citations: Multiple quotes are linked to subcriteria."""
    sub_python = SubcriterionDefinition(
        id="sub_py",
        name="Python Programming",
        required_keywords=["python"],
    )
    ev1 = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        claim_text="Project: Student Expense Tracker",
        source_page=1,
        source_excerpt="Built a command-line expense tracker in Python",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={"item_type": "project", "project_name": "Expense Tracker", "technologies": ["Python"]},
    )
    ev2 = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        claim_text="Project: Library Inventory API",
        source_page=1,
        source_excerpt="Created a small REST API in Python to manage books",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={"item_type": "project", "project_name": "Library API", "technologies": ["Python"]},
    )
    res = evaluate_subcriterion(sub_python, [ev1, ev2], [])
    assert res.status == EvidenceStatus.SUPPORTED
    assert len(res.citations) == 2


@pytest.mark.asyncio
async def test_10_invalid_fabricated_citation_rejection(test_session: AsyncSession) -> None:
    """10. Citation validation: Quotes with grounding_verified=False are rejected as ungrounded."""
    sub_postgres = SubcriterionDefinition(
        id="sub_pg",
        name="PostgreSQL Database",
        required_keywords=["postgresql"],
    )
    ev_fake = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        claim_text="Candidate has PostgreSQL scaling experience",
        source_page=1,
        source_excerpt="Scaled PostgreSQL clusters to 10M queries per second across 5 continents",
        confidence=0.0,
        grounding_verified=False,
        raw_metadata={"item_type": "experience", "grounding_failure": "Fabricated quote"},
    )
    res = evaluate_subcriterion(sub_postgres, [ev_fake], [])
    assert res.status != EvidenceStatus.SUPPORTED


@pytest.mark.asyncio
async def test_11_riya_sharma_end_to_end_evaluation(test_session: AsyncSession) -> None:
    """11. Riya Sharma end-to-end evaluation using actual PDF text."""
    reader = pypdf.PdfReader("tests/fixtures/ClearHire_Test_Resume_Riya_Sharma.pdf")
    pages = {str(i + 1): page.extract_text() for i, page in enumerate(reader.pages)}

    criteria_specs = [
        ("Experience in FastAPI", "required"),
        ("PostgreSQL Scaling & Index Optimization", "required"),
        ("Experience in PostgreSQL", "required"),
    ]
    _, _, job, doc, run, app = await setup_test_environment(test_session, criteria_specs, document_pages=pages)

    provider = FakeLLMProvider()
    profile = await provider.extract_resume_profile(
        resume_pages={int(k): v for k, v in pages.items()},
        document_hash=doc.file_hash,
    )

    for proj in profile.projects:
        ev = EvidenceItem(
            id=uuid.uuid4(),
            extraction_run_id=run.id,
            document_id=doc.id,
            claim_text=f"Project: {proj.project_name}",
            source_page=proj.source_quote.page_number,
            source_excerpt=proj.source_quote.exact_excerpt,
            confidence=0.95,
            grounding_verified=True,
            raw_metadata={
                "item_type": "project",
                "project_name": proj.project_name,
                "technologies": proj.technologies,
                "description": proj.description,
            },
        )
        test_session.add(ev)

    for skill in profile.skills:
        cs = CandidateSkill(
            id=uuid.uuid4(),
            extraction_run_id=run.id,
            candidate_id=app.candidate_id,
            skill_name=skill.skill_name,
            confidence=skill.confidence,
            source_page=skill.source_quote.page_number,
            source_excerpt=skill.source_quote.exact_excerpt,
        )
        test_session.add(cs)

    await test_session.flush()

    service = EvaluationService()
    evaluation = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(evaluation)

    eval_by_name = {item.criterion_name: item for item in response.criteria_evaluations}

    # Verify Riya Sharma evaluations
    assert eval_by_name["Experience in FastAPI"].status == EvidenceStatus.PARTIALLY_SUPPORTED
    assert eval_by_name["PostgreSQL Scaling & Index Optimization"].status == EvidenceStatus.PARTIALLY_SUPPORTED
    assert eval_by_name["Experience in PostgreSQL"].status == EvidenceStatus.SUPPORTED

    # Verify coverage counts
    assert response.coverage.supported_count == 1
    assert response.coverage.partially_supported_count == 2
    assert response.coverage.not_found_count == 0


@pytest.mark.asyncio
async def test_12_candidate_reviewer_consistency(test_session: AsyncSession) -> None:
    """12. Candidate-reviewer consistency: Serialization contains identical subcriteria structure."""
    criteria_specs = [("Experience in FastAPI", "required")]
    _, _, job, doc, run, app = await setup_test_environment(test_session, criteria_specs)

    ev_proj = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Project: Library Inventory API",
        source_page=1,
        source_excerpt="Created a small REST API in Python",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={"item_type": "project", "project_name": "Library API", "technologies": ["Python"]},
    )
    test_session.add(ev_proj)
    await test_session.flush()

    service = EvaluationService()
    evaluation = await service.evaluate_application(app.id, session=test_session)

    # Employer / Reviewer view
    reviewer_response = EvaluationService.build_evaluation_response(evaluation)
    # Candidate view
    candidate_response = EvaluationService.build_evaluation_response(evaluation)

    assert reviewer_response.coverage.model_dump() == candidate_response.coverage.model_dump()
    assert len(reviewer_response.criteria_evaluations[0].subcriteria) == 3
    assert len(candidate_response.criteria_evaluations[0].subcriteria) == 3
    for r_sub, c_sub in zip(
        reviewer_response.criteria_evaluations[0].subcriteria,
        candidate_response.criteria_evaluations[0].subcriteria,
    ):
        assert r_sub.name == c_sub.name
        assert r_sub.status == c_sub.status
