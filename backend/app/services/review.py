import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.security import CurrentUser, UserRole
from app.db.models.application import Application
from app.db.models.enums import (
    ApplicationStatus,
    EvidenceStatus,
    ReviewDecisionType,
    ReviewFlagStatus,
    VerificationState,
)
from app.db.models.evaluation import CriterionEvidence, Evaluation
from app.db.models.job import Job
from app.db.models.user import User
from app.repositories.audit import AuditEventRepository
from app.repositories.domain import (
    ApplicationRepository,
    CorrectionRequestRepository,
    DocumentRepository,
    ReviewDecisionRepository,
    ReviewFlagRepository,
    UserRepository,
)
from app.schemas.review import (
    CandidateClarificationItem,
    CandidateClarificationResponse,
    ReviewCaseDetailResponse,
    ReviewDecisionItem,
    ReviewDecisionResponse,
    ReviewFlagResponse,
    ReviewFlagSummaryResponse,
)


class ReviewWorkflowService:
    """
    Orchestrates the ClearHire human review workflow:
    - Rule-based auto-flagging of ambiguous and not_found criteria.
    - Reviewer case queues and assignment boundaries.
    - Full review case aggregation (criterion, evidence, clarifications, decisions).
    - Authorized human reviewer decisions with mandatory rationales.
    - Candidate clarification submissions keeping evidence unverified until reviewer approval.
    """

    async def create_review_flags(
        self,
        application_id: uuid.UUID,
        session: AsyncSession,
        criterion_evidence_id: uuid.UUID | None = None,
        flag_preferred: bool = False,
        reason: str | None = None,
        priority: str = "normal",
        assigned_to_user_id: uuid.UUID | None = None,
        actor_id: str | None = None,
        actor_role: str | None = None,
        current_user: CurrentUser | None = None,
    ) -> list[ReviewFlagResponse]:
        """
        Creates review flags for an application.
        By default, auto-flags all ambiguous required criteria and not_found required criteria.
        Preferred criteria are flagged only when flag_preferred=True.
        """
        flag_repo = ReviewFlagRepository(session)

        # 1. Fetch application with latest evaluation and criteria evidence
        app_query = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.evaluations)
                .selectinload(Evaluation.criterion_evidence_items)
                .selectinload(CriterionEvidence.criterion),
                selectinload(Application.candidate),
                selectinload(Application.job).selectinload(Job.creator),
            )
        )
        app_res = await session.execute(app_query)
        application = app_res.scalar_one_or_none()
        if not application:
            raise NotFoundError(f"Application {application_id} not found.")

        # Check tenant authorization if current_user is provided
        if current_user is not None:
            if current_user.role == UserRole.CANDIDATE:
                raise AuthorizationError("Candidates are not authorized to create review flags.")
            elif current_user.role in (UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER):
                if not application.job:
                    raise NotFoundError(f"Job for application {application_id} not found.")
                is_creator = str(application.job.employer_id) == current_user.id
                org_matches = bool(
                    current_user.employer_id
                    and application.job.creator
                    and application.job.creator.employer_id == current_user.employer_id
                )
                if not (is_creator or org_matches):
                    raise AuthorizationError(
                        "You are not authorized to create review flags for this job requisition."
                    )
            elif current_user.role == UserRole.SYSTEM_AUDITOR:
                pass
            else:
                raise AuthorizationError("You are not authorized to create review flags.")

        if not application.evaluations:
            raise ValidationError(
                f"Application {application_id} has no evaluations to flag. Run evaluation first."
            )

        # Get latest evaluation (prefer is_latest, fallback to highest version)
        latest_eval = next(
            (e for e in application.evaluations if e.is_latest),
            sorted(application.evaluations, key=lambda e: e.version, reverse=True)[0],
        )

        # 2. Determine which criterion evidence items to flag
        items_to_flag: list[CriterionEvidence] = []
        if criterion_evidence_id is not None:
            target_ce = next(
                (
                    ce
                    for ce in latest_eval.criterion_evidence_items
                    if ce.id == criterion_evidence_id
                ),
                None,
            )
            if not target_ce:
                raise NotFoundError(
                    f"CriterionEvidence {criterion_evidence_id} not found in latest evaluation."
                )
            if target_ce.verification_state in (
                VerificationState.HUMAN_VERIFIED,
                VerificationState.HUMAN_REJECTED,
            ):
                return []
            items_to_flag.append(target_ce)
        else:
            existing_flags_pre = await flag_repo.get_by_application(application_id)
            resolved_ce_ids_pre = {
                f.criterion_evidence_id
                for f in existing_flags_pre
                if f.status == ReviewFlagStatus.RESOLVED
            }

            for ce in latest_eval.criterion_evidence_items:
                # Guard: do not flag criteria that have already been adjudicated by human review
                if ce.verification_state in (
                    VerificationState.HUMAN_VERIFIED,
                    VerificationState.HUMAN_REJECTED,
                ):
                    continue
                if ce.id in resolved_ce_ids_pre:
                    continue

                cat = str(ce.criterion.category).lower() if ce.criterion else "required"
                is_req = cat in ("required", "requirement")
                is_ambiguous_or_missing = ce.ai_status in (
                    EvidenceStatus.AMBIGUOUS,
                    EvidenceStatus.NOT_FOUND,
                )

                if is_ambiguous_or_missing:
                    if is_req or flag_preferred:
                        items_to_flag.append(ce)

        if not items_to_flag:
            return []

        # 3. Check existing active flags to prevent duplicate escalations
        existing_flags = await flag_repo.get_by_application(application_id)
        active_ce_ids = {
            f.criterion_evidence_id
            for f in existing_flags
            if f.status in (ReviewFlagStatus.PENDING, ReviewFlagStatus.UNDER_REVIEW)
        }

        # Ensure assigned user exists for foreign key integrity
        if assigned_to_user_id:
            user_repo = UserRepository(session)
            assigned_user = await user_repo.get_by_id(assigned_to_user_id)
            if not assigned_user:
                assigned_user = User(
                    id=assigned_to_user_id,
                    email=f"reviewer_{str(assigned_to_user_id)[:8]}@clearhire.internal",
                    full_name="Assigned Reviewer",
                    role=UserRole.REVIEWER,
                )
                session.add(assigned_user)
                await session.flush()

        created_flags: list[ReviewFlagResponse] = []
        for ce in items_to_flag:
            if ce.id in active_ce_ids:
                # Find the existing active flag
                existing = next(f for f in existing_flags if f.criterion_evidence_id == ce.id)
                created_flags.append(ReviewFlagResponse.model_validate(existing))
                continue

            crit_name = ce.criterion.name if ce.criterion else "Criterion"
            flag_type = (
                "AMBIGUOUS_EVIDENCE"
                if ce.ai_status == EvidenceStatus.AMBIGUOUS
                else "MISSING_EVIDENCE"
            )
            item_reason = reason or (
                f"Ambiguous evidence for required criterion '{crit_name}' requires human assessment."
                if ce.ai_status == EvidenceStatus.AMBIGUOUS
                else f"No evidence found for required criterion '{crit_name}' in submitted material."
            )

            flag = await flag_repo.create_flag(
                application_id=application_id,
                criterion_evidence_id=ce.id,
                flag_type=flag_type,
                reason=item_reason,
                priority=priority,
                assigned_to_user_id=assigned_to_user_id,
                status=ReviewFlagStatus.PENDING,
            )

            # Audit event
            audit_repo = AuditEventRepository(session)
            await audit_repo.log_event(
                action="REVIEW_FLAG_CREATED",
                resource_type="review_flag",
                resource_id=str(flag.id),
                actor_id=actor_id or "system",
                actor_role=actor_role or "system",
                entity_version=1,
                prior_state=None,
                new_state={
                    "status": ReviewFlagStatus.PENDING.value,
                    "priority": priority,
                    "flag_type": flag_type,
                },
                details={
                    "application_id": str(application_id),
                    "criterion_evidence_id": str(ce.id),
                    "criterion_name": crit_name,
                    "flag_type": flag_type,
                    "priority": priority,
                    "assigned_to_user_id": str(assigned_to_user_id)
                    if assigned_to_user_id
                    else None,
                },
            )
            created_flags.append(ReviewFlagResponse.model_validate(flag))

        # 4. Update application status to NEEDS_REVIEW
        application.status = ApplicationStatus.NEEDS_REVIEW
        await session.flush()

        return created_flags

    async def get_assigned_review_cases(
        self,
        current_user: CurrentUser,
        session: AsyncSession,
        status: ReviewFlagStatus | None = None,
        status_list: list[ReviewFlagStatus] | None = None,
        application_id: uuid.UUID | None = None,
    ) -> list[ReviewFlagSummaryResponse]:
        """
        Retrieves review cases from the queue.
        Enforces role-based access:
        - Reviewers view cases assigned to them.
        - Employer Admins view cases belonging to their organization/jobs.
        - System Auditors view all cases.
        """
        flag_repo = ReviewFlagRepository(session)

        filter_user_id: uuid.UUID | None = None
        filter_employer_id: uuid.UUID | None = None
        filter_org_employer_id: str | None = None

        if current_user.role == UserRole.REVIEWER:
            filter_user_id = uuid.UUID(current_user.id)
        elif current_user.role == UserRole.EMPLOYER_ADMIN:
            filter_employer_id = uuid.UUID(current_user.id)
            filter_org_employer_id = current_user.employer_id
        elif current_user.role == UserRole.CANDIDATE:
            raise AuthorizationError("Candidates are not permitted to access reviewer case queues.")

        flags = await flag_repo.get_assigned_flags(
            user_id=filter_user_id,
            status=status,
            status_list=status_list,
            application_id=application_id,
            employer_id=filter_employer_id,
            org_employer_id=filter_org_employer_id,
        )

        # Auto-reconcile lingering flags whose criterion has already been decided
        for f in flags:
            ce = f.criterion_evidence
            if ce and ce.verification_state in (
                VerificationState.HUMAN_VERIFIED,
                VerificationState.HUMAN_REJECTED,
            ):
                if f.status != ReviewFlagStatus.RESOLVED:
                    await flag_repo.update_status(
                        f.id, ReviewFlagStatus.RESOLVED, resolved_at=datetime.now(UTC)
                    )
                    f.status = ReviewFlagStatus.RESOLVED

        # Deduplicate cases by (application_id, criterion_evidence_id) so duplicate flag rows are not double-counted
        seen_cases: set[tuple[uuid.UUID, uuid.UUID | None]] = set()
        summaries: list[ReviewFlagSummaryResponse] = []
        for f in flags:
            ce = f.criterion_evidence
            ce_id = ce.id if ce else f.criterion_evidence_id
            case_key = (f.application_id, ce_id)
            if case_key in seen_cases:
                continue
            seen_cases.add(case_key)

            cand = f.application.candidate if f.application else None
            job = f.application.job if f.application else None
            crit = ce.criterion if ce else None

            summaries.append(
                ReviewFlagSummaryResponse(
                    id=f.id,
                    application_id=f.application_id,
                    criterion_evidence_id=ce_id,
                    criterion_name=crit.name if crit else None,
                    criterion_category=crit.category if crit else None,
                    candidate_id=f.application.candidate_id if f.application else uuid.uuid4(),
                    candidate_name=cand.full_name if cand else "Candidate",
                    job_title=job.title if job else "Requisition",
                    ai_status=ce.ai_status if ce else None,
                    verification_state=ce.verification_state if ce else None,
                    flag_type=f.flag_type,
                    status=f.status,
                    priority=f.priority,
                    reason=f.reason,
                    created_at=f.created_at,
                )
            )

        return summaries

    async def get_review_case_detail(
        self,
        flag_id: uuid.UUID,
        current_user: CurrentUser,
        session: AsyncSession,
    ) -> ReviewCaseDetailResponse:
        """
        Retrieves full review case package including criterion, source evidence,
        clarifications, and decisions history.
        Enforces reviewer assignment authorization.
        """
        flag_repo = ReviewFlagRepository(session)
        flag = await flag_repo.get_flag_with_full_details(flag_id)
        if not flag:
            raise NotFoundError(f"ReviewFlag {flag_id} not found.")

        # Enforce authorization
        if current_user.role == UserRole.CANDIDATE:
            raise AuthorizationError("Candidates may not view internal review case details.")
        if current_user.role == UserRole.REVIEWER:
            if flag.assigned_to_user_id != uuid.UUID(current_user.id):
                raise AuthorizationError("Reviewers may only access review cases assigned to them.")
        elif current_user.role == UserRole.EMPLOYER_ADMIN:
            if flag.application and flag.application.job:
                job = flag.application.job
                is_creator = str(job.employer_id) == current_user.id
                org_matches = bool(
                    current_user.employer_id
                    and job.creator
                    and job.creator.employer_id == current_user.employer_id
                )
                if not (is_creator or org_matches):
                    raise AuthorizationError(
                        "You are not authorized to view review cases for this job requisition."
                    )

        app = flag.application
        cand = app.candidate if app else None
        job = app.job if app else None
        ce = flag.criterion_evidence
        crit = ce.criterion if ce else None
        evidence_item = ce.evidence_item if ce else None

        clarification_items = [
            CandidateClarificationItem.model_validate(c)
            for c in (ce.correction_requests if ce else [])
        ]
        decision_items = [
            ReviewDecisionItem.model_validate(d) for d in (ce.review_decisions if ce else [])
        ]

        return ReviewCaseDetailResponse(
            flag_id=flag.id,
            flag_status=flag.status,
            priority=flag.priority,
            reason=flag.reason,
            assigned_to_user_id=flag.assigned_to_user_id,
            application_id=flag.application_id,
            application_status=app.status if app else ApplicationStatus.SCREENING,
            candidate_id=cand.id if cand else uuid.uuid4(),
            candidate_name=cand.full_name if cand else "Candidate",
            candidate_email=cand.email if cand else "",
            job_id=job.id if job else uuid.uuid4(),
            job_title=job.title if job else "",
            criterion_id=crit.id if crit else uuid.uuid4(),
            criterion_name=crit.name if crit else "Unknown",
            criterion_category=crit.category if crit else "required",
            criterion_description=crit.description if crit else None,
            criterion_version=crit.version if crit else 1,
            criterion_weight=crit.weight if crit else 1.0,
            criterion_evidence_id=ce.id if ce else uuid.uuid4(),
            ai_status=ce.ai_status if ce else EvidenceStatus.AMBIGUOUS,
            ai_confidence=ce.ai_confidence if ce else 0.0,
            ai_reasoning=ce.ai_reasoning if ce else None,
            verification_state=ce.verification_state if ce else VerificationState.UNVERIFIED,
            source_excerpt=ce.source_excerpt if ce else None,
            source_page=ce.source_page if ce else None,
            evidence_item_id=ce.evidence_item_id if ce else None,
            claim_text=evidence_item.claim_text if evidence_item else None,
            clarifications=clarification_items,
            decisions=decision_items,
            created_at=flag.created_at,
            resolved_at=flag.resolved_at,
        )

    async def record_reviewer_decision(
        self,
        flag_id: uuid.UUID,
        decision: ReviewDecisionType,
        mandatory_rationale: str,
        current_user: CurrentUser,
        session: AsyncSession,
        ip_address: str | None = None,
    ) -> ReviewDecisionResponse:
        """
        Records an authorized human reviewer action on evidence:
        - accepted: VerificationState.HUMAN_VERIFIED, flag resolved.
        - rejected: VerificationState.HUMAN_REJECTED, flag resolved.
        - requested_clarification: VerificationState.UNVERIFIED, flag under_review.
        Enforces non-empty rationale and reviewer assignment boundaries.
        """
        clean_rationale = mandatory_rationale.strip()
        if not clean_rationale:
            raise ValidationError(
                "A non-empty explanatory rationale is strictly mandatory for reviewer actions."
            )

        if current_user.role == UserRole.CANDIDATE:
            raise AuthorizationError("Candidates cannot make reviewer decisions.")

        flag_repo = ReviewFlagRepository(session)
        flag = await flag_repo.get_flag_with_full_details(flag_id)
        ce = None
        application = None

        if flag:
            ce = flag.criterion_evidence
            application = flag.application
            criterion_evidence_id = flag.criterion_evidence_id
            if not criterion_evidence_id:
                raise ValidationError(
                    "This review flag is not linked to a specific criterion evidence item."
                )

            # Enforce reviewer assignment boundary
            if current_user.role == UserRole.REVIEWER:
                if flag.assigned_to_user_id and flag.assigned_to_user_id != uuid.UUID(current_user.id):
                    raise AuthorizationError(
                        "Reviewers may only record decisions for review cases assigned to them."
                    )
            elif current_user.role == UserRole.EMPLOYER_ADMIN:
                if application and application.job:
                    job = application.job
                    is_creator = str(job.employer_id) == current_user.id
                    org_matches = bool(
                        current_user.employer_id
                        and job.creator
                        and job.creator.employer_id == current_user.employer_id
                    )
                    if not (is_creator or org_matches):
                        raise AuthorizationError(
                            "You are not authorized to record decisions for this job requisition."
                        )
        else:
            # Check if flag_id is a CriterionEvidence.id
            ce_query = (
                select(CriterionEvidence)
                .where(CriterionEvidence.id == flag_id)
                .options(
                    selectinload(CriterionEvidence.evaluation)
                    .selectinload(Evaluation.application)
                    .selectinload(Application.job)
                    .selectinload(Job.creator),
                    selectinload(CriterionEvidence.criterion),
                    selectinload(CriterionEvidence.review_flags),
                )
            )
            ce_res = await session.execute(ce_query)
            ce = ce_res.scalar_one_or_none()
            if not ce:
                raise NotFoundError(f"ReviewFlag or CriterionEvidence {flag_id} not found.")

            criterion_evidence_id = ce.id
            evaluation = ce.evaluation
            application = evaluation.application if evaluation else None
            if not application:
                raise NotFoundError("Application associated with this criterion evidence not found.")

            if ce.review_flags:
                flag = ce.review_flags[0]

            # Enforce reviewer / employer authorization
            if current_user.role == UserRole.REVIEWER:
                if flag and flag.assigned_to_user_id and flag.assigned_to_user_id != uuid.UUID(current_user.id):
                    raise AuthorizationError(
                        "Reviewers may only record decisions for review cases assigned to them."
                    )
            elif current_user.role == UserRole.EMPLOYER_ADMIN:
                if application.job:
                    job = application.job
                    is_creator = str(job.employer_id) == current_user.id
                    org_matches = bool(
                        current_user.employer_id
                        and job.creator
                        and job.creator.employer_id == current_user.employer_id
                    )
                    if not (is_creator or org_matches):
                        raise AuthorizationError(
                            "You are not authorized to record decisions for this job requisition."
                        )

        reviewer_id = uuid.UUID(current_user.id)
        user_repo = UserRepository(session)
        reviewer_user = await user_repo.get_by_id(reviewer_id)
        if not reviewer_user:
            reviewer_user = User(
                id=reviewer_id,
                email=current_user.email,
                full_name=current_user.email.split("@")[0],
                role=current_user.role,
                employer_id=current_user.employer_id,
            )
            session.add(reviewer_user)
            await session.flush()

        # Determine target state and flag lifecycle
        if decision == ReviewDecisionType.ACCEPTED:
            new_verification_state = VerificationState.HUMAN_VERIFIED
            new_flag_status = ReviewFlagStatus.RESOLVED
            resolved_at = datetime.now(UTC)
        elif decision == ReviewDecisionType.REJECTED:
            new_verification_state = VerificationState.HUMAN_REJECTED
            new_flag_status = ReviewFlagStatus.RESOLVED
            resolved_at = datetime.now(UTC)
        elif decision == ReviewDecisionType.REQUESTED_CLARIFICATION:
            new_verification_state = VerificationState.UNVERIFIED
            new_flag_status = ReviewFlagStatus.UNDER_REVIEW
            resolved_at = None
        else:
            raise ValidationError(f"Invalid decision type: {decision}")

        # Record decision via repository (creates ReviewDecision and AuditEvent)
        decision_repo = ReviewDecisionRepository(session)
        review_decision = await decision_repo.record_decision(
            application_id=application.id,
            criterion_evidence_id=criterion_evidence_id,
            reviewer_id=reviewer_id,
            decision=decision,
            mandatory_rationale=clean_rationale,
            new_verification_state=new_verification_state,
            actor_role=current_user.role.value,
            ip_address=ip_address,
        )

        # Update flag status for all associated flags for this criterion evidence
        if criterion_evidence_id:
            await flag_repo.update_status_for_criterion_evidence(
                criterion_evidence_id=criterion_evidence_id,
                status=new_flag_status,
                resolved_at=resolved_at,
            )
        elif flag:
            await flag_repo.update_status(flag.id, new_flag_status, resolved_at)

        # If all flags on this application are resolved, mark application as REVIEWED
        all_app_flags = await flag_repo.get_by_application(application.id)
        if all_app_flags:
            all_resolved = all(
                f.status in (ReviewFlagStatus.RESOLVED, ReviewFlagStatus.DISMISSED)
                for f in all_app_flags
            )
            if all_resolved and application:
                application.status = ApplicationStatus.REVIEWED

        await session.flush()

        return ReviewDecisionResponse(
            id=review_decision.id,
            application_id=application.id,
            criterion_evidence_id=criterion_evidence_id,
            reviewer_id=reviewer_id,
            decision=decision,
            mandatory_rationale=clean_rationale,
            previous_verification_state=review_decision.previous_verification_state,
            new_verification_state=review_decision.new_verification_state,
            flag_status=new_flag_status if flag else None,
            created_at=review_decision.created_at,
        )

    async def submit_candidate_clarification(
        self,
        application_id: uuid.UUID,
        criterion_evidence_id: uuid.UUID,
        candidate_statement: str,
        additional_document_id: uuid.UUID | None,
        candidate: CurrentUser,
        session: AsyncSession,
        ip_address: str | None = None,
    ) -> CandidateClarificationResponse:
        """
        Allows a candidate to submit clarification or additional evidence for a criterion.
        Candidate-provided evidence remains strictly unverified until human review.
        Updates verification_state to CANDIDATE_CLARIFIED without overwriting prior evaluations.
        """
        clean_statement = candidate_statement.strip()
        if not clean_statement:
            raise ValidationError("Candidate clarification statement cannot be empty.")

        if candidate.role != UserRole.CANDIDATE:
            raise AuthorizationError("Only candidates may submit clarifications.")

        candidate_id = uuid.UUID(str(candidate.id))

        # 1. Fetch application and verify ownership
        app_repo = ApplicationRepository(session)
        application = await app_repo.get_with_job(application_id)
        if not application:
            raise NotFoundError(f"Application {application_id} not found.")

        if str(application.candidate_id) != str(candidate.id):
            raise AuthorizationError(
                "Candidates may only submit clarifications for their own applications."
            )

        # 2. Verify additional document if provided
        if additional_document_id is not None:
            doc_repo = DocumentRepository(session)
            doc = await doc_repo.get_by_id(additional_document_id)
            if not doc:
                raise NotFoundError(f"Additional document {additional_document_id} not found.")
            if str(doc.candidate_id) != str(candidate.id):
                raise AuthorizationError(
                    "Additional document must belong to the submitting candidate."
                )

        # 3. Fetch criterion evidence and verify it belongs to this application
        ce_query = (
            select(CriterionEvidence)
            .join(Evaluation, CriterionEvidence.evaluation_id == Evaluation.id)
            .where(
                (CriterionEvidence.id == criterion_evidence_id)
                | (CriterionEvidence.job_criterion_id == criterion_evidence_id),
                Evaluation.application_id == application_id,
            )
        )
        ce_res = await session.execute(ce_query)
        ce = ce_res.scalar_one_or_none()
        if not ce:
            raise NotFoundError(f"CriterionEvidence {criterion_evidence_id} not found.")

        # 4. Create CorrectionRequest record
        correction_repo = CorrectionRequestRepository(session)
        correction = await correction_repo.create_correction(
            application_id=application_id,
            candidate_id=candidate_id,
            criterion_evidence_id=ce.id,
            candidate_statement=clean_statement,
            additional_document_id=additional_document_id,
        )

        # 5. Update criterion evidence state to CANDIDATE_CLARIFIED
        # Candidate-provided evidence remains unverified until reviewed
        ce.verification_state = VerificationState.CANDIDATE_CLARIFIED

        # 6. Re-activate or update review flag to PENDING so reviewer sees candidate response
        flag_repo = ReviewFlagRepository(session)
        flags = await flag_repo.get_by_criterion_evidence(ce.id)
        for flag in flags:
            if flag.status in (ReviewFlagStatus.RESOLVED, ReviewFlagStatus.UNDER_REVIEW):
                flag.status = ReviewFlagStatus.PENDING
                flag.resolved_at = None

        application.status = ApplicationStatus.NEEDS_REVIEW

        # 7. Append immutable audit event
        audit_repo = AuditEventRepository(session)
        await audit_repo.log_event(
            action="CANDIDATE_CLARIFICATION_SUBMITTED",
            resource_type="correction_request",
            resource_id=str(correction.id),
            actor_id=str(candidate_id),
            actor_role=candidate.role.value,
            entity_version=1,
            prior_state={"verification_state": VerificationState.UNVERIFIED.value},
            new_state={"verification_state": VerificationState.CANDIDATE_CLARIFIED.value},
            details={
                "application_id": str(application_id),
                "criterion_evidence_id": str(criterion_evidence_id),
                "has_additional_document": additional_document_id is not None,
                "statement_length": len(clean_statement),
            },
            ip_address=ip_address,
        )

        return CandidateClarificationResponse(
            id=correction.id,
            application_id=application_id,
            candidate_id=candidate_id,
            criterion_evidence_id=criterion_evidence_id,
            candidate_statement=clean_statement,
            additional_document_id=additional_document_id,
            status=correction.status,
            new_verification_state=VerificationState.CANDIDATE_CLARIFIED,
            created_at=correction.created_at,
        )
