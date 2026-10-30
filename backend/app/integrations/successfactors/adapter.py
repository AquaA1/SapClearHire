import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ValidationError
from app.core.security import CurrentUser, UserRole
from app.db.models.application import Application
from app.db.models.document import Document
from app.db.models.enums import (
    ApplicationStatus,
    CriterionCategory,
    DocumentProcessingStatus,
    JobStatus,
)
from app.db.models.job import Job, JobCriterion
from app.db.models.user import User
from app.integrations.successfactors.schemas import (
    SIMULATED_DISCLAIMER,
    SFApplicantFeedBatch,
    SFImportResult,
)
from app.repositories.audit import AuditEventRepository


class SuccessFactorsImportAdapter:
    """
    Data adapter importing authorized synthetic SuccessFactors applicant feeds
    into ClearHire's domain models (Job, JobCriterion, User, Document, Application).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_repo = AuditEventRepository(session)

    async def import_feed(
        self,
        feed: SFApplicantFeedBatch,
        current_user: CurrentUser,
    ) -> SFImportResult:
        """
        Imports the batch feed into the database in the active transaction:
        - Validates actor permissions (EMPLOYER_ADMIN or SYSTEM_AUDITOR).
        - Persists Job and criteria.
        - Persists Candidates, Documents, and Applications.
        - Records an immutable AuditEvent.
        """
        if current_user.role not in (UserRole.EMPLOYER_ADMIN, UserRole.SYSTEM_AUDITOR):
            raise AuthorizationError(
                "Only Employer Administrators and System Auditors can import applicant feeds."
            )

        # Ensure employer exists
        emp_query = select(User).where(User.id == uuid.UUID(current_user.id))
        emp_res = await self.session.execute(emp_query)
        employer = emp_res.scalar_one_or_none()
        if not employer:
            employer = User(
                id=uuid.UUID(current_user.id),
                email=current_user.email,
                role=current_user.role,
                full_name=getattr(current_user, "email", "Employer Admin"),
            )
            self.session.add(employer)
            await self.session.flush()

        req = feed.requisition
        if not req.criteria:
            raise ValidationError(
                f"SuccessFactors Job Requisition {req.job_req_id} contains no criteria."
            )

        # 1. Create ClearHire Job
        job = Job(
            employer_id=employer.id,
            external_requisition_id=req.job_req_id,
            title=req.title,
            description=f"Imported from simulated SuccessFactors requisition {req.job_req_id} ({req.department})",
            department=req.department,
            status=JobStatus.ACTIVE,
        )
        self.session.add(job)
        await self.session.flush()

        # 2. Create Job Criteria
        for crit_data in req.criteria:
            cat_str = str(crit_data.get("category", "required")).lower()
            category = (
                CriterionCategory.REQUIRED if cat_str == "required" else CriterionCategory.PREFERRED
            )
            criterion = JobCriterion(
                job_id=job.id,
                name=crit_data["name"],
                category=category,
                description=crit_data.get("description"),
                version=1,
            )
            self.session.add(criterion)
        await self.session.flush()

        # 3. Create Candidates, Documents, and Applications
        imported_app_ids: list[uuid.UUID] = []
        imported_candidates_count = 0
        warnings: list[str] = []

        for sf_app in feed.applications:
            cand_meta = sf_app.candidate
            cand_email = cand_meta.email.strip().lower()

            # Find or create candidate user
            cand_user_query = select(User).where(User.email == cand_email)
            cand_user_res = await self.session.execute(cand_user_query)
            candidate_user = cand_user_res.scalar_one_or_none()
            if not candidate_user:
                candidate_user = User(
                    email=cand_email,
                    role=UserRole.CANDIDATE,
                    full_name=f"{cand_meta.first_name} {cand_meta.last_name}",
                )
                self.session.add(candidate_user)
                await self.session.flush()
                imported_candidates_count += 1

            # Create Document with page-preserved extracted text
            attachment = sf_app.resume_attachment
            raw_pages = {str(k): v for k, v in attachment.pages.items()}
            doc = Document(
                candidate_id=candidate_user.id,
                file_name=attachment.file_name,
                file_path=f"simulated/successfactors/{sf_app.application_id}_{attachment.file_name}",
                file_hash=attachment.file_hash,
                mime_type=attachment.mime_type,
                file_size_bytes=attachment.file_size_bytes,
                extracted_text_by_page=raw_pages,
                processing_status=DocumentProcessingStatus.COMPLETED,
            )
            self.session.add(doc)
            await self.session.flush()

            # Create Application
            application = Application(
                job_id=job.id,
                candidate_id=candidate_user.id,
                primary_document_id=doc.id,
                status=ApplicationStatus.SUBMITTED,
            )
            self.session.add(application)
            await self.session.flush()
            imported_app_ids.append(application.id)

        # 4. Log immutable AuditEvent
        await self.audit_repo.log_event(
            action="SUCCESSFACTORS_IMPORT_COMPLETED",
            resource_type="job",
            resource_id=str(job.id),
            actor_id=str(employer.id),
            actor_role=current_user.role,
            details={
                "feed_id": feed.feed_id,
                "job_req_id": req.job_req_id,
                "applications_imported": len(imported_app_ids),
                "is_simulated": True,
            },
        )

        return SFImportResult(
            is_simulated=True,
            simulation_disclaimer=SIMULATED_DISCLAIMER,
            feed_id=feed.feed_id,
            job_id=job.id,
            job_title=job.title,
            imported_candidates_count=imported_candidates_count,
            imported_applications_count=len(imported_app_ids),
            imported_application_ids=imported_app_ids,
            warnings=warnings,
        )
