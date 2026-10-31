import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UserRole
from app.db.models.application import Application
from app.db.models.document import Document, EvidenceItem, ExtractionRun
from app.db.models.enums import ApplicationStatus, DocumentProcessingStatus, EvidenceStatus
from app.db.models.job import Job, JobCriterion
from app.db.models.user import User
from app.services.evaluation import EvaluationService


async def create_base_entities(
    session: AsyncSession, criteria_names: list[tuple[str, str]]
) -> tuple[User, Job, list[JobCriterion], Document, ExtractionRun, Application]:
    cand_id = uuid.uuid4()
    emp_id = uuid.uuid4()

    cand = User(
        id=cand_id,
        email=f"cand-{cand_id}@example.com",
        full_name="Candidate",
        role=UserRole.CANDIDATE,
    )
    emp = User(
        id=emp_id,
        email=f"emp-{emp_id}@example.com",
        full_name="Employer",
        role=UserRole.EMPLOYER_ADMIN,
    )
    session.add_all([cand, emp])
    await session.flush()

    job = Job(id=uuid.uuid4(), employer_id=emp_id, title="Software Engineer")
    session.add(job)
    await session.flush()

    criteria = []
    for name, cat in criteria_names:
        crit = JobCriterion(
            id=uuid.uuid4(), job_id=job.id, name=name, category=cat, weight=1.0, version=1
        )
        session.add(crit)
        criteria.append(crit)

    doc = Document(
        id=uuid.uuid4(),
        candidate_id=cand_id,
        file_name="resume.pdf",
        file_path="/tmp/res.pdf",
        file_hash=f"hash-{uuid.uuid4().hex[:8]}",
        file_size_bytes=1000,
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    session.add(doc)
    await session.flush()

    run = ExtractionRun(
        id=uuid.uuid4(),
        document_id=doc.id,
        run_number=1,
        provider="fake",
        model_name="fake-model",
        status=DocumentProcessingStatus.COMPLETED,
    )
    session.add(run)
    await session.flush()

    app = Application(
        id=uuid.uuid4(),
        job_id=job.id,
        candidate_id=cand_id,
        primary_document_id=doc.id,
        status=ApplicationStatus.SUBMITTED,
    )
    session.add(app)
    await session.flush()

    return cand, job, criteria, doc, run, app


@pytest.mark.asyncio
async def test_case_1_qualifier_isolation_python_sql_basic_java(test_session: AsyncSession) -> None:
    _, _, criteria, doc, run, app = await create_base_entities(
        test_session, [("Python", "required"), ("SQL", "required"), ("Java", "required")]
    )

    ev_python = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Candidate possesses skill: Python",
        source_page=1,
        source_excerpt="Programming: Python, SQL, basic Java",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={"item_type": "skill", "skill_name": "Python"},
    )
    ev_sql = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Candidate possesses skill: SQL",
        source_page=1,
        source_excerpt="Programming: Python, SQL, basic Java",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={"item_type": "skill", "skill_name": "SQL"},
    )
    ev_java = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Candidate possesses skill: Java",
        source_page=1,
        source_excerpt="Programming: Python, SQL, basic Java",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={"item_type": "skill", "skill_name": "Java"},
    )
    test_session.add_all([ev_python, ev_sql, ev_java])
    await test_session.flush()

    service = EvaluationService()
    eval_res = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(eval_res)

    by_name = {item.criterion_name: item for item in response.criteria_evaluations}

    # Python & SQL must not inherit basic
    assert "basic familiarity" not in by_name["Python"].plain_language_explanation.lower()
    assert "limited exposure" not in by_name["Python"].plain_language_explanation.lower()
    assert "basic familiarity" not in by_name["SQL"].plain_language_explanation.lower()
    assert "limited exposure" not in by_name["SQL"].plain_language_explanation.lower()

    # Java must reflect limited exposure / basic familiarity
    assert (
        "limited exposure" in by_name["Java"].plain_language_explanation.lower()
        or "basic familiarity" in by_name["Java"].plain_language_explanation.lower()
    )


