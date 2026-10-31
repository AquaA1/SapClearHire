import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.core.security import CurrentUser, UserRole, get_current_user
from app.db.models.application import Application
from app.db.models.enums import ApplicationStatus
from app.db.models.job import Job
from app.db.models.user import User
from app.db.session import get_db_session
from app.repositories.domain import (
    ApplicationRepository,
    DocumentRepository,
    JobRepository,
    UserRepository,
)
from app.schemas.evaluation import ApplicationCreateRequest, ApplicationResponse

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get(
    "",
    response_model=list[ApplicationResponse],
    summary="List Candidate Applications",
    description="Retrieves a paginated list of candidate applications with role-based tenant isolation.",
)
async def list_applications(
    job_id: uuid.UUID | None = Query(default=None, description="Filter by job ID"),
    status_filter: ApplicationStatus | None = Query(
        default=None, alias="status", description="Filter by application status"
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Max applications to return"),
    offset: int = Query(default=0, ge=0, description="Records offset"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[ApplicationResponse]:
    stmt = select(Application).options(selectinload(Application.job).selectinload(Job.creator))

    if job_id:
        stmt = stmt.where(Application.job_id == job_id)
    if status_filter:
        stmt = stmt.where(Application.status == status_filter)

    if current_user.role == UserRole.CANDIDATE:
        stmt = stmt.where(Application.candidate_id == uuid.UUID(current_user.id))
    elif current_user.role in (UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER):
        stmt = stmt.join(Application.job).outerjoin(Job.creator)
        curr_uuid = uuid.UUID(current_user.id)
        if current_user.employer_id:
            stmt = stmt.where(
                (Job.employer_id == curr_uuid) | (User.employer_id == current_user.employer_id)
            )
        else:
            stmt = stmt.where(Job.employer_id == curr_uuid)
    elif current_user.role == UserRole.SYSTEM_AUDITOR:
        pass
    else:
        raise AuthorizationError("You are not authorized to list applications.")

    stmt = stmt.order_by(Application.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    applications = result.scalars().all()

    return [
        ApplicationResponse(
            id=app.id,
            job_id=app.job_id,
            candidate_id=app.candidate_id,
            primary_document_id=app.primary_document_id,
            status=app.status.value,
            submitted_at=app.submitted_at,
            created_at=app.created_at,
        )
        for app in applications
    ]


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
    app_repo = ApplicationRepository(db)
    application = await app_repo.get_with_job(id)
    if not application:
        raise NotFoundError(f"Application {id} not found.")

    if current_user.role == UserRole.CANDIDATE:
        if str(application.candidate_id) != current_user.id:
            raise AuthorizationError("Candidates may only view their own applications.")
    elif current_user.role in (UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER):
        if not application.job:
            raise NotFoundError(f"Job for application {id} not found.")
        is_creator = str(application.job.employer_id) == current_user.id
        org_matches = bool(
            current_user.employer_id
            and application.job.creator
            and application.job.creator.employer_id == current_user.employer_id
        )
        if not (is_creator or org_matches):
            raise AuthorizationError(
                "You are not authorized to view applications for this job requisition."
            )
    elif current_user.role == UserRole.SYSTEM_AUDITOR:
        pass
    else:
        raise AuthorizationError("You are not authorized to view this application.")

    return ApplicationResponse(
        id=application.id,
        job_id=application.job_id,
        candidate_id=application.candidate_id,
        primary_document_id=application.primary_document_id,
        status=application.status.value,
        submitted_at=application.submitted_at,
        created_at=application.created_at,
    )
