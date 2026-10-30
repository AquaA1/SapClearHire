import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SIMULATED_DISCLAIMER = (
    "NOTICE: This feed and integration is a SIMULATION built for demonstration and benchmark purposes. "
    "It models standard SAP SuccessFactors Recruiting OData entity structures but does NOT connect to "
    "or interact with a live SAP SuccessFactors instance."
)


class SFJobRequisition(BaseModel):
    """
    Simulated SAP SuccessFactors Job Requisition entity (JobRequisition).
    Models requisition metadata, required criteria, and department classifications.
    """

    model_config = ConfigDict(from_attributes=True)

    job_req_id: str = Field(
        description="Simulated SuccessFactors Job Requisition ID (e.g. 'REQ-1001')"
    )
    title: str = Field(description="Position title")
    department: str = Field(default="Engineering", description="Organizational unit")
    hiring_manager_name: str = Field(default="Jane HR Manager", description="Hiring manager name")
    hiring_manager_email: str = Field(
        default="hiring.manager@example.com", description="Hiring manager email"
    )
    status: str = Field(default="open", description="Requisition status")
    criteria: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Versioned criteria with name, category (required/preferred), and description",
    )
    created_date: datetime = Field(default_factory=datetime.utcnow)


class SFCandidate(BaseModel):
    """
    Simulated SAP SuccessFactors Candidate entity (Candidate).
    Models applicant profile metadata and contact information.
    """

    model_config = ConfigDict(from_attributes=True)

    candidate_id: str = Field(
        description="Simulated SuccessFactors Candidate ID (e.g. 'CAND-5001')"
    )
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    city: str | None = None
    country: str | None = "USA"


class SFAttachment(BaseModel):
    """
    Simulated SAP SuccessFactors Attachment entity (Attachment).
    Carries resume text partitioned by page numbers and metadata.
    """

    model_config = ConfigDict(from_attributes=True)

    attachment_id: str = Field(description="Unique attachment identifier")
    file_name: str = Field(description="Resume file name (e.g. 'resume.pdf')")
    mime_type: str = Field(default="application/pdf")
    file_size_bytes: int = Field(default=1024)
    file_hash: str = Field(description="SHA-256 checksum of document content")
    pages: dict[int, str] = Field(
        description="Page-preserved text content mapped by page number (1-indexed)"
    )


class SFJobApplication(BaseModel):
    """
    Simulated SAP SuccessFactors Job Application entity (JobApplication).
    Links a candidate and their resume attachment to a job requisition.
    """

    model_config = ConfigDict(from_attributes=True)

    application_id: str = Field(
        description="Simulated SuccessFactors Application ID (e.g. 'APP-9001')"
    )
    job_req_id: str = Field(description="Referenced JobRequisition ID")
    candidate: SFCandidate = Field(description="Candidate profile details")
    resume_attachment: SFAttachment = Field(description="Attached candidate resume document")
    status: str = Field(default="Applied", description="SuccessFactors application workflow status")
    application_date: datetime = Field(default_factory=datetime.utcnow)


class SFApplicantFeedBatch(BaseModel):
    """
    Simulated batch payload representing an exported applicant feed from SuccessFactors.
    """

    model_config = ConfigDict(from_attributes=True)

    is_simulated: Literal[True] = True
    simulation_disclaimer: str = SIMULATED_DISCLAIMER
    feed_id: str = Field(default_factory=lambda: f"FEED-{uuid.uuid4().hex[:8].upper()}")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    requisition: SFJobRequisition
    applications: list[SFJobApplication] = Field(default_factory=list)


class SFImportResult(BaseModel):
    """
    Summary of applicant feed importation into ClearHire's domain models.
    """

    model_config = ConfigDict(from_attributes=True)

    is_simulated: Literal[True] = True
    simulation_disclaimer: str = SIMULATED_DISCLAIMER
    feed_id: str
    job_id: uuid.UUID
    job_title: str
    imported_candidates_count: int
    imported_applications_count: int
    imported_application_ids: list[uuid.UUID]
    warnings: list[str] = Field(default_factory=list)