@pytest.mark.asyncio
async def test_case_2_project_evidence_outranks_bare_skill(test_session: AsyncSession) -> None:
    _, _, criteria, doc, run, app = await create_base_entities(
        test_session, [("Python", "required")]
    )

    ev_skill = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Candidate possesses skill: Python",
        source_page=1,
        source_excerpt="Programming: Python, SQL",
        confidence=0.99,
        grounding_verified=True,
        raw_metadata={"item_type": "skill", "skill_name": "Python"},
    )
    ev_proj = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Project: Expense API",
        source_page=1,
        source_excerpt="Expense API · Built REST API in Python using FastAPI",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={
            "item_type": "project",
            "project_name": "Expense API",
            "technologies": ["Python", "FastAPI"],
            "description": "Built REST API in Python using FastAPI",
        },
    )
    test_session.add_all([ev_skill, ev_proj])
    await test_session.flush()

    service = EvaluationService()
    eval_res = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(eval_res)

    item = response.criteria_evaluations[0]
    assert item.evidence_item_id == ev_proj.id
    assert item.status == EvidenceStatus.SUPPORTED


@pytest.mark.asyncio
async def test_case_3_student_project_title_not_penalized(test_session: AsyncSession) -> None:
    _, _, criteria, doc, run, app = await create_base_entities(
        test_session, [("Python", "required")]
    )

    ev_proj = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Project: Student Expense Tracker",
        source_page=1,
        source_excerpt="Student Expense Tracker · Python, PostgreSQL · Built a CLI expense tracker in Python",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={
            "item_type": "project",
            "project_name": "Student Expense Tracker",
            "technologies": ["Python", "PostgreSQL"],
            "description": "Built a CLI expense tracker in Python",
        },
    )
    test_session.add(ev_proj)
    await test_session.flush()

    service = EvaluationService()
    eval_res = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(eval_res)

    item = response.criteria_evaluations[0]
    assert item.status == EvidenceStatus.SUPPORTED
    assert "limited exposure" not in item.plain_language_explanation.lower()


@pytest.mark.asyncio
async def test_case_4_cross_criterion_isolation(test_session: AsyncSession) -> None:
    _, _, criteria, doc, run, app = await create_base_entities(
        test_session, [("Python", "required"), ("SQL", "required")]
    )

    ev_py = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Candidate possesses skill: Python",
        source_page=1,
        source_excerpt="Programming: Python, SQL",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={"item_type": "skill", "skill_name": "Python"},
    )
    ev_sql = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Candidate possesses skill: SQL",
        source_page=1,
        source_excerpt="Programming: Python, SQL",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={"item_type": "skill", "skill_name": "SQL"},
    )
    test_session.add_all([ev_py, ev_sql])
    await test_session.flush()

    service = EvaluationService()
    eval_res = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(eval_res)

    by_name = {item.criterion_name: item for item in response.criteria_evaluations}
    assert by_name["Python"].evidence_item_id == ev_py.id
    assert by_name["SQL"].evidence_item_id == ev_sql.id
    assert by_name["SQL"].evidence_item_id != ev_py.id


@pytest.mark.asyncio
async def test_case_5_project_only_evidence_library_inventory_api(
    test_session: AsyncSession,
) -> None:
    _, _, criteria, doc, run, app = await create_base_entities(
        test_session, [("Python", "required"), ("SQL", "required")]
    )

    ev_proj = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Project: Library Inventory API",
        source_page=1,
        source_excerpt="Library Inventory API · Python, SQLite · Created a small REST API in Python to manage books. Used SQL statements to search records.",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={
            "item_type": "project",
            "project_name": "Library Inventory API",
            "technologies": ["Python", "SQLite"],
            "description": "Created a small REST API in Python to manage books. Used SQL statements to search records.",
        },
    )
    test_session.add(ev_proj)
    await test_session.flush()

    service = EvaluationService()
    eval_res = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(eval_res)

    by_name = {item.criterion_name: item for item in response.criteria_evaluations}
    assert by_name["Python"].status == EvidenceStatus.SUPPORTED
    assert by_name["SQL"].status == EvidenceStatus.SUPPORTED


@pytest.mark.asyncio
async def test_case_6_bare_skill_list_git_ambiguous(test_session: AsyncSession) -> None:
    _, _, criteria, doc, run, app = await create_base_entities(test_session, [("Git", "preferred")])

    ev_git = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Candidate possesses skill: Git",
        source_page=1,
        source_excerpt="Tools: Git, GitHub, VS Code, Linux",
        confidence=1.0,
        grounding_verified=True,
        raw_metadata={"item_type": "skill", "skill_name": "Git"},
    )
    test_session.add(ev_git)
    await test_session.flush()

    service = EvaluationService()
    eval_res = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(eval_res)

    item = response.criteria_evaluations[0]
    assert item.status == EvidenceStatus.AMBIGUOUS
    assert item.confidence < 1.0


