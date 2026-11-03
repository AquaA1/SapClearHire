import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.core.security import CurrentUser, UserRole, get_current_user, require_roles
from app.db.models.application import Application
from app.db.models.job import Job
from app.db.models.transcript import InterviewTranscript, TranscriptQAItem
from app.db.session import get_db_session
from app.schemas.transcript import (
    InterviewTranscriptResponse,
    TranscriptClarificationRequest,
    TranscriptQAItemResponse,
)
from app.services.transcript import InterviewTranscriptService
from app.workers import get_background_worker

router = APIRouter(prefix="", tags=["Interview Transcripts"])


async def verify_application_access(
    application_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession,
    require_employer: bool = False,
) -> Application:
    """Verifies user authorization to access application transcripts."""
    stmt = (
        select(Application)
        .where(Application.id == application_id)
        .options(selectinload(Application.job))
    )
    res = await session.execute(stmt)
    app = res.scalar_one_or_none()

    if not app:
        raise NotFoundError(f"Application {application_id} was not found.")

    # Candidate access
    if user.role == UserRole.CANDIDATE:
        if require_employer:
            raise AuthorizationError("Only employers and reviewers may upload interview transcripts.")
        if str(app.candidate_id) != str(user.id):
            raise AuthorizationError("You are not authorized to view transcripts for this application.")
        return app

    # Reviewer / Employer access
    if user.role in (UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER):
        # Reviewers have universal queue access; employers only access applications for their own jobs
        if user.role == UserRole.EMPLOYER_ADMIN and app.job and str(app.job.employer_id) != str(user.id):
            raise AuthorizationError("You are not authorized to access applications outside your organization.")
        return app

    # System Auditor
    if user.role == UserRole.SYSTEM_AUDITOR:
        return app

    raise AuthorizationError("Unauthorized to access application transcripts.")


@router.post(
    "/applications/{application_id}/transcripts",
    response_model=InterviewTranscriptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an interview transcript for a candidate application",
)
async def upload_interview_transcript(
    application_id: uuid.UUID,
    file: UploadFile = File(..., description="Transcript file (.txt, .md, .json, .pdf, .docx)"),
    round_name: str = Form("Technical Interview", description="Interview round name"),
    current_user: CurrentUser = Depends(require_roles(UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER, UserRole.SYSTEM_AUDITOR)),
    db: AsyncSession = Depends(get_db_session),
) -> InterviewTranscriptResponse:
    """
    Uploads an interview dialogue transcript (HR/Employer side).
    Persists file securely, emits an immutable audit event, and initiates
    asynchronous background Q&A dialogue extraction and coaching analysis.
    """
    await verify_application_access(application_id, current_user, db, require_employer=True)

    filename = file.filename or "transcript.txt"
    try:
        content = await file.read()
    except Exception as exc:
        raise ValidationError(f"Failed to read uploaded transcript: {str(exc)}") from exc

    service = InterviewTranscriptService()
    transcript = await service.create_and_store_transcript(
        application_id=application_id,
        uploader_id=current_user.id,
        file_content=content,
        filename=filename,
        round_name=round_name,
        session=db,
    )

    return InterviewTranscriptResponse(
        id=transcript.id,
        application_id=transcript.application_id,
        uploader_id=transcript.uploader_id,
        round_name=transcript.round_name,
        file_name=transcript.file_name,
        file_hash=transcript.file_hash,
        file_size_bytes=transcript.file_size_bytes,
        mime_type=transcript.mime_type,
        processing_status=transcript.processing_status.value,
        raw_text=transcript.raw_text,
        processing_error=transcript.processing_error,
        qa_items=[],
        created_at=transcript.created_at,
        updated_at=transcript.updated_at,
    )


@router.get(
    "/applications/{application_id}/transcripts",
    response_model=list[InterviewTranscriptResponse],
    summary="List all interview transcripts and Q&A coaching items for an application",
)
async def list_interview_transcripts(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[InterviewTranscriptResponse]:
    """
    Retrieves all interview transcripts and structured Q&A items for an application.
    Accessible to the candidate (for their own application) and authorized employers/reviewers.
    """
    await verify_application_access(application_id, current_user, db, require_employer=False)

    service = InterviewTranscriptService()
    transcripts = await service.get_transcripts_by_application(application_id, session=db)
    return [InterviewTranscriptResponse.model_validate(t) for t in transcripts]


@router.post(
    "/transcripts/qa/{qa_id}/clarify",
    response_model=TranscriptQAItemResponse,
    summary="Submit a candidate clarification for an interview Q&A response",
)
async def clarify_transcript_qa_item(
    qa_id: uuid.UUID,
    payload: TranscriptClarificationRequest,
    current_user: CurrentUser = Depends(require_roles(UserRole.CANDIDATE)),
    db: AsyncSession = Depends(get_db_session),
) -> TranscriptQAItemResponse:
    """
    Enables candidates to provide missing context or clarification if an interview answer
    was truncated, misunderstood, or omitted from interview notes.
    """
    service = InterviewTranscriptService()
    updated_qa = await service.submit_qa_clarification(
        qa_item_id=qa_id,
        candidate_id=current_user.id,
        clarification_text=payload.clarification_text,
        session=db,
    )
    return TranscriptQAItemResponse.model_validate(updated_qa)


@router.post(
    "/transcripts/{transcript_id}/retry",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry failed interview transcript analysis",
)
async def retry_transcript_analysis(
    transcript_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_roles(UserRole.EMPLOYER_ADMIN, UserRole.REVIEWER)),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Retries analysis for a failed transcript."""
    stmt = select(InterviewTranscript).where(InterviewTranscript.id == transcript_id)
    res = await db.execute(stmt)
    transcript = res.scalar_one_or_none()

    if not transcript:
        raise NotFoundError(f"Interview transcript {transcript_id} not found.")

    worker = get_background_worker()
    await worker.submit_job(
        job_type="analyze_transcript",
        payload={"transcript_id": str(transcript.id)},
    )
    return {"message": "Transcript analysis retried", "transcript_id": str(transcript_id)}
