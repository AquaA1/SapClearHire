import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.security import CurrentUser, UserRole, get_current_user, require_roles
from app.db.session import get_db_session
from app.repositories.domain import EvaluationRepository
from app.schemas.evaluation import EvaluationCreateRequest, EvaluationResponse
from app.services.evaluation import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.post(
    "",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate Candidate Application Against Criteria",
    description=(
        "Executes deterministic evidence evaluation for a candidate application against active job criteria. "
        "Returns factual coverage counts (never opaque scores) and per-criterion evaluations."
    ),
)
async def evaluate_application(
    request: EvaluationCreateRequest,
    current_user: CurrentUser = Depends(
        require_roles(
            UserRole.EMPLOYER_ADMIN,
            UserRole.REVIEWER,
            UserRole.SYSTEM_AUDITOR,
        )
    ),
    db: AsyncSession = Depends(get_db_session),
) -> EvaluationResponse:
    eval_service = EvaluationService()
    evaluation = await eval_service.evaluate_application(
        application_id=request.application_id,
        session=db,
        actor_id=current_user.id,
        current_user=current_user,
    )
    await db.commit()

    return EvaluationService.build_evaluation_response(evaluation)


@router.get(
    "/application/{application_id}",
    response_model=EvaluationResponse,
    summary="Get Evaluation Report by Application ID",
    description="Retrieves the latest candidate evaluation report for a given application ID.",
)
async def get_evaluation_by_application(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> EvaluationResponse:
    eval_repo = EvaluationRepository(db)
    evaluation = await eval_repo.get_latest_by_application(application_id)
    if not evaluation:
        raise NotFoundError(f"No evaluation found for application {application_id}.")

    if current_user.role == UserRole.CANDIDATE:
        if evaluation.application and str(evaluation.application.candidate_id) != current_user.id:
            raise AuthorizationError(
                "Candidates may only view evaluations of their own applications."
            )
    elif current_user.role in (UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER):
        if evaluation.application and evaluation.application.job:
            job = evaluation.application.job
            is_creator = str(job.employer_id) == current_user.id
            org_matches = bool(
                current_user.employer_id
                and job.creator
                and job.creator.employer_id == current_user.employer_id
            )
            if not (is_creator or org_matches):
                raise AuthorizationError(
                    "You are not authorized to view evaluations for this job requisition."
                )
    elif current_user.role == UserRole.SYSTEM_AUDITOR:
        pass
    else:
        raise AuthorizationError("You are not authorized to view this evaluation.")

    return EvaluationService.build_evaluation_response(evaluation)


@router.get(
    "/{id}",
    response_model=EvaluationResponse,
    summary="Get Evaluation Report",
    description="Retrieves a candidate evaluation report with factual coverage counts and criteria evidence links.",
)
async def get_evaluation(
    id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> EvaluationResponse:
    eval_repo = EvaluationRepository(db)
    evaluation = await eval_repo.get_evaluation_with_items(id)
    if not evaluation:
        raise NotFoundError(f"Evaluation {id} not found.")

    if current_user.role == UserRole.CANDIDATE:
        if evaluation.application and str(evaluation.application.candidate_id) != current_user.id:
            raise AuthorizationError(
                "Candidates may only view evaluations of their own applications."
            )
    elif current_user.role in (UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER):
        if evaluation.application and evaluation.application.job:
            job = evaluation.application.job
            is_creator = str(job.employer_id) == current_user.id
            org_matches = bool(
                current_user.employer_id
                and job.creator
                and job.creator.employer_id == current_user.employer_id
            )
            if not (is_creator or org_matches):
                raise AuthorizationError(
                    "You are not authorized to view evaluations for this job requisition."
                )
    elif current_user.role == UserRole.SYSTEM_AUDITOR:
        pass
    else:
        raise AuthorizationError("You are not authorized to view this evaluation.")

    return EvaluationService.build_evaluation_response(evaluation)
