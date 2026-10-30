import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.core.security import CurrentUser, UserRole, get_current_user
from app.db.models.application import Application
from app.db.models.enums import ApplicationStatus
from app.db.models.user import User
from app.db.session import get_db_session
from app.repositories.domain import DocumentRepository, JobRepository, UserRepository
from app.schemas.evaluation import ApplicationCreateRequest, ApplicationResponse

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Candidate Application",
    description="Applies a candidate's uploaded resume document to an active job requisition.",
)
async def submit_application(
    request: ApplicationCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApplicationResponse:
    candidate_id = uuid.UUID(current_user.id)

    # Ensure user record exists for foreign key integrity
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

    # Verify job requisition exists
    job_repo = JobRepository(db)
    job = await job_repo.get_by_id(request.job_id)
    if not job:
        raise NotFoundError(f"Job requisition {request.job_id} not found.")

    # Verify document exists and belongs to the candidate
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(request.primary_document_id)
    if not doc:
        raise NotFoundError(f"Document {request.primary_document_id} not found.")

    if current_user.role == UserRole.CANDIDATE and doc.candidate_id != candidate_id:
        raise AuthorizationError("Candidates may only apply with their own uploaded documents.")

    # Check for existing application
    existing_query = select(Application).where(
        Application.job_id == request.job_id,
        Application.candidate_id == candidate_id,
    )
    existing_res = await db.execute(existing_query)
    if existing_res.scalar_one_or_none():
        raise ConflictError(
            "An application for this job has already been submitted by this candidate."
        )

    application = Application(
        job_id=request.job_id,
        candidate_id=candidate_id,
        primary_document_id=request.primary_document_id,
        status=ApplicationStatus.SUBMITTED,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    return ApplicationResponse(
        id=application.id,
        job_id=application.job_id,
        candidate_id=application.candidate_id,
        primary_document_id=application.primary_document_id,
        status=application.status.value,
        submitted_at=application.submitted_at,
        created_at=application.created_at,
    )


@router.get(
    "/{id}",
    response_model=ApplicationResponse,
    summary="Get Candidate Application",
    description="Retrieves candidate application details and screening status.",
)
async def get_application(
    id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApplicationResponse:
    query = select(Application).where(Application.id == id)
    result = await db.execute(query)
    application = result.scalar_one_or_none()
    if not application:
        raise NotFoundError(f"Application {id} not found.")

    if current_user.role == UserRole.CANDIDATE and str(application.candidate_id) != current_user.id:
        raise AuthorizationError("Candidates may only view their own applications.")

    return ApplicationResponse(
        id=application.id,
        job_id=application.job_id,
        candidate_id=application.candidate_id,
        primary_document_id=application.primary_document_id,
        status=application.status.value,
        submitted_at=application.submitted_at,
        created_at=application.created_at,
    )
