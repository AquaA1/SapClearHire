import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.core.security import CurrentUser, UserRole, get_current_user
from app.db.models.application import Application
from app.db.models.document import Document
from app.db.models.enums import DocumentProcessingStatus
from app.db.models.job import Job
from app.db.models.user import User
from app.db.session import get_db_session
from app.repositories.domain import DocumentRepository, ExtractionRepository, UserRepository
from app.schemas.document import (
    CandidateSkillSummary,
    DocumentStatusResponse,
    DocumentUploadResponse,
    EvidenceItemSummary,
    ExtractionRunResponse,
)
from app.services.document import DocumentService
from app.services.extraction import AIExtractionService

router = APIRouter(prefix="/documents", tags=["Documents"])


async def verify_document_access(
    doc: Document,
    current_user: CurrentUser,
    db: AsyncSession,
    write_access: bool = False,
) -> None:
    """
    Enforces strict tenant and ownership authorization on documents.
    - Candidates may only access their own documents.
    - Employer administrators and reviewers may only access documents linked to an application
      for a job requisition owned by their organization.
    - System auditors have read-only access and cannot trigger write operations.
    """
    if current_user.role == UserRole.CANDIDATE:
        if doc.candidate_id != uuid.UUID(current_user.id):
            raise AuthorizationError("You are not authorized to access this document")
        return

    if current_user.role == UserRole.SYSTEM_AUDITOR:
        if write_access:
            raise AuthorizationError("Auditors do not have permission to trigger extraction")
        return

    if current_user.role in (UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER):
        stmt = (
            select(Application)
            .options(selectinload(Application.job).selectinload(Job.creator))
            .where(Application.primary_document_id == doc.id)
        )
        res = await db.execute(stmt)
        apps = res.scalars().all()

        authorized = False
        for app in apps:
            if app.job:
                is_creator = str(app.job.employer_id) == current_user.id
                org_matches = bool(
                    current_user.employer_id
                    and app.job.creator
                    and app.job.creator.employer_id == current_user.employer_id
                )
                if is_creator or org_matches:
                    authorized = True
                    break

        if not authorized:
            raise AuthorizationError(
                "You are not authorized to access documents outside your organization"
            )
        return

    raise AuthorizationError("You are not authorized to access this document")


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload Candidate Resume",
    description=(
        "Uploads a PDF resume, validates format and size, stores it securely, "
        "and enqueues background text extraction without blocking."
    ),
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF resume file to upload"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    candidate_id = uuid.UUID(current_user.id)

    # Ensure user record exists for database foreign key integrity
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(candidate_id)
    if not user:
        user = User(
            id=candidate_id,
            email=current_user.email,
            full_name=current_user.email.split("@")[0],
            role=current_user.role,
            employer_id=current_user.employer_id,
        )
        db.add(user)
        await db.flush()

    service = DocumentService()
    doc = await service.create_and_store_document(
        file=file,
        candidate_id=candidate_id,
        session=db,
    )

    # Persist document to DB before scheduling background processing
    await db.commit()
    await db.refresh(doc)

    # Schedule background extraction task
    background_tasks.add_task(
        service.process_document_extraction,
        doc.id,
    )

    return DocumentUploadResponse.model_validate(doc)


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Poll Document Extraction Status",
    description="Retrieves the processing status, page count, and extracted text per page.",
)
async def get_document_status(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentStatusResponse:
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(document_id)

    if not doc:
        raise NotFoundError(f"Document {document_id} was not found")

    await verify_document_access(doc, current_user, db, write_access=False)

    return DocumentStatusResponse.model_validate(doc)


@router.post(
    "/{document_id}/retry",
    response_model=DocumentStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry Document Extraction",
    description="Retries processing for an existing failed document without requiring the candidate to re-upload the file.",
)
async def retry_document_processing(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentStatusResponse:
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(document_id)

    if not doc:
        raise NotFoundError(f"Document {document_id} was not found")

    await verify_document_access(doc, current_user, db, write_access=True)

    service = DocumentService()
    updated_doc = await service.retry_document_processing(
        document_id=document_id,
        actor_id=current_user.id,
    )
    # Also add to background tasks for test execution environments
    background_tasks.add_task(service.process_document_extraction, document_id)

    return DocumentStatusResponse.model_validate(updated_doc)


@router.post(
    "/{document_id}/extract",
    response_model=ExtractionRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger AI Evidence Extraction",
    description="Triggers the AI extraction pipeline to parse structured claims and source quotes from resume text.",
)
async def trigger_ai_extraction(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExtractionRunResponse:
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id)

    if not doc:
        raise NotFoundError(f"Document {document_id} was not found")

    await verify_document_access(doc, current_user, db, write_access=True)

    # 1. Reject if PDF text extraction is still queued or processing (HTTP 409)
    if doc.processing_status in (
        DocumentProcessingStatus.QUEUED,
        DocumentProcessingStatus.PROCESSING,
    ):
        raise ConflictError(
            "Document text extraction is still in progress. Please poll /status until completed."
        )

    # 2. Reject if PDF processing failed (HTTP 422)
    if doc.processing_status == DocumentProcessingStatus.FAILED:
        err_msg = (
            doc.processing_error.get("message", "Document text extraction failed")
            if isinstance(doc.processing_error, dict)
            else "Document text extraction failed"
        )
        raise ValidationError(f"Document text extraction failed: {err_msg}")

    # 3. Reject if no usable page text exists (HTTP 422)
    raw_pages = doc.extracted_text_by_page or {}
    has_text = any(str(text).strip() for text in raw_pages.values())
    if not has_text:
        raise ValidationError("Document contains no usable extracted text for AI extraction.")

    ext_repo = ExtractionRepository(db)

    # Prevent accidental duplicate in-flight runs: if an extraction run is already QUEUED or PROCESSING, return it
    existing_run = await ext_repo.get_latest_run_for_document(document_id)
    if existing_run and existing_run.status in (
        DocumentProcessingStatus.QUEUED,
        DocumentProcessingStatus.PROCESSING,
    ):
        skills = await ext_repo.get_candidate_skills_for_run(existing_run.id)
        evidence_items = await ext_repo.get_evidence_items_for_run(existing_run.id)
        return ExtractionRunResponse(
            id=existing_run.id,
            document_id=document_id,
            run_number=existing_run.run_number,
            provider=existing_run.provider,
            model_name=existing_run.model_name,
            status=existing_run.status,
            error_message=existing_run.error_message,
            skills=[CandidateSkillSummary.model_validate(s) for s in skills],
            evidence_items=[EvidenceItemSummary.model_validate(e) for e in evidence_items],
            started_at=existing_run.started_at,
            completed_at=existing_run.completed_at,
        )

    # Synchronously create and commit the real ExtractionRun database record with QUEUED status
    extraction_service = AIExtractionService()
    provider = extraction_service.llm_provider
    provider_name = getattr(provider, "provider_name", "fake")
    model_name = getattr(provider, "model_name", "default")

    new_run = await ext_repo.create_extraction_run(
        document_id=document_id,
        provider=provider_name,
        model_name=model_name,
        status=DocumentProcessingStatus.QUEUED,
    )
    await db.commit()
    await db.refresh(new_run)

    # Pass both document_id and run_id to the background task
    background_tasks.add_task(
        extraction_service.extract_and_persist,
        document_id,
        new_run.id,
    )

    return ExtractionRunResponse(
        id=new_run.id,
        document_id=new_run.document_id,
        run_number=new_run.run_number,
        provider=new_run.provider,
        model_name=new_run.model_name,
        status=new_run.status,
        error_message=new_run.error_message,
        skills=[],
        evidence_items=[],
        started_at=new_run.started_at,
        completed_at=new_run.completed_at,
    )


@router.get(
    "/{document_id}/extraction-results",
    response_model=ExtractionRunResponse,
    summary="Get AI Evidence Extraction Results",
    description="Retrieves the latest structured AI evidence extraction run, including grounded skills and evidence items.",
)
async def get_extraction_results(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExtractionRunResponse:
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id)

    if not doc:
        raise NotFoundError(f"Document {document_id} was not found")

    await verify_document_access(doc, current_user, db, write_access=False)

    ext_repo = ExtractionRepository(db)
    run = await ext_repo.get_latest_run_for_document(document_id)
    if not run:
        raise NotFoundError(f"No extraction run found for document {document_id}")

    skills = await ext_repo.get_candidate_skills_for_run(run.id)
    evidence_items = await ext_repo.get_evidence_items_for_run(run.id)

    return ExtractionRunResponse(
        id=run.id,
        document_id=document_id,
        run_number=run.run_number,
        provider=run.provider,
        model_name=run.model_name,
        status=run.status,
        error_message=run.error_message,
        skills=[CandidateSkillSummary.model_validate(s) for s in skills],
        evidence_items=[EvidenceItemSummary.model_validate(e) for e in evidence_items],
        started_at=run.started_at,
        completed_at=run.completed_at,
    )
