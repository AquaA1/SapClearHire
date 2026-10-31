import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.security import CurrentUser, UserRole, get_current_user, require_roles
from app.db.models.application import Application
from app.db.models.document import Document
from app.db.models.job import Job
from app.db.models.review import ReviewDecision, ReviewFlag
from app.db.session import get_db_session
from app.repositories.audit import AuditEventRepository
from app.schemas.audit import AuditEventDetailResponse, AuditVerificationReportResponse
from app.services.audit import (
    AuditVerificationService,
    canonicalize_audit_payload,
    compute_audit_hash,
)

router = APIRouter(prefix="/audit", tags=["Audit & Integrity"])


@router.get(
    "/verify",
    response_model=AuditVerificationReportResponse,
    summary="Verify Audit Hash Chain",
    description=(
        "Verifies cryptographic hash-chain continuity and content integrity across all audit events. "
        "Explicitly detects modifications, deletions, reorderings, or sequence gaps."
    ),
)
@router.post(
    "/verify",
    response_model=AuditVerificationReportResponse,
    include_in_schema=False,
)
async def verify_audit_chain(
    current_user: CurrentUser = Depends(
        require_roles(UserRole.SYSTEM_AUDITOR, UserRole.EMPLOYER_ADMIN)
    ),
    db: AsyncSession = Depends(get_db_session),
) -> AuditVerificationReportResponse:
    verifier = AuditVerificationService()
    result = await verifier.verify_chain(db)
    return AuditVerificationReportResponse.model_validate(result)


def _safe_uuid(val: object) -> uuid.UUID | None:
    if not val:
        return None
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return None


async def _verify_employer_resource_ownership(
    resource_type: str | None,
    resource_id: str,
    current_user: CurrentUser,
    db: AsyncSession,
) -> bool:
    """Verifies that a given resource belongs to the employer administrator's organization."""
    res_uuid = _safe_uuid(resource_id)
    if not res_uuid:
        return False

    if resource_type == "job":
        res = await db.execute(
            select(Job).options(selectinload(Job.creator)).where(Job.id == res_uuid)
        )
        job = res.scalar_one_or_none()
        if job:
            is_creator = str(job.employer_id) == current_user.id
            org_matches = bool(
                current_user.employer_id
                and job.creator
                and job.creator.employer_id == current_user.employer_id
            )
            return is_creator or org_matches
        return False

    if resource_type == "application":
        res = await db.execute(
            select(Application)
            .options(selectinload(Application.job).selectinload(Job.creator))
            .where(Application.id == res_uuid)
        )
        app = res.scalar_one_or_none()
        if app and app.job:
            is_creator = str(app.job.employer_id) == current_user.id
            org_matches = bool(
                current_user.employer_id
                and app.job.creator
                and app.job.creator.employer_id == current_user.employer_id
            )
            return is_creator or org_matches
        return False

    if resource_type == "document":
        res = await db.execute(
            select(Application)
            .options(selectinload(Application.job).selectinload(Job.creator))
            .where(Application.primary_document_id == res_uuid)
        )
        apps = res.scalars().all()
        for app in apps:
            if app.job:
                is_creator = str(app.job.employer_id) == current_user.id
                org_matches = bool(
                    current_user.employer_id
                    and app.job.creator
                    and app.job.creator.employer_id == current_user.employer_id
                )
                if is_creator or org_matches:
                    return True
        return False

    if resource_type in ("review_flag", "review_case"):
        res = await db.execute(
            select(ReviewFlag)
            .options(
                selectinload(ReviewFlag.application)
                .selectinload(Application.job)
                .selectinload(Job.creator)
            )
            .where(ReviewFlag.id == res_uuid)
        )
        flag = res.scalar_one_or_none()
        if flag and flag.application and flag.application.job:
            job = flag.application.job
            is_creator = str(job.employer_id) == current_user.id
            org_matches = bool(
                current_user.employer_id
                and job.creator
                and job.creator.employer_id == current_user.employer_id
            )
            return is_creator or org_matches
        return False

    if resource_type == "review_decision":
        res = await db.execute(
            select(ReviewDecision)
            .options(
                selectinload(ReviewDecision.review_flag)
                .selectinload(ReviewFlag.application)
                .selectinload(Application.job)
                .selectinload(Job.creator)
            )
            .where(ReviewDecision.id == res_uuid)
        )
        decision = res.scalar_one_or_none()
        if (
            decision
            and decision.review_flag
            and decision.review_flag.application
            and decision.review_flag.application.job
        ):
            job = decision.review_flag.application.job
            is_creator = str(job.employer_id) == current_user.id
            org_matches = bool(
                current_user.employer_id
                and job.creator
                and job.creator.employer_id == current_user.employer_id
            )
            return is_creator or org_matches
        return False

    return False


