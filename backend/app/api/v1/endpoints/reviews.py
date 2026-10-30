import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser, UserRole, get_current_user, require_roles
from app.db.models.enums import ReviewFlagStatus
from app.db.session import get_db_session
from app.repositories.domain import ReviewFlagRepository
from app.schemas.review import (
    CandidateClarificationRequest,
    CandidateClarificationResponse,
    ReviewCaseDetailResponse,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewFlagBatchResponse,
    ReviewFlagCreateRequest,
    ReviewFlagSummaryResponse,
)
from app.services.review import ReviewWorkflowService

router = APIRouter(tags=["Human Review Workflow"])


# ============================================================================
# 1. Review Flags Management
# ============================================================================


@router.post(
    "/review-flags",
    response_model=ReviewFlagBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or Auto-Flag Review Cases",
    description=(
        "Raises review flags for candidate evaluation criteria. "
        "By default, auto-flags all ambiguous required criteria and not_found required criteria. "
        "Preferred criteria are flagged only when flag_preferred=True."
    ),
)
async def create_review_flags(
    request: ReviewFlagCreateRequest,
    current_user: CurrentUser = Depends(require_roles(UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER)),
    db: AsyncSession = Depends(get_db_session),
) -> ReviewFlagBatchResponse:
    service = ReviewWorkflowService()
    flags = await service.create_review_flags(
        application_id=request.application_id,
        session=db,
        criterion_evidence_id=request.criterion_evidence_id,
        flag_preferred=request.flag_preferred,
        reason=request.reason,
        priority=request.priority,
        assigned_to_user_id=request.assigned_to_user_id,
        actor_id=current_user.id,
        actor_role=current_user.role.value,
    )
    await db.commit()

    return ReviewFlagBatchResponse(
        application_id=request.application_id,
        total_flagged=len(flags),
        flags=flags,
    )


@router.get(
    "/review-flags",
    response_model=list[ReviewFlagSummaryResponse],
    summary="List Assigned Review Cases",
    description="Retrieves review cases assigned to the current reviewer. Admins may view all cases.",
)
@router.get(
    "/reviews",
    response_model=list[ReviewFlagSummaryResponse],
    include_in_schema=False,
)
async def list_review_cases(
    status_filter: ReviewFlagStatus | None = Query(
        default=None, alias="status", description="Filter by review flag status"
    ),
    application_id: uuid.UUID | None = Query(default=None, description="Filter by application ID"),
    current_user: CurrentUser = Depends(
        require_roles(UserRole.REVIEWER, UserRole.EMPLOYER_ADMIN, UserRole.SYSTEM_AUDITOR)
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[ReviewFlagSummaryResponse]:
    service = ReviewWorkflowService()
    return await service.get_assigned_review_cases(
        current_user=current_user,
        session=db,
        status=status_filter,
        application_id=application_id,
    )


@router.get(
    "/reviews/{id}",
    response_model=ReviewCaseDetailResponse,
    summary="Get Full Review Case Details",
    description=(
        "Retrieves full review case package: criterion definition, source evidence quote & page, "
        "candidate clarifications, and reviewer decision history."
    ),
)
@router.get(
    "/review-flags/{id}",
    response_model=ReviewCaseDetailResponse,
    include_in_schema=False,
)
async def get_review_case_detail(
    id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReviewCaseDetailResponse:
    service = ReviewWorkflowService()
    return await service.get_review_case_detail(
        flag_id=id,
        current_user=current_user,
        session=db,
    )


# ============================================================================
# 2. Reviewer Decisions
# ============================================================================


@router.post(
    "/reviews/{id}/decision",
    response_model=ReviewDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Reviewer Decision",
    description=(
        "Records an authorized reviewer verdict (accepted, rejected, or requested_clarification) "
        "with a mandatory non-empty explanatory rationale. Updates verification state and audit trail."
    ),
)
async def record_review_decision(
    id: uuid.UUID,
    decision_request: ReviewDecisionRequest,
    req: Request,
    current_user: CurrentUser = Depends(require_roles(UserRole.REVIEWER, UserRole.EMPLOYER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> ReviewDecisionResponse:
    client_ip = req.client.host if req.client else None
    service = ReviewWorkflowService()
    decision_response = await service.record_reviewer_decision(
        flag_id=id,
        decision=decision_request.decision,
        mandatory_rationale=decision_request.mandatory_rationale,
        current_user=current_user,
        session=db,
        ip_address=client_ip,
    )
    await db.commit()
    return decision_response


# ============================================================================
# 3. Candidate Clarification & Evidence Submission
# ============================================================================


@router.post(
    "/applications/{id}/clarifications",
    response_model=CandidateClarificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Candidate Clarification or Supplementary Evidence",
    description=(
        "Allows a candidate to submit clarification or contest evidence for a criterion. "
        "Candidate-provided evidence remains strictly unverified until approved by a reviewer."
    ),
)
async def submit_candidate_clarification_on_application(
    id: uuid.UUID,
    clarification_request: CandidateClarificationRequest,
    req: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CandidateClarificationResponse:
    client_ip = req.client.host if req.client else None
    service = ReviewWorkflowService()
    clarification_response = await service.submit_candidate_clarification(
        application_id=id,
        criterion_evidence_id=clarification_request.criterion_evidence_id,
        candidate_statement=clarification_request.candidate_statement,
        additional_document_id=clarification_request.additional_document_id,
        candidate=current_user,
        session=db,
        ip_address=client_ip,
    )
    await db.commit()
    return clarification_response


@router.post(
    "/reviews/{id}/clarification",
    response_model=CandidateClarificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Candidate Clarification via Review Case ID",
    description="Convenience endpoint to submit candidate clarification directly referencing a review flag ID.",
)
async def submit_candidate_clarification_on_review(
    id: uuid.UUID,
    clarification_request: CandidateClarificationRequest,
    req: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CandidateClarificationResponse:
    flag_repo = ReviewFlagRepository(db)
    flag = await flag_repo.get_by_id(id)
    if not flag:
        raise NotFoundError(f"ReviewFlag {id} not found.")

    client_ip = req.client.host if req.client else None
    service = ReviewWorkflowService()
    clarification_response = await service.submit_candidate_clarification(
        application_id=flag.application_id,
        criterion_evidence_id=clarification_request.criterion_evidence_id,
        candidate_statement=clarification_request.candidate_statement,
        additional_document_id=clarification_request.additional_document_id,
        candidate=current_user,
        session=db,
        ip_address=client_ip,
    )
    await db.commit()
    return clarification_response