@pytest.mark.asyncio
async def test_case_7_relevant_git_project_evidence_supported(test_session: AsyncSession) -> None:
    _, _, criteria, doc, run, app = await create_base_entities(test_session, [("Git", "preferred")])

    ev_skill = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Candidate possesses skill: Git",
        source_page=1,
        source_excerpt="Tools: Git, GitHub, VS Code, Linux",
        confidence=1.0,
        grounding_verified=True,
        raw_metadata={"item_type": "skill", "skill_name": "Git"},
    )
    ev_proj = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Project: Expense Tracker",
        source_page=1,
        source_excerpt="Used Git branches and commits to track changes and maintained a GitHub repository for the project.",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={
            "item_type": "project",
            "project_name": "Expense Tracker",
            "technologies": ["Python", "Git"],
            "description": "Used Git branches and commits to track changes and maintained a GitHub repository for the project.",
        },
    )
    test_session.add_all([ev_skill, ev_proj])
    await test_session.flush()

    service = EvaluationService()
    eval_res = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(eval_res)

    item = response.criteria_evaluations[0]
    assert item.status == EvidenceStatus.SUPPORTED
    assert item.evidence_item_id == ev_proj.id


@pytest.mark.asyncio
async def test_case_8_irrelevant_education_does_not_falsely_support(
    test_session: AsyncSession,
) -> None:
    _, _, criteria, doc, run, app = await create_base_entities(
        test_session, [("Python", "required"), ("SQL", "required")]
    )

    ev_edu = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Education: Bachelor of Technology Computer Science",
        source_page=1,
        source_excerpt="Bachelor of Technology — Computer Science at Example Institute of Technology",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={
            "item_type": "education",
            "institution": "Example Institute of Technology",
            "degree": "Bachelor of Technology",
            "field_of_study": "Computer Science",
        },
    )
    test_session.add(ev_edu)
    await test_session.flush()

    service = EvaluationService()
    eval_res = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(eval_res)

    by_name = {item.criterion_name: item for item in response.criteria_evaluations}
    assert by_name["Python"].status == EvidenceStatus.NOT_FOUND
    assert by_name["SQL"].status == EvidenceStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_case_9_multiple_evidence_project_ranks_above_earlier_bare_skill(
    test_session: AsyncSession,
) -> None:
    _, _, criteria, doc, run, app = await create_base_entities(
        test_session, [("Python", "required")]
    )

    ev_skill = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Candidate possesses skill: Python",
        source_page=1,
        source_excerpt="Programming: Python, SQL",
        confidence=1.0,
        grounding_verified=True,
        raw_metadata={"item_type": "skill", "skill_name": "Python"},
    )
    ev_proj = EvidenceItem(
        id=uuid.uuid4(),
        extraction_run_id=run.id,
        document_id=doc.id,
        claim_text="Project: Data Pipeline",
        source_page=2,
        source_excerpt="Data Pipeline · Developed distributed Python worker nodes",
        confidence=0.95,
        grounding_verified=True,
        raw_metadata={
            "item_type": "project",
            "project_name": "Data Pipeline",
            "technologies": ["Python"],
            "description": "Developed distributed Python worker nodes",
        },
    )
    test_session.add_all([ev_skill, ev_proj])
    await test_session.flush()

    service = EvaluationService()
    eval_res = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(eval_res)

    item = response.criteria_evaluations[0]
    assert item.evidence_item_id == ev_proj.id
    assert item.status == EvidenceStatus.SUPPORTED


@pytest.mark.asyncio
async def test_case_10_not_found_criterion_preserved(test_session: AsyncSession) -> None:
    _, _, criteria, doc, run, app = await create_base_entities(test_session, [("Ruby", "required")])

    service = EvaluationService()
    eval_res = await service.evaluate_application(app.id, session=test_session)
    response = EvaluationService.build_evaluation_response(eval_res)

    item = response.criteria_evaluations[0]
    assert item.status == EvidenceStatus.NOT_FOUND
    assert item.confidence == 1.0
    assert "No validated evidence for 'Ruby' was found" in item.plain_language_explanation
    assert "This does not mean the candidate lacks this skill" in item.plain_language_explanation
