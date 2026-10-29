import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ValidationError
from app.db.models.application import Application
from app.db.models.audit import AuditEvent
from app.db.models.document import Document
from app.db.models.enums import DocumentProcessingStatus, ReviewDecisionType, VerificationState
from app.db.models.evaluation import CriterionEvidence, Evaluation
from app.db.models.job import Job, JobCriterion
from app.db.models.review import ReviewDecision
from app.db.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


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
        audit_event = AuditEvent(
            action="EVALUATION_RECORDED",
            resource_type="evaluation",
            resource_id=str(evaluation.id),
            actor_id=actor_id or "system_ai_pipeline",
            actor_role="system",
            details={
                "application_id": str(application_id),
                "evaluation_version": next_version,
                "overall_status": str(overall_status),
                "criteria_evaluated_count": len(criterion_mappings),
            },
        )
        self.session.add(audit_event)
        await self.session.flush()

        return evaluation


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
        audit_event = AuditEvent(
            action="REVIEW_DECISION_RECORDED",
            resource_type="review_decision",
            resource_id=str(review_decision.id),
            actor_id=str(reviewer_id),
            actor_role=actor_role,
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
        self.session.add(audit_event)
        await self.session.flush()

        return review_decision


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
