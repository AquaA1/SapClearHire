import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser, UserRole, get_current_user, require_roles
from app.db.models.job import Job
from app.db.models.user import User
from app.db.session import get_db_session
from app.repositories.domain import JobRepository, UserRepository
from app.schemas.evaluation import JobCreateRequest, JobCriterionResponse, JobResponse

router = APIRouter(prefix="/jobs", tags=["Jobs & Criteria"])


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
