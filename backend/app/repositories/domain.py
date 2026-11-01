import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.core.exceptions import ValidationError
from app.core.security import UserRole
from app.db.models.application import Application
from app.db.models.document import CandidateSkill, Document, EvidenceItem, ExtractionRun
from app.db.models.enums import (
    CorrectionRequestStatus,
    DocumentProcessingStatus,
    ReviewDecisionType,
    ReviewFlagStatus,
    VerificationState,
)
from app.db.models.evaluation import CriterionEvidence, Evaluation
from app.db.models.job import Job, JobCriterion
from app.db.models.review import CorrectionRequest, ReviewDecision, ReviewFlag
from app.db.models.user import User
from app.repositories.audit import AuditEventRepository
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    async def get_by_email(self, email: str) -> User | None:
        normalized = self.normalize_email(email)
        query = select(User).where(User.email == normalized)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_user_with_credentials(
        self,
        email: str,
        full_name: str,
        password_hash: str | None,
        role: UserRole = UserRole.CANDIDATE,
        employer_id: str | None = None,
        email_verified: bool = False,
        is_active: bool = True,
        user_id: uuid.UUID | None = None,
    ) -> User:
        user = User(
            id=user_id or uuid.uuid4(),
            email=self.normalize_email(email),
            full_name=full_name.strip(),
            password_hash=password_hash,
            role=role,
            employer_id=employer_id,
            email_verified=email_verified,
            is_active=is_active,
        )
        self.session.add(user)
        await self.session.flush()
        return user


