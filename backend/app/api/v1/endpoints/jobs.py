import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.security import CurrentUser, UserRole, get_current_user, require_roles
from app.db.models.enums import JobStatus
from app.db.models.job import Job
from app.db.models.user import User
from app.db.session import get_db_session
from app.repositories.domain import JobRepository, UserRepository
from app.schemas.evaluation import JobCreateRequest, JobCriterionResponse, JobResponse

router = APIRouter(prefix="/jobs", tags=["Jobs & Criteria"])


@router.get(
    "",
    response_model=list[JobResponse],
    summary="List Job Requisitions",
    description="Retrieves a paginated list of job requisitions with criteria, subject to role and tenant isolation.",
)
async def list_jobs(
    status_filter: JobStatus | None = Query(
        default=None, alias="status", description="Filter by job status"
    ),
    department: str | None = Query(default=None, description="Filter by department"),
    limit: int = Query(default=50, ge=1, le=200, description="Max jobs to return"),
    offset: int = Query(default=0, ge=0, description="Records offset"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[JobResponse]:
    stmt = select(Job).options(selectinload(Job.criteria), selectinload(Job.creator))

    if department:
        stmt = stmt.where(Job.department == department)

    if current_user.role == UserRole.CANDIDATE:
        stmt = stmt.where(Job.status == JobStatus.ACTIVE)
    elif current_user.role in (UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER):
        curr_uuid = uuid.UUID(current_user.id)
        if current_user.employer_id:
            stmt = stmt.outerjoin(Job.creator).where(
                (Job.employer_id == curr_uuid) | (User.employer_id == current_user.employer_id)
            )
        else:
            stmt = stmt.where(Job.employer_id == curr_uuid)
        if status_filter:
            stmt = stmt.where(Job.status == status_filter)
    elif current_user.role == UserRole.SYSTEM_AUDITOR:
        if status_filter:
            stmt = stmt.where(Job.status == status_filter)
    else:
        raise AuthorizationError("You are not authorized to view jobs.")

    stmt = stmt.order_by(Job.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    return [
        JobResponse(
            id=j.id,
            employer_id=j.employer_id,
            title=j.title,
            description=j.description,
            department=j.department,
            status=j.status,
            criteria=[JobCriterionResponse.model_validate(c) for c in j.criteria],
            created_at=j.created_at,
            updated_at=j.updated_at,
        )
        for j in jobs
    ]


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Job Requisition with Criteria",
    description="Creates a new employer job requisition with versioned screening criteria.",
)
async def create_job(
    request: JobCreateRequest,
    current_user: CurrentUser = Depends(require_roles(UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER)),
    db: AsyncSession = Depends(get_db_session),
) -> JobResponse:
    employer_id = uuid.UUID(current_user.id)

    # Ensure user row exists for foreign key integrity
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(employer_id)
    if not user:
        user = User(
            id=employer_id,
            email=current_user.email,
            full_name=current_user.email.split("@")[0],
            role=current_user.role,
            employer_id=current_user.employer_id,
        )
        db.add(user)
        await db.flush()

    job_repo = JobRepository(db)

    # Duplicate submission protection: check if identical requisition was submitted by this employer within last 10 seconds
    recent_threshold = datetime.now(UTC) - timedelta(seconds=10)
    dupe_query = (
        select(Job)
        .options(selectinload(Job.criteria))
        .where(
            Job.employer_id == employer_id,
            Job.title == request.title,
            Job.department == request.department,
            Job.created_at >= recent_threshold,
        )
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    existing_dupe = (await db.execute(dupe_query)).scalar_one_or_none()
    if existing_dupe:
        return JobResponse(
            id=existing_dupe.id,
            employer_id=existing_dupe.employer_id,
            title=existing_dupe.title,
            description=existing_dupe.description,
            department=existing_dupe.department,
            status=existing_dupe.status,
            criteria=[JobCriterionResponse.model_validate(c) for c in existing_dupe.criteria],
            created_at=existing_dupe.created_at,
            updated_at=existing_dupe.updated_at,
        )

    job = Job(
        employer_id=employer_id,
        title=request.title,
        description=request.description,
        department=request.department,
    )
    db.add(job)
    await db.flush()

    criteria_responses: list[JobCriterionResponse] = []
    for crit_data in request.criteria:
        crit = await job_repo.add_criterion(
            job_id=job.id,
            name=crit_data.name,
            category=crit_data.category.value
            if hasattr(crit_data.category, "value")
            else str(crit_data.category),
            weight=crit_data.weight,
            description=crit_data.description,
            version=1,
        )
        criteria_responses.append(JobCriterionResponse.model_validate(crit))

    await db.commit()
    await db.refresh(job)

    return JobResponse(
        id=job.id,
        employer_id=job.employer_id,
        title=job.title,
        description=job.description,
        department=job.department,
        status=job.status,
        criteria=criteria_responses,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get(
    "/{id}",
    response_model=JobResponse,
    summary="Get Job Requisition",
    description="Retrieves a job requisition with all defined criteria.",
)
async def get_job(
    id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> JobResponse:
    job_repo = JobRepository(db)
    job = await job_repo.get_with_criteria(id)
    if not job:
        raise NotFoundError(f"Job requisition {id} not found.")

    criteria_responses = [JobCriterionResponse.model_validate(c) for c in job.criteria]

    return JobResponse(
        id=job.id,
        employer_id=job.employer_id,
        title=job.title,
        description=job.description,
        department=job.department,
        status=job.status,
        criteria=criteria_responses,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
