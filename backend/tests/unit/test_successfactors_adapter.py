import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ValidationError
from app.core.security import CurrentUser, UserRole
from app.db.models.application import Application
from app.db.models.audit import AuditEvent
from app.db.models.job import Job, JobCriterion
from app.integrations.successfactors.adapter import SuccessFactorsImportAdapter
from app.integrations.successfactors.fixtures import (
    get_synthetic_applicant_feed,
)
from app.integrations.successfactors.schemas import (
    SIMULATED_DISCLAIMER,
    SFApplicantFeedBatch,
    SFJobRequisition,
)


def test_synthetic_applicant_feed_fixtures():
    """Verify fixture properties, disclaimer, and benchmark scenario coverage."""
    feed = get_synthetic_applicant_feed()
    assert feed.is_simulated is True
    assert "SIMULATION" in feed.simulation_disclaimer
    assert feed.requisition.job_req_id == "REQ-CLOUD-2026"
    assert len(feed.requisition.criteria) == 5
    assert len(feed.applications) == 8

    # Verify each application has valid resume attachment with pages
    for app in feed.applications:
        assert app.resume_attachment.pages
        assert app.resume_attachment.file_hash
        assert app.candidate.email


@pytest.mark.asyncio
async def test_successfactors_import_adapter_success(test_session: AsyncSession):
    """
    Test that SuccessFactorsImportAdapter imports the simulated feed into ClearHire domain models
    and logs an audit event.
    """
    employer_id = str(uuid.uuid4())
    admin_user = CurrentUser(
        id=employer_id,
        email="emp.admin@example.com",
        role=UserRole.EMPLOYER_ADMIN,
    )

    feed = get_synthetic_applicant_feed()
    adapter = SuccessFactorsImportAdapter(test_session)
    result = await adapter.import_feed(feed, admin_user)
    await test_session.commit()

    assert result.is_simulated is True
    assert result.simulation_disclaimer == SIMULATED_DISCLAIMER
    assert result.imported_applications_count == 8
    assert result.imported_candidates_count == 8
    assert len(result.imported_application_ids) == 8

    # Verify Job and Criteria in database
    job_res = await test_session.execute(select(Job).where(Job.id == result.job_id))
    job = job_res.scalar_one()
    assert job.title == "Senior Cloud Backend Engineer"

    crit_res = await test_session.execute(select(JobCriterion).where(JobCriterion.job_id == job.id))
    criteria = crit_res.scalars().all()
    assert len(criteria) == 5

    # Verify Applications and Documents
    apps_res = await test_session.execute(select(Application).where(Application.job_id == job.id))
    apps = apps_res.scalars().all()
    assert len(apps) == 8

    # Verify Audit Event
    audit_res = await test_session.execute(
        select(AuditEvent).where(
            AuditEvent.action == "SUCCESSFACTORS_IMPORT_COMPLETED",
            AuditEvent.resource_id == str(job.id),
        )
    )
    audit_event = audit_res.scalar_one_or_none()
    assert audit_event is not None
    assert audit_event.details["is_simulated"] is True
    assert audit_event.details["applications_imported"] == 8


@pytest.mark.asyncio
async def test_successfactors_import_adapter_rejects_unauthorized_user(test_session: AsyncSession):
    """Test that Candidates cannot trigger SuccessFactors feed imports."""
    cand_user = CurrentUser(
        id=str(uuid.uuid4()),
        email="candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    feed = get_synthetic_applicant_feed()
    adapter = SuccessFactorsImportAdapter(test_session)

    with pytest.raises(AuthorizationError) as exc_info:
        await adapter.import_feed(feed, cand_user)
    assert "Only Employer Administrators" in str(exc_info.value)


@pytest.mark.asyncio
async def test_successfactors_import_adapter_validates_criteria(test_session: AsyncSession):
    """Test that a requisition without criteria is rejected with ValidationError."""
    admin_user = CurrentUser(
        id=str(uuid.uuid4()),
        email="admin@example.com",
        role=UserRole.EMPLOYER_ADMIN,
    )
    empty_req = SFJobRequisition(
        job_req_id="REQ-EMPTY",
        title="Empty Job",
        criteria=[],
    )
    feed = SFApplicantFeedBatch(
        requisition=empty_req,
        applications=[],
    )
    adapter = SuccessFactorsImportAdapter(test_session)

    with pytest.raises(ValidationError) as exc_info:
        await adapter.import_feed(feed, admin_user)
    assert "contains no criteria" in str(exc_info.value)