class JobRepository(BaseRepository[Job]):
    def __init__(self, session: AsyncSession):
        super().__init__(Job, session)

    async def get_with_criteria(self, job_id: uuid.UUID) -> Job | None:
        query = select(Job).where(Job.id == job_id).options(selectinload(Job.criteria))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def add_criterion(
        self,
        job_id: uuid.UUID,
        name: str,
        category: str = "requirement",
        weight: float = 1.0,
        description: str | None = None,
        version: int = 1,
    ) -> JobCriterion:
        criterion = JobCriterion(
            job_id=job_id,
            name=name,
            category=category,
            weight=weight,
            description=description,
            version=version,
        )
        self.session.add(criterion)
        await self.session.flush()
        return criterion

    async def get_active_criteria(self, job_id: uuid.UUID) -> list[JobCriterion]:
        query = (
            select(JobCriterion)
            .where(JobCriterion.job_id == job_id, JobCriterion.is_active == True)  # noqa: E712
            .order_by(JobCriterion.version.desc())
        )
        result = await self.session.execute(query)
        # Deduplicate to latest version per criterion name
        seen_names = set()
        active_items = []
        for c in result.scalars().all():
            if c.name.lower() not in seen_names:
                seen_names.add(c.name.lower())
                active_items.append(c)
        return active_items

    async def get_latest_criteria_version(self, job_id: uuid.UUID) -> int:
        query = (
            select(JobCriterion.version)
            .where(JobCriterion.job_id == job_id)
            .order_by(JobCriterion.version.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() or 1


class ApplicationRepository(BaseRepository[Application]):
    def __init__(self, session: AsyncSession):
        super().__init__(Application, session)

    async def get_with_evaluations(self, application_id: uuid.UUID) -> Application | None:
        query = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.evaluations).selectinload(
                    Evaluation.criterion_evidence_items
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_with_job(self, application_id: uuid.UUID) -> Application | None:
        query = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.job).selectinload(Job.creator),
                selectinload(Application.candidate),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class EvaluationRepository(BaseRepository[Evaluation]):
    def __init__(self, session: AsyncSession):
        super().__init__(Evaluation, session)

    async def record_evaluation(
        self,
        application_id: uuid.UUID,
        job_criteria_version: int,
        extraction_run_id: uuid.UUID,
        overall_status: Any,
        criterion_mappings: list[dict[str, Any]],
        summary_notes: str | None = None,
        raw_model_output: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> Evaluation:
        """
        Creates a new versioned Evaluation and appends an immutable AuditEvent in the same transaction.
        Prior evaluations for this application have is_latest set to False.
        """
        # Determine next version
        version_query = (
            select(Evaluation.version)
            .where(Evaluation.application_id == application_id)
            .order_by(Evaluation.version.desc())
            .limit(1)
        )
        max_ver = (await self.session.execute(version_query)).scalar_one_or_none() or 0
        next_version = max_ver + 1

        # Mark previous evaluations as not latest
        await self.session.execute(
            update(Evaluation)
            .where(Evaluation.application_id == application_id)
            .values(is_latest=False)
        )

        evaluation = Evaluation(
            application_id=application_id,
            version=next_version,
            job_criteria_version=job_criteria_version,
            extraction_run_id=extraction_run_id,
            overall_status=overall_status,
            summary_notes=summary_notes,
            raw_model_output=raw_model_output or {},
            is_latest=True,
        )
        self.session.add(evaluation)
        await self.session.flush()

        # Add criterion evidence items
        for mapping in criterion_mappings:
            ce = CriterionEvidence(
                evaluation_id=evaluation.id,
                job_criterion_id=mapping["job_criterion_id"],
                evidence_item_id=mapping.get("evidence_item_id"),
                ai_status=mapping["ai_status"],
                ai_confidence=mapping.get("ai_confidence", 1.0),
                ai_reasoning=mapping.get("ai_reasoning"),
                verification_state=mapping.get("verification_state", VerificationState.UNVERIFIED),
                source_excerpt=mapping.get("source_excerpt"),
                source_page=mapping.get("source_page"),
            )
            self.session.add(ce)

        # Append-only audit record in same transaction
        audit_repo = AuditEventRepository(self.session)
        await audit_repo.log_event(
            action="EVALUATION_RECORDED",
            resource_type="evaluation",
            resource_id=str(evaluation.id),
            actor_id=actor_id or "system_ai_pipeline",
            actor_role="system",
            entity_version=next_version,
            prior_state={"previous_evaluation_version": max_ver} if max_ver > 0 else None,
            new_state={
                "version": next_version,
                "overall_status": str(overall_status),
                "criteria_evaluated_count": len(criterion_mappings),
            },
            details={
                "application_id": str(application_id),
                "evaluation_version": next_version,
                "overall_status": str(overall_status),
                "criteria_evaluated_count": len(criterion_mappings),
            },
        )

        return evaluation

    async def get_evaluation_with_items(self, evaluation_id: uuid.UUID) -> Evaluation | None:
        query = (
            select(Evaluation)
            .where(Evaluation.id == evaluation_id)
            .options(
                selectinload(Evaluation.application)
                .selectinload(Application.job)
                .selectinload(Job.creator),
                selectinload(Evaluation.criterion_evidence_items).selectinload(
                    CriterionEvidence.criterion
                ),
                selectinload(Evaluation.criterion_evidence_items).selectinload(
                    CriterionEvidence.evidence_item
                ),
                selectinload(Evaluation.criterion_evidence_items).selectinload(
                    CriterionEvidence.review_decisions
                ),
                selectinload(Evaluation.criterion_evidence_items).selectinload(
                    CriterionEvidence.correction_requests
                ),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_by_application(self, application_id: uuid.UUID) -> Evaluation | None:
        query = (
            select(Evaluation)
            .where(Evaluation.application_id == application_id, Evaluation.is_latest.is_(True))
            .options(
                selectinload(Evaluation.application)
                .selectinload(Application.job)
                .selectinload(Job.creator),
                selectinload(Evaluation.criterion_evidence_items).selectinload(
                    CriterionEvidence.criterion
                ),
                selectinload(Evaluation.criterion_evidence_items).selectinload(
                    CriterionEvidence.evidence_item
                ),
                selectinload(Evaluation.criterion_evidence_items).selectinload(
                    CriterionEvidence.review_decisions
                ),
                selectinload(Evaluation.criterion_evidence_items).selectinload(
                    CriterionEvidence.correction_requests
                ),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class ReviewDecisionRepository(BaseRepository[ReviewDecision]):
    def __init__(self, session: AsyncSession):
        super().__init__(ReviewDecision, session)

    async def record_decision(
        self,
        application_id: uuid.UUID,
        criterion_evidence_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        decision: ReviewDecisionType,
        mandatory_rationale: str,
        new_verification_state: VerificationState,
        actor_role: str = "reviewer",
        ip_address: str | None = None,
    ) -> ReviewDecision:
        """
        Records an authorized human reviewer decision with mandatory non-empty rationale.
        Preserves historical decisions (sets prior is_active=False), updates criterion state,
        and creates an immutable AuditEvent in the same database transaction.
        """
        clean_rationale = mandatory_rationale.strip()
        if not clean_rationale:
            raise ValidationError(
                "A non-empty explanatory rationale is strictly mandatory for reviewer decisions."
            )

        # Fetch current criterion evidence to capture previous state
        ce_query = select(CriterionEvidence).where(CriterionEvidence.id == criterion_evidence_id)
        ce_result = await self.session.execute(ce_query)
        ce = ce_result.scalar_one_or_none()
        if not ce:
            raise ValidationError(f"CriterionEvidence {criterion_evidence_id} not found.")

        previous_state = ce.verification_state

        # Check for duplicate submission (idempotency)
        existing_active_query = (
            select(ReviewDecision)
            .where(
                ReviewDecision.criterion_evidence_id == criterion_evidence_id,
                ReviewDecision.is_active.is_(True),
            )
        )
        existing_active = (await self.session.execute(existing_active_query)).scalar_one_or_none()
        if (
            existing_active
            and existing_active.decision == decision
            and existing_active.mandatory_rationale == clean_rationale
            and existing_active.reviewer_id == reviewer_id
        ):
            return existing_active

        # Deactivate previous active decisions for this criterion evidence
        await self.session.execute(
            update(ReviewDecision)
            .where(
                ReviewDecision.criterion_evidence_id == criterion_evidence_id,
                ReviewDecision.is_active == True,  # noqa: E712
            )
            .values(is_active=False)
        )

        # Insert new decision
        review_decision = ReviewDecision(
            application_id=application_id,
            criterion_evidence_id=criterion_evidence_id,
            reviewer_id=reviewer_id,
            decision=decision,
            mandatory_rationale=clean_rationale,
            previous_verification_state=str(previous_state),
            new_verification_state=str(new_verification_state),
            is_active=True,
        )
        self.session.add(review_decision)

        # Update criterion evidence verification state
        ce.verification_state = new_verification_state

        # Append-only audit trail record in the same transaction
        audit_repo = AuditEventRepository(self.session)
        await audit_repo.log_event(
            action="REVIEW_DECISION_RECORDED",
            resource_type="review_decision",
            resource_id=str(review_decision.id),
            actor_id=str(reviewer_id),
            actor_role=actor_role,
            entity_version=1,
            prior_state={"verification_state": str(previous_state)},
            new_state={"verification_state": str(new_verification_state)},
            details={
                "application_id": str(application_id),
                "criterion_evidence_id": str(criterion_evidence_id),
                "decision": str(decision),
                "rationale": clean_rationale,
                "previous_state": str(previous_state),
                "new_state": str(new_verification_state),
            },
            ip_address=ip_address,
        )

        return review_decision


class ReviewFlagRepository(BaseRepository[ReviewFlag]):
    def __init__(self, session: AsyncSession):
        super().__init__(ReviewFlag, session)

    async def create_flag(
        self,
        application_id: uuid.UUID,
        flag_type: str,
        reason: str,
        criterion_evidence_id: uuid.UUID | None = None,
        priority: str = "normal",
        assigned_to_user_id: uuid.UUID | None = None,
        status: ReviewFlagStatus = ReviewFlagStatus.PENDING,
    ) -> ReviewFlag:
        flag = ReviewFlag(
            application_id=application_id,
            criterion_evidence_id=criterion_evidence_id,
            flag_type=flag_type,
            status=status,
            priority=priority,
            reason=reason,
            assigned_to_user_id=assigned_to_user_id,
        )
        self.session.add(flag)
        await self.session.flush()
        return flag

    async def get_by_criterion_evidence(self, criterion_evidence_id: uuid.UUID) -> list[ReviewFlag]:
        query = (
            select(ReviewFlag)
            .where(ReviewFlag.criterion_evidence_id == criterion_evidence_id)
            .order_by(ReviewFlag.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_application(self, application_id: uuid.UUID) -> list[ReviewFlag]:
        query = (
            select(ReviewFlag)
            .where(ReviewFlag.application_id == application_id)
            .order_by(ReviewFlag.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_assigned_flags(
        self,
        user_id: uuid.UUID | None = None,
        status: ReviewFlagStatus | None = None,
        status_list: list[ReviewFlagStatus] | None = None,
        application_id: uuid.UUID | None = None,
        employer_id: uuid.UUID | None = None,
        org_employer_id: str | None = None,
    ) -> list[ReviewFlag]:
        query = (
            select(ReviewFlag)
            .options(
                selectinload(ReviewFlag.application).selectinload(Application.candidate),
                selectinload(ReviewFlag.application).selectinload(Application.job),
                selectinload(ReviewFlag.criterion_evidence).selectinload(
                    CriterionEvidence.criterion
                ),
                selectinload(ReviewFlag.criterion_evidence).selectinload(
                    CriterionEvidence.review_decisions
                ),
            )
            .order_by(ReviewFlag.created_at.desc())
        )
        if employer_id is not None or org_employer_id is not None:
            creator = aliased(User)
            query = (
                query.join(ReviewFlag.application)
                .join(Application.job)
                .outerjoin(creator, Job.creator)
            )
            if employer_id is not None and org_employer_id:
                query = query.where(
                    (Job.employer_id == employer_id) | (creator.employer_id == org_employer_id)
                )
            elif employer_id is not None:
                query = query.where(Job.employer_id == employer_id)
            elif org_employer_id:
                query = query.where(creator.employer_id == org_employer_id)

        if user_id is not None:
            query = query.where(ReviewFlag.assigned_to_user_id == user_id)
        if status_list is not None:
            query = query.where(ReviewFlag.status.in_(status_list))
        elif status is not None:
            query = query.where(ReviewFlag.status == status)
        if application_id is not None:
            query = query.where(ReviewFlag.application_id == application_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_flag_with_full_details(self, flag_id: uuid.UUID) -> ReviewFlag | None:
        query = (
            select(ReviewFlag)
            .where(ReviewFlag.id == flag_id)
            .options(
                selectinload(ReviewFlag.application).selectinload(Application.candidate),
                selectinload(ReviewFlag.application)
                .selectinload(Application.job)
                .selectinload(Job.creator),
                selectinload(ReviewFlag.criterion_evidence).selectinload(
                    CriterionEvidence.criterion
                ),
                selectinload(ReviewFlag.criterion_evidence).selectinload(
                    CriterionEvidence.evidence_item
                ),
                selectinload(ReviewFlag.criterion_evidence).selectinload(
                    CriterionEvidence.correction_requests
                ),
                selectinload(ReviewFlag.criterion_evidence).selectinload(
                    CriterionEvidence.review_decisions
                ),
                selectinload(ReviewFlag.assigned_to),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        flag_id: uuid.UUID,
        status: ReviewFlagStatus,
        resolved_at: datetime | None = None,
    ) -> ReviewFlag | None:
        flag = await self.get_by_id(flag_id)
        if not flag:
            return None
        flag.status = status
        flag.resolved_at = resolved_at
        await self.session.flush()
        return flag

    async def update_status_for_criterion_evidence(
        self,
        criterion_evidence_id: uuid.UUID,
        status: ReviewFlagStatus,
        resolved_at: datetime | None = None,
    ) -> list[ReviewFlag]:
        flags = await self.get_by_criterion_evidence(criterion_evidence_id)
        for flag in flags:
            flag.status = status
            flag.resolved_at = resolved_at
        await self.session.flush()
        return flags


class CorrectionRequestRepository(BaseRepository[CorrectionRequest]):
    def __init__(self, session: AsyncSession):
        super().__init__(CorrectionRequest, session)

    async def create_correction(
        self,
        application_id: uuid.UUID,
        candidate_id: uuid.UUID,
        criterion_evidence_id: uuid.UUID,
        candidate_statement: str,
        additional_document_id: uuid.UUID | None = None,
    ) -> CorrectionRequest:
        req = CorrectionRequest(
            application_id=application_id,
            candidate_id=candidate_id,
            criterion_evidence_id=criterion_evidence_id,
            candidate_statement=candidate_statement.strip(),
            additional_document_id=additional_document_id,
            status=CorrectionRequestStatus.SUBMITTED,
        )
        self.session.add(req)
        await self.session.flush()
        return req

    async def get_by_application(self, application_id: uuid.UUID) -> list[CorrectionRequest]:
        query = (
            select(CorrectionRequest)
            .where(CorrectionRequest.application_id == application_id)
            .order_by(CorrectionRequest.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())


class DocumentRepository(BaseRepository[Document]):
    """Data access repository for Document records."""

    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        query = select(Document).where(Document.id == document_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id_and_candidate(
        self, document_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> Document | None:
        query = select(Document).where(
            Document.id == document_id,
            Document.candidate_id == candidate_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_document(
        self,
        candidate_id: uuid.UUID,
        file_name: str,
        file_path: str,
        file_hash: str,
        file_size_bytes: int,
        mime_type: str = "application/pdf",
        status: DocumentProcessingStatus = DocumentProcessingStatus.QUEUED,
    ) -> Document:
        doc = Document(
            candidate_id=candidate_id,
            file_name=file_name,
            file_path=file_path,
            file_hash=file_hash,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            processing_status=status,
            extracted_text_by_page={},
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def update_status(
        self,
        document_id: uuid.UUID,
        status: DocumentProcessingStatus,
        page_count: int | None = None,
        extracted_text_by_page: dict[str, Any] | None = None,
        processing_error: dict[str, Any] | None = None,
    ) -> Document | None:
        doc = await self.get_by_id(document_id)
        if not doc:
            return None
        doc.processing_status = status
        if page_count is not None:
            doc.page_count = page_count
        if extracted_text_by_page is not None:
            doc.extracted_text_by_page = extracted_text_by_page
        doc.processing_error = processing_error
        await self.session.flush()
        return doc


class ExtractionRepository(BaseRepository[ExtractionRun]):
    """Data access repository for ExtractionRun, CandidateSkill, and EvidenceItem records."""

    def __init__(self, session: AsyncSession):
        super().__init__(ExtractionRun, session)

    async def get_latest_run_for_document(self, document_id: uuid.UUID) -> ExtractionRun | None:
        query = (
            select(ExtractionRun)
            .where(ExtractionRun.document_id == document_id)
            .order_by(ExtractionRun.run_number.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_next_run_number(self, document_id: uuid.UUID) -> int:
        query = (
            select(ExtractionRun.run_number)
            .where(ExtractionRun.document_id == document_id)
            .order_by(ExtractionRun.run_number.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        latest = result.scalar_one_or_none()
        return (latest or 0) + 1

    async def create_extraction_run(
        self,
        document_id: uuid.UUID,
        provider: str,
        model_name: str,
        status: DocumentProcessingStatus = DocumentProcessingStatus.PROCESSING,
    ) -> ExtractionRun:
        run_number = await self.get_next_run_number(document_id)
        run = ExtractionRun(
            document_id=document_id,
            run_number=run_number,
            provider=provider,
            model_name=model_name,
            status=status,
            raw_output={},
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def complete_extraction_run(
        self,
        extraction_run_id: uuid.UUID,
        status: DocumentProcessingStatus,
        raw_output: dict[str, Any],
        error_message: str | None = None,
    ) -> ExtractionRun | None:
        run = await self.get_by_id(extraction_run_id)
        if not run:
            return None
        run.status = status
        run.raw_output = raw_output
        run.error_message = error_message
        run.completed_at = datetime.now(UTC)
        await self.session.flush()
        return run

    async def update_run_status(
        self,
        extraction_run_id: uuid.UUID,
        status: DocumentProcessingStatus,
        error_message: str | None = None,
    ) -> ExtractionRun | None:
        run = await self.get_by_id(extraction_run_id)
        if not run:
            return None
        run.status = status
        if status == DocumentProcessingStatus.PROCESSING:
            run.started_at = datetime.now(UTC)
        elif status in (DocumentProcessingStatus.COMPLETED, DocumentProcessingStatus.FAILED):
            run.completed_at = datetime.now(UTC)
        if error_message is not None:
            run.error_message = error_message
        await self.session.flush()
        return run

    async def add_candidate_skill(
        self,
        extraction_run_id: uuid.UUID,
        candidate_id: uuid.UUID,
        skill_name: str,
        category: str | None,
        confidence: float,
        source_page: int | None,
        source_excerpt: str | None,
    ) -> CandidateSkill:
        skill = CandidateSkill(
            extraction_run_id=extraction_run_id,
            candidate_id=candidate_id,
            skill_name=skill_name,
            category=category,
            confidence=confidence,
            source_page=source_page,
            source_excerpt=source_excerpt,
        )
        self.session.add(skill)
        await self.session.flush()
        return skill

    async def add_evidence_item(
        self,
        extraction_run_id: uuid.UUID,
        document_id: uuid.UUID,
        claim_text: str,
        source_page: int,
        source_excerpt: str,
        confidence: float,
        grounding_verified: bool,
        raw_metadata: dict[str, Any],
    ) -> EvidenceItem:
        item = EvidenceItem(
            extraction_run_id=extraction_run_id,
            document_id=document_id,
            claim_text=claim_text,
            source_page=source_page,
            source_excerpt=source_excerpt,
            confidence=confidence,
            grounding_verified=grounding_verified,
            raw_metadata=raw_metadata,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_evidence_items_for_run(self, extraction_run_id: uuid.UUID) -> list[EvidenceItem]:
        query = select(EvidenceItem).where(EvidenceItem.extraction_run_id == extraction_run_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_candidate_skills_for_run(
        self, extraction_run_id: uuid.UUID
    ) -> list[CandidateSkill]:
        query = select(CandidateSkill).where(CandidateSkill.extraction_run_id == extraction_run_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_skills_for_candidate(self, candidate_id: uuid.UUID) -> list[CandidateSkill]:
        query = (
            select(CandidateSkill)
            .where(CandidateSkill.candidate_id == candidate_id)
            .order_by(CandidateSkill.confidence.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def clear_run_artifacts(self, extraction_run_id: uuid.UUID) -> None:
        """Deletes any partial CandidateSkill and EvidenceItem records for this run to prevent duplicates on retry."""
        await self.session.execute(
            delete(CandidateSkill).where(CandidateSkill.extraction_run_id == extraction_run_id)
        )
        await self.session.execute(
            delete(EvidenceItem).where(EvidenceItem.extraction_run_id == extraction_run_id)
        )
        await self.session.flush()

