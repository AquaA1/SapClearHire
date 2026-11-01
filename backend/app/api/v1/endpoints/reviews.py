import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.core.logging import logger
from app.core.security import CurrentUser, UserRole, get_current_user, require_roles
from app.core.websocket import ws_manager
from app.db.models.application import Application
from app.db.models.enums import ReviewDecisionType, ReviewFlagStatus
from app.db.models.job import Job
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
        current_user=current_user,
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
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by review flag status: 'pending', 'under_review', 'resolved', 'all'",
    ),
    application_id: uuid.UUID | None = Query(default=None, description="Filter by application ID"),
    current_user: CurrentUser = Depends(
        require_roles(UserRole.REVIEWER, UserRole.EMPLOYER_ADMIN, UserRole.SYSTEM_AUDITOR)
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[ReviewFlagSummaryResponse]:
    service = ReviewWorkflowService()

    status_enum: ReviewFlagStatus | None = None
    status_list: list[ReviewFlagStatus] | None = None

    if status_filter:
        s = status_filter.strip().lower()
        if s in ("pending", "unresolved", "needs_review"):
            status_list = [ReviewFlagStatus.PENDING, ReviewFlagStatus.UNDER_REVIEW]
        elif s == "under_review":
            status_enum = ReviewFlagStatus.UNDER_REVIEW
        elif s == "resolved":
            status_enum = ReviewFlagStatus.RESOLVED
        elif s == "dismissed":
            status_enum = ReviewFlagStatus.DISMISSED
        elif s in ("all", ""):
            status_enum = None
        else:
            try:
                status_enum = ReviewFlagStatus(s)
            except ValueError:
                status_enum = None

    results = await service.get_assigned_review_cases(
        current_user=current_user,
        session=db,
        status=status_enum,
        status_list=status_list,
        application_id=application_id,
    )
    await db.commit()
    return results


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


async def _get_application_participant_ids(
    session: AsyncSession, application_id: uuid.UUID
) -> tuple[str, list[str]]:
    """Helper to retrieve candidate and employer user IDs for application WebSocket event routing."""
    stmt = (
        select(Application)
        .options(selectinload(Application.job).selectinload(Job.creator))
        .where(Application.id == application_id)
    )
    res = await session.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        return "", []
    candidate_id = str(app.candidate_id)
    employer_ids: list[str] = []
    if app.job:
        if app.job.employer_id:
            employer_ids.append(str(app.job.employer_id))
        if app.job.creator and app.job.creator.employer_id:
            employer_ids.append(str(app.job.creator.employer_id))
        if app.job.creator and str(app.job.creator.id) not in employer_ids:
            employer_ids.append(str(app.job.creator.id))
    return candidate_id, employer_ids


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

    # Real-time WebSocket event broadcast (post-commit)
    try:
        candidate_id, employer_ids = await _get_application_participant_ids(
            db, decision_response.application_id
        )
        if decision_request.decision == ReviewDecisionType.ACCEPTED:
            event_name = "clarification.accepted"
        elif decision_request.decision == ReviewDecisionType.REJECTED:
            event_name = "clarification.rejected"
        elif decision_request.decision == ReviewDecisionType.REQUESTED_CLARIFICATION:
            event_name = "clarification.created"
        else:
            event_name = "clarification.created"

        await ws_manager.broadcast_clarification_event(
            event=event_name,
            application_id=decision_response.application_id,
            clarification_id=decision_response.id,
            candidate_id=candidate_id,
            employer_ids=employer_ids,
        )
    except Exception as exc:
        logger.warning("Failed to broadcast WebSocket event for review decision: %s", exc)

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
    current_user: CurrentUser = Depends(require_roles(UserRole.CANDIDATE)),
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

    # Real-time WebSocket event broadcast (post-commit)
    try:
        candidate_id, employer_ids = await _get_application_participant_ids(
            db, clarification_response.application_id
        )
        await ws_manager.broadcast_clarification_event(
            event="clarification.responded",
            application_id=clarification_response.application_id,
            clarification_id=clarification_response.id,
            candidate_id=candidate_id,
            employer_ids=employer_ids,
        )
    except Exception as exc:
        logger.warning("Failed to broadcast WebSocket event for candidate clarification: %s", exc)

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
    current_user: CurrentUser = Depends(require_roles(UserRole.CANDIDATE)),
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

    # Real-time WebSocket event broadcast (post-commit)
    try:
        candidate_id, employer_ids = await _get_application_participant_ids(
            db, clarification_response.application_id
        )
        await ws_manager.broadcast_clarification_event(
            event="clarification.responded",
            application_id=clarification_response.application_id,
            clarification_id=clarification_response.id,
            candidate_id=candidate_id,
            employer_ids=employer_ids,
        )
    except Exception as exc:
        logger.warning("Failed to broadcast WebSocket event for candidate clarification: %s", exc)

    return clarification_response