@router.get(
    "",
    response_model=list[AuditEventDetailResponse],
    summary="Query Resource Audit Events",
    description=(
        "Retrieves paginated, cryptographically verifiable audit events filtered by resource_type, "
        "resource_id, and actor_id. Accessible to system auditors and employer admins."
    ),
)
async def list_audit_events(
    resource_type: str | None = Query(default=None, description="Filter by resource type"),
    resource_id: str | None = Query(default=None, description="Filter by resource ID"),
    actor_id: str | None = Query(default=None, description="Filter by actor ID"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Records offset"),
    current_user: CurrentUser = Depends(
        require_roles(UserRole.SYSTEM_AUDITOR, UserRole.EMPLOYER_ADMIN)
    ),
    db: AsyncSession = Depends(get_db_session),
) -> list[AuditEventDetailResponse]:
    repo = AuditEventRepository(db)

    if current_user.role == UserRole.EMPLOYER_ADMIN:
        if resource_id:
            authorized = await _verify_employer_resource_ownership(
                resource_type, resource_id, current_user, db
            )
            if not authorized:
                raise AuthorizationError(
                    "You are not authorized to query audit events for resources outside your organization."
                )
            events = await repo.query_events(
                resource_type=resource_type,
                resource_id=resource_id,
                actor_id=actor_id,
                limit=limit,
                offset=offset,
            )
        else:
            raw_events = await repo.query_events(
                resource_type=resource_type,
                resource_id=None,
                actor_id=actor_id,
                limit=limit * 2,
                offset=offset,
            )
            events = []
            for ev in raw_events:
                if ev.actor_id == current_user.id or (
                    ev.details and ev.details.get("employer_id") == current_user.employer_id
                ):
                    events.append(ev)
                elif ev.resource_id and await _verify_employer_resource_ownership(
                    ev.resource_type, ev.resource_id, current_user, db
                ):
                    events.append(ev)
                if len(events) >= limit:
                    break
    else:
        # SYSTEM_AUDITOR has unrestricted query capability
        events = await repo.query_events(
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            limit=limit,
            offset=offset,
        )

    responses = []
    for event in events:
        canonical_bytes = canonicalize_audit_payload(
            sequence_number=event.sequence_number,
            timestamp=event.timestamp,
            actor_id=event.actor_id,
            actor_role=event.actor_role,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            entity_version=event.entity_version,
            prior_state=event.prior_state,
            new_state=event.new_state,
            details=event.details,
            previous_hash=event.previous_hash,
        )
        is_verified = compute_audit_hash(canonical_bytes) == event.event_hash
        responses.append(
            AuditEventDetailResponse(
                id=event.id,
                sequence_number=event.sequence_number,
                timestamp=event.timestamp,
                actor_id=event.actor_id,
                actor_role=event.actor_role,
                action=event.action,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                entity_version=event.entity_version,
                prior_state=event.prior_state,
                new_state=event.new_state,
                details=event.details,
                ip_address=event.ip_address,
                previous_hash=event.previous_hash,
                event_hash=event.event_hash,
                is_verified=is_verified,
            )
        )

    return responses


@router.get(
    "/{id}",
    response_model=AuditEventDetailResponse,
    summary="Get Audit Event Details",
    description="Retrieves a specific audit event with previous/event hashes and cryptographic verification.",
)
async def get_audit_event(
    id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AuditEventDetailResponse:
    repo = AuditEventRepository(db)
    event = await repo.get_by_id(id)
    if not event:
        raise NotFoundError(f"Audit event {id} not found.")

    # 1. Enforce strict authorization rules
    if current_user.role in (UserRole.SYSTEM_AUDITOR, UserRole.EMPLOYER_ADMIN):
        pass  # Full access
    elif current_user.role == UserRole.REVIEWER:
        # Reviewer can only access events they acted on or cases assigned to them
        is_actor = event.actor_id == current_user.id
        has_access = is_actor
        res_uuid = _safe_uuid(event.resource_id)
        curr_uuid = _safe_uuid(current_user.id)

        if not has_access and event.resource_type == "review_decision" and res_uuid:
            res = await db.execute(select(ReviewDecision).where(ReviewDecision.id == res_uuid))
            decision = res.scalar_one_or_none()
            if decision and str(decision.reviewer_id) == current_user.id:
                has_access = True
        elif not has_access and event.resource_type == "review_flag" and res_uuid:
            res = await db.execute(select(ReviewFlag).where(ReviewFlag.id == res_uuid))
            flag = res.scalar_one_or_none()
            if flag and str(flag.assigned_to_user_id) == current_user.id:
                has_access = True
        elif not has_access and event.resource_type == "application" and res_uuid and curr_uuid:
            res = await db.execute(
                select(ReviewFlag).where(
                    ReviewFlag.application_id == res_uuid,
                    ReviewFlag.assigned_to_user_id == curr_uuid,
                )
            )
            if res.scalar_one_or_none():
                has_access = True

        if not has_access:
            raise AuthorizationError(
                "Reviewers may only query audit events for their assigned review cases."
            )

    elif current_user.role == UserRole.CANDIDATE:
        # Candidate can only access events directly related to their own records
        is_actor = event.actor_id == current_user.id
        has_access = is_actor
        res_uuid = _safe_uuid(event.resource_id)

        if not has_access and event.resource_type == "document" and res_uuid:
            res = await db.execute(select(Document).where(Document.id == res_uuid))
            doc = res.scalar_one_or_none()
            if doc and str(doc.candidate_id) == current_user.id:
                has_access = True
        elif not has_access and event.resource_type == "application" and res_uuid:
            res = await db.execute(select(Application).where(Application.id == res_uuid))
            app = res.scalar_one_or_none()
            if app and str(app.candidate_id) == current_user.id:
                has_access = True
        elif not has_access and event.details and "application_id" in event.details:
            app_uuid = _safe_uuid(event.details.get("application_id"))
            if app_uuid:
                res = await db.execute(select(Application).where(Application.id == app_uuid))
                app = res.scalar_one_or_none()
                if app and str(app.candidate_id) == current_user.id:
                    has_access = True

        if not has_access:
            raise AuthorizationError(
                "Candidates may only query audit events relating to their own records."
            )

    # 2. Check individual event content verification
    canonical_bytes = canonicalize_audit_payload(
        sequence_number=event.sequence_number,
        timestamp=event.timestamp,
        actor_id=event.actor_id,
        actor_role=event.actor_role,
        action=event.action,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        entity_version=event.entity_version,
        prior_state=event.prior_state,
        new_state=event.new_state,
        details=event.details,
        previous_hash=event.previous_hash,
    )
    is_verified = compute_audit_hash(canonical_bytes) == event.event_hash

    return AuditEventDetailResponse(
        id=event.id,
        sequence_number=event.sequence_number,
        timestamp=event.timestamp,
        actor_id=event.actor_id,
        actor_role=event.actor_role,
        action=event.action,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        entity_version=event.entity_version,
        prior_state=event.prior_state,
        new_state=event.new_state,
        details=event.details,
        ip_address=event.ip_address,
        previous_hash=event.previous_hash,
        event_hash=event.event_hash,
        is_verified=is_verified,
    )
